"""Gmail API client — OAuth2 auth, Pub/Sub notification decoding, history fetching."""

import base64
import json
import logging
import os
import pickle
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.utils.firestore_client import get_history_id, store_history_id

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",  # needed for watch()
]

RUNDOWNAI_SENDER = "news@daily.therundown.ai"


def get_gmail_service():
    """Build an authenticated Gmail API service using OAuth2 credentials."""
    creds = None
    # GMAIL_TOKEN_PATH is always writable (/tmp/token.pickle in Cloud Run)
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "/tmp/token.pickle")
    credentials_path = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")

    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
    else:
        # Cloud Run: GMAIL_TOKEN_B64 env var holds the base64-encoded token.pickle
        # (injected from Secret Manager). Decode it to /tmp on first use.
        token_b64 = os.environ.get("GMAIL_TOKEN_B64", "")
        if token_b64:
            raw = base64.b64decode(token_b64)
            with open(token_path, "wb") as f:
                f.write(raw)
            with open(token_path, "rb") as f:
                creds = pickle.load(f)
            logger.info("Gmail token decoded from GMAIL_TOKEN_B64 env var")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError(
                "Gmail token missing or invalid and cannot do interactive OAuth in Cloud Run. "
                "Re-run scripts/setup_gmail_watch.py locally to generate a fresh token."
            )

        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


def decode_pubsub_notification(envelope: dict) -> Optional[dict]:
    """
    Decode a Pub/Sub push envelope to extract the Gmail notification.

    Gmail sends: {"emailAddress": "...", "historyId": "123456"}
    The data is base64url-encoded — must add padding before decoding.
    """
    try:
        message = envelope.get("message", {})
        data = message.get("data", "")
        if not data:
            logger.warning("Pub/Sub message has no data field")
            return None

        # base64url decode with padding fix
        decoded = base64.urlsafe_b64decode(data + "==")
        notification = json.loads(decoded)
        logger.info(f"Gmail notification: {notification}")
        return notification
    except Exception as e:
        logger.error(f"Failed to decode Pub/Sub notification: {e}")
        return None


def get_history_since(service, start_history_id: str) -> list[dict]:
    """
    Fetch all new messages added since start_history_id.
    Returns list of message stubs: [{"id": "...", "threadId": "..."}]
    """
    messages = []
    try:
        result = service.users().history().list(
            userId="me",
            startHistoryId=start_history_id,
            historyTypes=["messageAdded"],
        ).execute()

        for record in result.get("history", []):
            for msg in record.get("messagesAdded", []):
                messages.append(msg["message"])

        logger.info(f"Found {len(messages)} new messages since historyId {start_history_id}")
    except Exception as e:
        logger.error(f"history.list() failed: {e}")

    return messages


def get_message(service, message_id: str) -> Optional[dict]:
    """Fetch a full Gmail message by ID."""
    try:
        return service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()
    except Exception as e:
        logger.error(f"Failed to fetch message {message_id}: {e}")
        return None


def extract_html_body(payload: dict) -> Optional[str]:
    """Recursively extract HTML body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = extract_html_body(part)
        if result:
            return result

    return None


def is_from_rundownai(message: dict) -> bool:
    """Check if a message is from the rundownai newsletter."""
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
    sender = headers.get("from", "")
    return RUNDOWNAI_SENDER in sender.lower()


async def process_gmail_notification(notification: dict, orchestrator) -> None:
    """
    Main handler: called when Gmail Pub/Sub notification arrives.
    Fetches new messages, filters for rundownai, triggers orchestrator.
    """
    new_history_id = notification.get("historyId")
    if not new_history_id:
        logger.warning("Notification missing historyId")
        return

    service = get_gmail_service()

    # Get the last stored historyId as our cursor
    last_history_id = await get_history_id()
    if not last_history_id:
        logger.info("No previous historyId stored — storing current and waiting for next notification")
        await store_history_id(new_history_id)
        return

    # Fetch messages added since last check
    new_messages = get_history_since(service, last_history_id)

    # Advance the cursor
    await store_history_id(new_history_id)

    # Filter for rundownai newsletter
    for msg_stub in new_messages:
        message = get_message(service, msg_stub["id"])
        if message and is_from_rundownai(message):
            html_body = extract_html_body(message["payload"])
            if html_body:
                logger.info(f"Found rundownai newsletter (msg_id={msg_stub['id']}), triggering pipeline")
                await orchestrator.run(html_body)
            else:
                logger.warning(f"rundownai message {msg_stub['id']} has no HTML body")


async def setup_gmail_watch(service, topic_name: str) -> str:
    """Set up Gmail push notifications. Returns the initial historyId."""
    request_body = {
        "labelIds": ["INBOX"],
        "topicName": topic_name,
        "labelFilterBehavior": "INCLUDE",
    }
    response = service.users().watch(userId="me", body=request_body).execute()
    history_id = response["historyId"]
    await store_history_id(history_id)
    logger.info(f"Gmail watch set up. historyId: {history_id}, expiry: {response.get('expiration')}")
    return history_id


async def renew_gmail_watch() -> str:
    """Renew the Gmail watch (call daily — watch expires every 7 days)."""
    project_id = os.environ["GCP_PROJECT_ID"]
    topic_name = f"projects/{project_id}/topics/gmail-notifications"
    service = get_gmail_service()
    return await setup_gmail_watch(service, topic_name)
