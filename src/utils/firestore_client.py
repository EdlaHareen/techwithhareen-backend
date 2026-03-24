"""
Firestore client — job logging, Gmail historyId cursor, and v2 post/job queue.

Collections:
  failed_jobs   — stories that failed the analyzer after retry (v1)
  gmail_state   — stores the current historyId cursor (v1, single document)
  jobs          — research jobs created from Web UI (v2)
  posts         — all posts pending/approved/rejected approval (v2)
"""

import logging
import os
from typing import Literal, Optional

from google.cloud import firestore

from src.utils.story import Story

logger = logging.getLogger(__name__)

_client: Optional[firestore.AsyncClient] = None

GMAIL_STATE_DOC = "gmail_state/cursor"
FAILED_JOBS_COLLECTION = "failed_jobs"
JOBS_COLLECTION = "jobs"
POSTS_COLLECTION = "posts"

JobStatus = Literal["researching", "creating", "analyzing", "ready", "failed"]
PostStatus = Literal["pending", "approved", "rejected"]


def _get_client() -> firestore.AsyncClient:
    global _client
    if _client is None:
        project_id = os.environ.get("GCP_PROJECT_ID")
        _client = firestore.AsyncClient(project=project_id)
    return _client


async def get_history_id() -> Optional[str]:
    """Get the stored Gmail historyId cursor."""
    try:
        client = _get_client()
        doc = await client.document(GMAIL_STATE_DOC).get()
        if doc.exists:
            return doc.to_dict().get("history_id")
        return None
    except Exception as e:
        logger.error(f"Failed to get historyId from Firestore: {e}")
        return None


async def store_history_id(history_id: str) -> None:
    """Update the Gmail historyId cursor."""
    try:
        client = _get_client()
        await client.document(GMAIL_STATE_DOC).set(
            {"history_id": history_id, "updated_at": firestore.SERVER_TIMESTAMP}
        )
        logger.debug(f"Stored historyId: {history_id}")
    except Exception as e:
        logger.error(f"Failed to store historyId: {e}")


async def log_failed_story(
    story_headline: str,
    story_url: Optional[str],
    issues: list[str],
    retry_attempted: bool,
) -> str:
    """
    Log a story that failed the post analyzer (after retry if applicable).

    Returns the Firestore document ID.
    """
    try:
        client = _get_client()
        doc_data = {
            "headline": story_headline,
            "url": story_url,
            "issues": issues,
            "retry_attempted": retry_attempted,
            "status": "failed",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        _, doc_ref = await client.collection(FAILED_JOBS_COLLECTION).add(doc_data)
        logger.info(f"Logged failed story to Firestore: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        logger.error(f"Failed to log story to Firestore: {e}")
        return ""


# ---------------------------------------------------------------------------
# v2 — Jobs
# ---------------------------------------------------------------------------

async def create_job(topic: str) -> str:
    """
    Create a new research job for a Web UI topic request.

    Returns the Firestore document ID (job_id).
    """
    client = _get_client()
    _, doc_ref = await client.collection(JOBS_COLLECTION).add({
        "topic": topic,
        "status": "researching",
        "story_ids": [],
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    logger.info(f"Created job {doc_ref.id} for topic: {topic!r}")
    return doc_ref.id


async def update_job_status(job_id: str, status: JobStatus, story_ids: Optional[list[str]] = None) -> None:
    """Update the status (and optionally story_ids) of a research job."""
    client = _get_client()
    data: dict = {"status": status}
    if story_ids is not None:
        data["story_ids"] = story_ids
    await client.collection(JOBS_COLLECTION).document(job_id).update(data)
    logger.info(f"Job {job_id} → {status}")


async def get_job(job_id: str) -> Optional[dict]:
    """Fetch a job document. Returns None if not found."""
    try:
        client = _get_client()
        doc = await client.collection(JOBS_COLLECTION).document(job_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# v2 — Posts
# ---------------------------------------------------------------------------

async def create_post(
    story: Story,
    slides: list[str],
    caption: str,
    source: Literal["newsletter", "web_ui"],
) -> str:
    """
    Persist a completed post (slides + caption) to the approval queue.

    Returns the Firestore document ID (post_id).
    """
    client = _get_client()
    _, doc_ref = await client.collection(POSTS_COLLECTION).add({
        "story": story.to_dict(),
        "slides": slides,
        "caption": caption,
        "status": "pending",
        "source": source,
        "telegram_sent": False,
        "created_at": firestore.SERVER_TIMESTAMP,
        "approved_at": None,
        "rejection_reason": None,
    })
    logger.info(f"Created post {doc_ref.id} ({source}): {story.headline!r}")
    return doc_ref.id


async def get_post(post_id: str) -> Optional[dict]:
    """Fetch a post document. Returns None if not found."""
    try:
        client = _get_client()
        doc = await client.collection(POSTS_COLLECTION).document(post_id).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        logger.error(f"Failed to get post {post_id}: {e}")
        return None


async def list_posts(status: Optional[PostStatus] = None) -> list[dict]:
    """
    List all posts, optionally filtered by status.
    Ordered by created_at descending.

    Filtering is done client-side to avoid requiring a Firestore composite
    index on (status, created_at).
    """
    try:
        client = _get_client()
        query = client.collection(POSTS_COLLECTION).order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )
        docs = await query.get()
        posts = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        if status:
            posts = [p for p in posts if p.get("status") == status]
        return posts
    except Exception as e:
        logger.error(f"Failed to list posts: {e}")
        return []


async def approve_post(post_id: str) -> None:
    """Mark a post as approved."""
    client = _get_client()
    await client.collection(POSTS_COLLECTION).document(post_id).update({
        "status": "approved",
        "approved_at": firestore.SERVER_TIMESTAMP,
    })
    logger.info(f"Post {post_id} approved")


async def reject_post(post_id: str, reason: str = "") -> None:
    """Mark a post as rejected with an optional reason."""
    client = _get_client()
    await client.collection(POSTS_COLLECTION).document(post_id).update({
        "status": "rejected",
        "rejection_reason": reason,
    })
    logger.info(f"Post {post_id} rejected")


async def update_post_caption(post_id: str, caption: str) -> None:
    """Update the caption of a pending post (inline edit before approval)."""
    client = _get_client()
    await client.collection(POSTS_COLLECTION).document(post_id).update({
        "caption": caption,
    })
    logger.info(f"Post {post_id} caption updated")


async def mark_telegram_sent(post_id: str) -> None:
    """Mark that this post was forwarded to Telegram."""
    client = _get_client()
    await client.collection(POSTS_COLLECTION).document(post_id).update({
        "telegram_sent": True,
    })
    logger.info(f"Post {post_id} marked telegram_sent")
