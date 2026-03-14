"""
Post Creator Agent — creates Instagram carousel posts in Canva for each story.

Pipeline per story:
  1. Search for a relevant image via Serper.dev
  2. Open Canva template via claude-agent-sdk + Canva MCP
  3. Fill in story content (hook, stats, brand)
  4. Export slides as PNG
"""

import logging

from src.agents.content_fetcher.newsletter_parser import Story
from src.agents.post_creator.image_fetcher import search_image, build_image_query
from src.utils.canva_session import CarouselResult, create_carousel

logger = logging.getLogger(__name__)


class PostCreatorAgent:
    """Creates a Canva carousel for a given story."""

    async def run(self, story: Story) -> CarouselResult:
        """
        Create a carousel post for a story.

        Args:
            story: Structured story from ContentFetcherAgent.

        Returns:
            CarouselResult with export URLs, or failed result if creation fails.
        """
        logger.info(f"PostCreatorAgent: creating carousel for '{story.headline[:60]}'")

        # Step 1: Fetch relevant image
        image_query = build_image_query(story.headline)
        image_url = await search_image(image_query)
        if image_url:
            logger.info(f"  Image found: {image_url[:60]}")
        else:
            logger.info("  No image found — proceeding without image")

        # Step 2: Create carousel
        result = await create_carousel(
            headline=story.headline,
            key_stats=story.key_stats if story.key_stats else [story.summary],
            image_url=image_url,
            hook_stat_value=story.hook_stat_value,
            hook_stat_label=story.hook_stat_label,
        )

        if result.success:
            logger.info(
                f"PostCreatorAgent: ✅ carousel created "
                f"({result.slide_count} slides, design_id={result.design_id})"
            )
        else:
            logger.error(
                f"PostCreatorAgent: ❌ carousel failed for '{story.headline[:60]}': {result.error}"
            )

        return result
