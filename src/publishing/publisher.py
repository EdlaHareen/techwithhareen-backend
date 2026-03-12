"""
Publishing Module — pluggable stub for Instagram publishing.

Currently: exports Canva slides as PNG and logs the approval.
Future: integrate Instagram Graph API or Buffer scheduling.
"""

import logging

logger = logging.getLogger(__name__)

# In-memory store for pending approvals: story_id → post data
# In production this should be Firestore or Redis
_pending_posts: dict[str, dict] = {}


def register_pending_post(story_id: str, post_data: dict) -> None:
    """Register a post as pending approval."""
    _pending_posts[story_id] = post_data


async def trigger_downstream(story_id: str, approved: bool) -> None:
    """
    Called by Telegram bot when owner approves or rejects a post.

    Currently a stub — logs the decision and returns export URLs.
    Replace this with Instagram Graph API calls when ready.
    """
    post_data = _pending_posts.pop(story_id, {})
    headline = post_data.get("headline", story_id)

    if approved:
        export_urls = post_data.get("export_urls", [])
        caption = post_data.get("caption_text", "")

        logger.info(
            f"✅ Post APPROVED: '{headline[:60]}'\n"
            f"   Slides: {len(export_urls)}\n"
            f"   Caption preview: {caption[:100]}...\n"
            f"   Export URLs: {export_urls}"
        )

        # TODO: Replace with actual Instagram publishing:
        # from src.publishing.instagram import post_carousel
        # await post_carousel(export_urls, caption)

        logger.info(
            "📋 Manual post reminder: Download the slides from the URLs above "
            "and post to @techwithhareen manually."
        )
    else:
        logger.info(f"❌ Post REJECTED: '{headline[:60]}'")


async def publish(story_id: str, slide_urls: list[str], caption_text: str) -> dict:
    """
    Stub publisher — returns pending_manual status.
    Will be replaced with real Instagram API integration.
    """
    logger.info(f"publish() called for story_id={story_id} — manual export mode")
    return {
        "status": "pending_manual",
        "story_id": story_id,
        "slide_count": len(slide_urls),
        "message": "Download slides and post manually to @techwithhareen",
    }
