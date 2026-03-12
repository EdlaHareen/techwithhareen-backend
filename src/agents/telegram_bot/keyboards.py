"""Inline keyboard builders for Telegram approval flow."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_approval_keyboard(story_id: str) -> InlineKeyboardMarkup:
    """Build Approve / Reject inline keyboard for a post."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{story_id}"),
        InlineKeyboardButton(text="❌ Reject",  callback_data=f"reject:{story_id}"),
    ]])
