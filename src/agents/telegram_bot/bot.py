"""
Telegram Bot — aiogram 3.x bot for post approval flow.

Flow:
  1. Orchestrator calls send_post_for_approval() after all posts are ready
  2. Bot sends carousel images (as album) + caption + Approve/Reject keyboard
  3. Owner taps Approve → trigger_downstream() called → publisher.py stub
  4. Owner taps Reject → silent dismiss, keyboard removed
  5. On story failure → send_failure_alert() sends plain text notification
"""

import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    CallbackQuery,
    InputMediaPhoto,
    Message,
)

from src.agents.telegram_bot.keyboards import build_approval_keyboard

logger = logging.getLogger(__name__)

# Bot and dispatcher — initialized at module level for reuse across requests
_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
_redis_port = int(os.environ.get("REDIS_PORT", "6379"))
_owner_chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID", "")
_webhook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

bot = Bot(token=_bot_token)

storage = RedisStorage.from_url(f"redis://{_redis_host}:{_redis_port}")
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """
    /start — store the user's chat ID so we know where to send posts.
    Only the owner should use this.
    """
    chat_id = str(message.chat.id)
    logger.info(f"/start from chat_id={chat_id}")
    await message.answer(
        f"👋 @techwithhareen bot ready!\n\n"
        f"Your chat ID is: `{chat_id}`\n\n"
        f"Add this to Secret Manager as `telegram-owner-chat-id`.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Callback query handlers (Approve / Reject buttons)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("approve:"))
async def handle_approve(query: CallbackQuery) -> None:
    story_id = query.data.split(":", 1)[1]
    logger.info(f"Post approved: story_id={story_id}")

    await query.answer("✅ Approved! Publishing now...")
    # Remove keyboard to prevent re-tapping
    await query.message.edit_reply_markup(reply_markup=None)

    # Trigger publishing
    try:
        from src.publishing.publisher import trigger_downstream
        await trigger_downstream(story_id, approved=True)
    except Exception as e:
        logger.error(f"trigger_downstream failed for story {story_id}: {e}")
        await bot.send_message(
            chat_id=query.message.chat.id,
            text=f"⚠️ Approved but publish failed: {e}",
        )


@router.callback_query(F.data.startswith("reject:"))
async def handle_reject(query: CallbackQuery) -> None:
    story_id = query.data.split(":", 1)[1]
    logger.info(f"Post rejected: story_id={story_id}")

    await query.answer("❌ Rejected.")
    await query.message.edit_reply_markup(reply_markup=None)

    try:
        from src.publishing.publisher import trigger_downstream
        await trigger_downstream(story_id, approved=False)
    except Exception as e:
        logger.error(f"trigger_downstream (reject) failed: {e}")


# ---------------------------------------------------------------------------
# Public API used by orchestrator
# ---------------------------------------------------------------------------

async def send_post_for_approval(
    story_id: str,
    headline: str,
    slide_urls: list[str],
    caption_text: str,
) -> None:
    """
    Send a post to the owner for approval on Telegram.

    Sends slide images as a photo album, followed by the caption
    and an Approve/Reject inline keyboard.
    """
    chat_id = _owner_chat_id
    if not chat_id:
        logger.error("TELEGRAM_OWNER_CHAT_ID not set — cannot send approval request")
        return

    try:
        if slide_urls:
            from aiogram.types import FSInputFile, BufferedInputFile
            media = []
            for url in slide_urls[:10]:
                if url.startswith("file://"):
                    # Local file — send bytes directly
                    path = url[len("file://"):]
                    media.append(InputMediaPhoto(media=FSInputFile(path)))
                else:
                    media.append(InputMediaPhoto(media=url))
            await bot.send_media_group(chat_id=chat_id, media=media)

        # Send approval header + keyboard
        short_headline = headline[:60] + ("..." if len(headline) > 60 else "")
        approval_text = (
            f"📸 *New post ready for approval*\n"
            f"_{short_headline}_"
        )
        await bot.send_message(
            chat_id=chat_id,
            text=approval_text,
            parse_mode="Markdown",
            reply_markup=build_approval_keyboard(story_id),
        )

        # Send full caption as a separate message (Telegram caps inline captions at 1024 chars)
        if caption_text:
            await bot.send_message(
                chat_id=chat_id,
                text=caption_text,
            )
        logger.info(f"Sent approval request for story_id={story_id}")

    except Exception as e:
        logger.error(f"Failed to send approval for story_id={story_id}: {e}", exc_info=True)


async def send_failure_alert(
    story_id: str,
    headline: str,
    issues: list[str],
) -> None:
    """Send a plain text alert when a story is skipped after failed analysis."""
    chat_id = _owner_chat_id
    if not chat_id:
        return

    issues_text = "\n".join(f"• {issue}" for issue in issues)
    message = (
        f"⚠️ *Story skipped after failed analysis*\n\n"
        f"*Headline:* {headline[:80]}\n\n"
        f"*Issues:*\n{issues_text}"
    )
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to send failure alert: {e}")


async def register_webhook() -> None:
    """Register Telegram webhook on service startup."""
    import asyncio
    from aiogram.exceptions import TelegramRetryAfter

    service_url = os.environ.get("SERVICE_URL", "")
    if not service_url:
        logger.warning("SERVICE_URL not set — skipping webhook registration (OK for local dev)")
        return

    webhook_url = f"{service_url}/telegram/webhook"
    for attempt in range(5):
        try:
            await bot.set_webhook(
                url=webhook_url,
                secret_token=_webhook_secret or None,
                drop_pending_updates=True,
            )
            logger.info(f"Telegram webhook registered: {webhook_url}")
            return
        except TelegramRetryAfter as e:
            wait = e.retry_after + 1
            logger.warning(f"Telegram flood control on SetWebhook, waiting {wait}s (attempt {attempt+1})")
            await asyncio.sleep(wait)
    logger.error("Failed to register Telegram webhook after 5 attempts")
