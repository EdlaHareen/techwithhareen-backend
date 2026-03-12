"""
Insta Handler Manager — top-level orchestrator.

Pipeline:
  1. ContentFetcherAgent  — extract stories from newsletter HTML
  2. Per story in parallel:
       PostCreatorAgent   — create Canva carousel + fetch image
       CaptionWriterAgent — write Instagram caption
       PostAnalyzerAgent  — quality check (1 auto-fix retry)
  3. Burst-send all passing posts to Telegram for approval
  4. Send failure alerts for skipped stories
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from src.agents.caption_writer.agent import Caption, CaptionWriterAgent
from src.agents.content_fetcher.agent import ContentFetcherAgent
from src.agents.content_fetcher.newsletter_parser import Story
from src.agents.post_analyzer.agent import AnalysisResult, PostAnalyzerAgent
from src.agents.post_creator.agent import PostCreatorAgent
from src.agents.telegram_bot.bot import send_failure_alert, send_post_for_approval
from src.publishing.publisher import register_pending_post
from src.utils.canva_session import CarouselResult
from src.utils.firestore_client import log_failed_story

logger = logging.getLogger(__name__)


@dataclass
class StoryResult:
    """Holds the complete output for one story through the pipeline."""
    story_id: str
    story: Story
    carousel: Optional[CarouselResult] = None
    caption: Optional[Caption] = None
    analysis: Optional[AnalysisResult] = None
    passed: bool = False
    skip_reason: Optional[str] = None


class InstaHandlerManager:
    """
    Orchestrates the full pipeline from newsletter HTML to Telegram approval.
    """

    def __init__(self):
        self._content_fetcher = ContentFetcherAgent()
        self._post_creator = PostCreatorAgent()
        self._caption_writer = CaptionWriterAgent()
        self._post_analyzer = PostAnalyzerAgent()

    async def run(self, newsletter_html: str) -> None:
        """
        Full pipeline entry point. Called by main.py on Pub/Sub notification.

        Args:
            newsletter_html: Raw HTML of the rundownai newsletter.
        """
        logger.info("=== InstaHandlerManager: pipeline started ===")

        # Step 1: Extract stories
        stories = await self._content_fetcher.run(newsletter_html)
        if not stories:
            logger.warning("No stories extracted — pipeline stopping")
            return

        logger.info(f"Processing {len(stories)} stories in parallel")

        # Step 2: Process all stories concurrently
        results = await asyncio.gather(
            *[self._process_story(story) for story in stories],
            return_exceptions=True,
        )

        passing = []
        failed = []

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Story pipeline raised exception: {result}", exc_info=result)
                continue
            if result.passed:
                passing.append(result)
            else:
                failed.append(result)

        logger.info(f"Results: {len(passing)} passing, {len(failed)} failed/skipped")

        # Step 3: Burst-send all passing posts to Telegram
        for result in passing:
            await send_post_for_approval(
                story_id=result.story_id,
                headline=result.story.headline,
                slide_urls=result.carousel.export_urls if result.carousel else [],
                caption_text=result.caption.full_text if result.caption else "",
            )

        # Step 4: Send failure alerts for skipped stories
        for result in failed:
            issues = result.analysis.issues if result.analysis else [result.skip_reason or "Unknown error"]
            await send_failure_alert(
                story_id=result.story_id,
                headline=result.story.headline,
                issues=issues,
            )

        logger.info("=== InstaHandlerManager: pipeline complete ===")

    async def _process_story(self, story: Story) -> StoryResult:
        """
        Run the full pipeline for a single story.
        Includes 1 auto-fix retry on analysis failure.
        """
        story_id = str(uuid.uuid4())[:8]
        result = StoryResult(story_id=story_id, story=story)

        try:
            # Run PostCreator + CaptionWriter concurrently
            carousel, caption = await asyncio.gather(
                self._post_creator.run(story),
                self._caption_writer.run(story, None),  # carousel not needed for caption
            )
            result.carousel = carousel
            result.caption = caption

            # First analysis pass
            analysis = await self._post_analyzer.run(story, carousel, caption)

            if analysis.passed:
                result.analysis = analysis
                result.passed = True
                _register(result)
                return result

            # --- Auto-fix retry ---
            logger.info(
                f"Story '{story.headline[:50]}' failed analysis — "
                f"attempting auto-fix with instructions: {analysis.fix_instructions}"
            )

            # Re-run creator + caption with fix instructions injected into context
            fixed_carousel, fixed_caption = await asyncio.gather(
                self._post_creator.run(story),      # re-create carousel
                self._caption_writer.run(story, carousel),  # re-write caption with context
            )
            result.carousel = fixed_carousel
            result.caption = fixed_caption

            # Second analysis pass
            analysis2 = await self._post_analyzer.run(story, fixed_carousel, fixed_caption)
            result.analysis = analysis2

            if analysis2.passed:
                result.passed = True
                _register(result)
                logger.info(f"Auto-fix succeeded for '{story.headline[:50]}'")
            else:
                result.passed = False
                result.skip_reason = f"Failed after retry: {'; '.join(analysis2.issues)}"
                logger.warning(f"Story skipped after retry: '{story.headline[:50]}'")
                await log_failed_story(
                    story_headline=story.headline,
                    story_url=story.url,
                    issues=analysis2.issues,
                    retry_attempted=True,
                )

        except Exception as e:
            logger.error(
                f"Pipeline exception for '{story.headline[:50]}': {e}", exc_info=True
            )
            result.passed = False
            result.skip_reason = str(e)
            await log_failed_story(
                story_headline=story.headline,
                story_url=story.url,
                issues=[str(e)],
                retry_attempted=False,
            )

        return result


def _register(result: StoryResult) -> None:
    """Register a passing post with the publisher for downstream use."""
    register_pending_post(
        story_id=result.story_id,
        post_data={
            "headline": result.story.headline,
            "export_urls": result.carousel.export_urls if result.carousel else [],
            "caption_text": result.caption.full_text if result.caption else "",
        },
    )
