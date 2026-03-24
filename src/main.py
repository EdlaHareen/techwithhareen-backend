"""
Cloud Run entry point — FastAPI app.

Registers all API routers and handles application lifespan (Telegram webhook).
Routes are defined in:
  src/api/routes_v1.py — Gmail, Telegram, test endpoint
  src/api/routes_v2.py — Web UI, research pipeline

CORS:
  Allowed origins are read from the CORS_ORIGINS env var (comma-separated).
  In production: set to the Vercel frontend URL.
  In local dev: add http://localhost:5173 to .env.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agents.telegram_bot.bot import bot, register_webhook
from src.api.routes_v1 import router as v1_router
from src.api.routes_v2 import router as v2_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_cors_origins() -> list[str]:
    """
    Read allowed CORS origins from CORS_ORIGINS env var.
    Falls back to localhost:5173 for local development if not set.
    """
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register Telegram webhook on startup, clean up on shutdown."""
    await register_webhook()
    logger.info("Telegram webhook registered.")
    yield
    await bot.session.close()


app = FastAPI(title="Insta Handler Manager", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(v1_router)
app.include_router(v2_router)
