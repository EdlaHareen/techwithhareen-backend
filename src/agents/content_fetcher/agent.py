"""
Content Fetching Agent — extracts stories from rundownai newsletter HTML.

Wraps newsletter_parser with logging and error handling.
Returns a list of Story objects for downstream agents.
"""

import logging
import os

import anthropic

from src.agents.content_fetcher.newsletter_parser import (
    Story,
    html_to_markdown,
    extract_stories_with_llm,
)

logger = logging.getLogger(__name__)


class ContentFetcherAgent:
    """
    Parses a rundownai newsletter HTML body and returns structured Story objects.
    Called by the orchestrator after Gmail Pub/Sub notification triggers.
    """

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def run(self, newsletter_html: str) -> list[Story]:
        """
        Parse newsletter HTML and extract all stories.

        Args:
            newsletter_html: Raw HTML body of the rundownai newsletter email.

        Returns:
            List of Story objects. Empty list if parsing fails.
        """
        logger.info("ContentFetcherAgent: starting story extraction")

        if not newsletter_html or not newsletter_html.strip():
            logger.warning("ContentFetcherAgent: received empty newsletter HTML")
            return []

        # Convert HTML → markdown (resilient to DOM structure changes)
        markdown = html_to_markdown(newsletter_html)
        logger.debug(f"Converted newsletter to {len(markdown)} chars of markdown")

        # Extract stories using Claude Haiku
        stories = extract_stories_with_llm(markdown, self._client)

        if not stories:
            logger.warning("ContentFetcherAgent: no stories extracted from newsletter")
        else:
            logger.info(f"ContentFetcherAgent: extracted {len(stories)} stories")
            for i, story in enumerate(stories):
                logger.info(f"  Story {i+1}: {story.headline[:80]}")

        return stories
