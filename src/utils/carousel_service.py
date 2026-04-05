"""
Carousel Service — builds Instagram carousel PNGs via the Pillow renderer,
then uploads them to GCS so the Web UI and Telegram can display them.

Inputs:  headline, key_stats, optional image URL, hook stat, source URL
Outputs: CarouselResult with public https:// export_urls pointing to GCS objects

GCS bucket: techwithhareen-carousel-assets (public read, objectAdmin for SA)
Local fallback: if GCS upload fails, returns file:// paths (dev/test only)
"""

import asyncio
import ipaddress
import logging
import os
import socket
import uuid
from typing import Optional
from urllib.parse import urlparse

import httpx

from src.utils.carousel_renderer import render_carousel
from src.utils.educational_renderer import render_educational_carousel
from src.utils.carousel_result import CarouselResult

logger = logging.getLogger(__name__)

GCS_BUCKET = "techwithhareen-carousel-assets"
GCS_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}"

# Private/link-local IP ranges to block (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("169.254.0.0/16"),  # link-local — GCP metadata service
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

# Singleton GCS client — avoid re-initialising on every upload
_gcs_client = None


def _get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        from google.cloud import storage
        _gcs_client = storage.Client()
    return _gcs_client


def _is_safe_url(url: str) -> bool:
    """Return False for private/link-local hosts (SSRF guard)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        return not any(ip in net for net in _BLOCKED_NETWORKS)
    except Exception:
        return False


async def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """Download image bytes from a URL. Blocks private/metadata IPs."""
    if not _is_safe_url(url):
        logger.warning(f"Blocked unsafe image URL: {url}")
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(f"Unexpected content-type '{content_type}' for {url}")
                return None
            if len(resp.content) > 10 * 1024 * 1024:  # 10 MB max
                logger.warning(f"Image too large from {url}")
                return None
            return resp.content
    except Exception as e:
        logger.warning(f"Could not download image from {url}: {e}")
        return None


async def _fetch_tool_logos(stats: list[str]) -> dict[str, Optional[bytes]]:
    """Fetch logos for each tool in a listicle via image search."""
    from src.agents.post_creator.image_fetcher import search_image

    logos: dict[str, Optional[bytes]] = {}
    for stat in stats:
        tool_name = stat.split("\n")[0].strip() if "\n" in stat else stat.strip()
        if tool_name in logos:
            continue
        try:
            query = f"{tool_name} logo transparent png"
            img_url = await search_image(query)
            if img_url:
                logos[tool_name] = await _fetch_image_bytes(img_url)
            else:
                logos[tool_name] = None
        except Exception as e:
            logger.warning(f"Logo fetch failed for '{tool_name}': {e}")
            logos[tool_name] = None
    return logos


def _upload_sync(local_path: str, gcs_object_name: str) -> str:
    """Synchronous GCS upload (called via asyncio.to_thread)."""
    try:
        client = _get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(gcs_object_name)
        blob.upload_from_filename(local_path, content_type="image/png")
        return f"{GCS_BASE_URL}/{gcs_object_name}"
    except Exception as e:
        logger.warning(f"GCS upload failed for {local_path}: {e} — falling back to file://")
        return f"file://{local_path}"


async def create_carousel(
    headline: str,
    key_stats: list[str],
    image_url: Optional[str] = None,
    hook_stat_value: str = "",
    hook_stat_label: str = "",
    source_url: str | None = None,
    content_type: str = "news",
    carousel_format: Optional[str] = None,
    template_id: str = "dark_tech",
) -> CarouselResult:
    """
    Create an Instagram carousel using the Pillow-based renderer,
    then upload slides to GCS for public access.

    Args:
        headline:         Hook headline for the cover slide.
        key_stats:        Bullet-point stats for content slide(s).
        image_url:        Optional URL of a story-relevant image for the cover.
        hook_stat_value:  Big number for slide 2 (e.g. "70%").
        hook_stat_label:  Context label for slide 2.
        source_url:       Source article URL — adds a "Read More" slide if present.
        content_type:     "news" (default) or "educational".
        carousel_format:  "A" (Mistakes), "B" (Pillars), "C" (Cheat Sheet), or None (legacy).
        template_id:      Visual theme — "dark_tech" or "clean_light".

    Returns:
        CarouselResult with public https:// export_urls (or file:// on GCS failure).
    """
    design_id = f"carousel-{uuid.uuid4().hex[:8]}"
    output_dir = f"/tmp/{design_id}"

    try:
        image_bytes: Optional[bytes] = None
        if image_url:
            image_bytes = await _fetch_image_bytes(image_url)

        # Listicle format: fetch logos for each tool, then route to educational renderer
        tool_logos: Optional[dict[str, Optional[bytes]]] = None
        if carousel_format == "listicle":
            tool_logos = await _fetch_tool_logos(key_stats)

        if content_type == "educational" or carousel_format == "listicle":
            paths = render_educational_carousel(
                headline=headline,
                stats=key_stats,
                image_bytes=image_bytes,
                hook_stat_value=hook_stat_value,
                hook_stat_label=hook_stat_label,
                output_dir=output_dir,
                source_url=source_url,
                carousel_format=carousel_format,
                template_id=template_id,
                tool_logos=tool_logos,
            )
        else:
            paths = render_carousel(
                headline=headline,
                stats=key_stats,
                image_bytes=image_bytes,
                hook_stat_value=hook_stat_value,
                hook_stat_label=hook_stat_label,
                output_dir=output_dir,
                source_url=source_url,
                content_type=content_type,
                carousel_format=carousel_format,
                template_id=template_id,
            )

        # Upload all slides to GCS in parallel
        upload_tasks = [
            asyncio.to_thread(_upload_sync, path, f"{design_id}/slide{i}.png")
            for i, path in enumerate(paths, start=1)
        ]
        export_urls = list(await asyncio.gather(*upload_tasks))

        logger.info(
            f"Carousel ready for '{headline[:50]}': "
            f"{len(paths)} slides → {export_urls[0] if export_urls else 'none'}"
        )

        return CarouselResult(
            design_id=design_id,
            export_urls=export_urls,
            slide_count=len(paths),
            success=True,
            image_url=image_url,
        )

    except Exception as e:
        logger.error(f"Carousel render failed for '{headline[:50]}': {e}", exc_info=True)
        return CarouselResult(
            design_id=design_id,
            export_urls=[],
            slide_count=0,
            success=False,
            error=str(e),
        )
