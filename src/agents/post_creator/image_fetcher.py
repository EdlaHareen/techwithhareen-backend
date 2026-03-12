"""
Image Fetcher — searches Google Images via Serper.dev for story-relevant images.

Validates the returned URL with a HEAD request to avoid broken image links.
Returns None gracefully if no suitable image is found.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SERPER_IMAGES_URL = "https://google.serper.dev/images"


async def search_image(query: str, num_results: int = 5) -> Optional[str]:
    """
    Search for a relevant image using Serper.dev Google Images API.

    Args:
        query: Search query derived from story headline (e.g., "Microsoft Copilot AI")
        num_results: Number of results to fetch before picking the best valid one

    Returns:
        URL of a valid image, or None if not found.
    """
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        logger.warning("SERPER_API_KEY not set — skipping image search")
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SERPER_IMAGES_URL,
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            images = response.json().get("images", [])

        if not images:
            logger.info(f"No images found for query: {query}")
            return None

        # Try each image URL until we find one that actually loads
        for image in images:
            url = image.get("imageUrl")
            if url and await _validate_image_url(url):
                logger.info(f"Found valid image for '{query}': {url[:80]}")
                return url

        logger.warning(f"All image URLs invalid for query: {query}")
        return None

    except httpx.HTTPError as e:
        logger.error(f"Serper.dev request failed: {e}")
        return None


async def _validate_image_url(url: str) -> bool:
    """Check that an image URL is reachable via HEAD request."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.head(url, follow_redirects=True)
            content_type = resp.headers.get("content-type", "")
            return resp.status_code == 200 and "image" in content_type
    except Exception:
        return False


def build_image_query(headline: str) -> str:
    """
    Build a clean image search query from a story headline.
    Strips common filler words to get a more targeted search.
    """
    # Remove common newsletter prefixes
    for prefix in ["breaking:", "exclusive:", "report:", "new:"]:
        if headline.lower().startswith(prefix):
            headline = headline[len(prefix):].strip()

    # Limit to first ~8 words for a focused query
    words = headline.split()[:8]
    return " ".join(words)
