"""
v1 API routes — Gmail Pub/Sub, Telegram webhook, Gmail watch renewal, and test endpoint.

Inputs:
  POST /pubsub/push      — Gmail Pub/Sub push notification (triggers newsletter pipeline)
  POST /telegram/webhook — Telegram bot webhook (approve/reject posts)
  POST /renew-watch      — Renew Gmail watch() (called daily by Cloud Scheduler)
  POST /test/story       — Dev/test: run a single story through the pipeline
  GET  /healthz          — Liveness probe
"""

import asyncio
import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.agents.telegram_bot.bot import dp, bot
from src.orchestrator.handler import InstaHandlerManager
from src.utils.gmail_client import decode_pubsub_notification, process_gmail_notification
from aiogram.types import Update

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = InstaHandlerManager()


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.post("/pubsub/push")
async def pubsub_push(request: Request):
    """
    Receives Gmail Pub/Sub push notification.
    Decodes the notification, extracts new message IDs, and triggers the pipeline.
    Returns HTTP 200 immediately — heavy work runs in background.
    """
    try:
        envelope = await request.json()
        notification = decode_pubsub_notification(envelope)
        if notification is None:
            return Response(status_code=400)

        asyncio.create_task(
            process_gmail_notification(notification, orchestrator)
        )
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"pubsub_push error: {e}", exc_info=True)
        return Response(status_code=200)  # Always 200 to prevent Pub/Sub infinite retries


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receives Telegram webhook updates and dispatches to aiogram."""
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"telegram_webhook error: {e}", exc_info=True)
        return Response(status_code=200)


class TestStoryRequest(BaseModel):
    headline: str
    summary: str
    url: str = "https://example.com"


@router.post("/test/story")
async def test_story(payload: TestStoryRequest):
    """
    Dev/test endpoint — runs a single story through the full pipeline
    (PostCreator → CaptionWriter → PostAnalyzer → Telegram).
    Bypasses Gmail and Pub/Sub entirely.
    """
    from src.utils.story import Story
    story = Story(
        headline=payload.headline,
        summary=payload.summary,
        url=payload.url,
    )
    asyncio.create_task(orchestrator._process_story_and_send(story))
    return JSONResponse({"status": "pipeline started", "headline": payload.headline})


@router.post("/renew-watch")
async def renew_watch():
    """Called daily by Cloud Scheduler to renew Gmail watch() (expires every 7 days)."""
    try:
        from src.utils.gmail_client import renew_gmail_watch
        await renew_gmail_watch()
        logger.info("Gmail watch renewed.")
        return JSONResponse({"status": "renewed"})
    except Exception as e:
        logger.error(f"renew_watch error: {e}", exc_info=True)
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
