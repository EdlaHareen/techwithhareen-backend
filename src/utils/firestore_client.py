"""
Firestore client — minimal job logging and Gmail historyId cursor storage.

Collections:
  failed_jobs   — stories that failed the analyzer after retry
  gmail_state   — stores the current historyId cursor (single document)
"""

import logging
import os
from typing import Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)

_client: Optional[firestore.AsyncClient] = None

GMAIL_STATE_DOC = "gmail_state/cursor"
FAILED_JOBS_COLLECTION = "failed_jobs"


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
