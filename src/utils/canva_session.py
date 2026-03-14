"""
Canva Session — carousel creation via Pillow renderer.

Replaces the previous claude-agent-sdk + Canva MCP approach with a local
Pillow-based PNG renderer (src/utils/carousel_renderer.py).

The public interface (CarouselResult, create_carousel) is unchanged so that
PostCreatorAgent and the orchestrator require no modifications.
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx

from src.utils.carousel_renderer import render_carousel

logger = logging.getLogger(__name__)

BRAND_NAME = "@techwithhareen"


@dataclass
class CarouselResult:
    """Result from Post Creator Agent."""
    design_id: str
    export_urls: list[str] = field(default_factory=list)
    slide_count: int = 0
    success: bool = True
    error: Optional[str] = None


async def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """Download image bytes from a URL for compositing onto slide 3."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning(f"Could not download image from {url}: {e}")
        return None


async def create_carousel(
    headline: str,
    key_stats: list[str],
    image_url: Optional[str] = None,
    hook_stat_value: str = "",
    hook_stat_label: str = "",
) -> CarouselResult:
    """
    Create an Instagram carousel using the Pillow-based renderer.

    Args:
        headline:         Hook headline for the cover slide.
        key_stats:        Bullet-point stats for content slide(s).
        image_url:        Optional URL of a story-relevant image for the cover.
        hook_stat_value:  Big number for slide 2 (e.g. "70%").
        hook_stat_label:  Context label for slide 2 (e.g. "OF SAMSUNG RAM GOES TO NVIDIA").

    Returns:
        CarouselResult with file:// export_urls pointing to the generated PNGs.
    """
    design_id = f"local-{uuid.uuid4().hex[:8]}"
    output_dir = f"/tmp/carousel_{design_id}"

    try:
        image_bytes: Optional[bytes] = None
        if image_url:
            image_bytes = await _fetch_image_bytes(image_url)

        paths = render_carousel(
            headline=headline,
            stats=key_stats,
            image_bytes=image_bytes,
            hook_stat_value=hook_stat_value,
            hook_stat_label=hook_stat_label,
            output_dir=output_dir,
        )

        export_urls = [f"file://{p}" for p in paths]

        logger.info(
            f"Carousel rendered for '{headline[:50]}': "
            f"{len(paths)} slides, output_dir={output_dir}"
        )

        return CarouselResult(
            design_id=design_id,
            export_urls=export_urls,
            slide_count=len(paths),
            success=True,
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
