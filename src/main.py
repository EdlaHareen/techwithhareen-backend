"""
Cloud Run entry point — FastAPI app.

Routes:
  POST /pubsub/push      — Gmail Pub/Sub push notification
  POST /telegram/webhook — Telegram bot webhook
  POST /renew-watch      — Renew Gmail watch() (called by Cloud Scheduler daily)
  GET  /healthz          — Liveness probe
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from src.agents.telegram_bot.bot import dp, bot, register_webhook
from src.orchestrator.handler import InstaHandlerManager
from src.utils.gmail_client import decode_pubsub_notification, process_gmail_notification
from aiogram.types import Update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

orchestrator = InstaHandlerManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register Telegram webhook on startup."""
    await register_webhook()
    logger.info("Telegram webhook registered.")
    yield
    await bot.session.close()


app = FastAPI(title="Insta Handler Manager", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/pubsub/push")
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

        # Fire and forget — Pub/Sub only needs a fast ack
        asyncio.create_task(
            process_gmail_notification(notification, orchestrator)
        )
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"pubsub_push error: {e}", exc_info=True)
        # Return 200 anyway to avoid Pub/Sub infinite retries on bad messages
        return Response(status_code=200)


@app.post("/telegram/webhook")
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


@app.post("/renew-watch")
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
