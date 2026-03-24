"""
v2 API routes — Web UI topic research, post approval queue, and caption/slide editing.

Inputs:
  POST /api/v2/research                          — start a research job for a topic
  GET  /api/v2/jobs/{job_id}                     — poll job status + stories
  GET  /api/v2/posts                             — list all posts (filterable by status)
  GET  /api/v2/posts/{post_id}                   — get a single post
  POST /api/v2/posts/{post_id}/approve           — approve a post (triggers publisher)
  POST /api/v2/posts/{post_id}/reject            — reject a post with optional reason
  PATCH /api/v2/posts/{post_id}/caption          — edit caption before approving
  PATCH /api/v2/posts/{post_id}/slides           — edit render data + re-render all slides
  DELETE /api/v2/posts/{post_id}/slides/{index}  — remove a slide by index
  POST /api/v2/posts/{post_id}/slides/reorder    — reorder slides by index permutation
"""

import asyncio
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.agents.content_validator.validator import ContentValidator
from src.agents.research_orchestrator.orchestrator import ResearchError, ResearchOrchestrator
from src.orchestrator.handler import InstaHandlerManager
from src.publishing.publisher import register_pending_post
from src.utils import firestore_client as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2")

_research_orchestrator = ResearchOrchestrator()
_content_validator = ContentValidator()
_pipeline = InstaHandlerManager()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    topic: str


class ApproveRequest(BaseModel):
    send_to_telegram: bool = False  # opt-in — default off for web UI path


class RejectRequest(BaseModel):
    reason: str = ""


class UpdateCaptionRequest(BaseModel):
    caption: str


class UpdateSlidesRequest(BaseModel):
    headline: str
    key_stats: list[str]
    hook_stat_value: str = ""
    hook_stat_label: str = ""
    source_url: Optional[str] = None
    image_url: Optional[str] = None


class ReorderSlidesRequest(BaseModel):
    order: list[int]  # permutation of 0..N-1 representing new slide positions


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@router.post("/research")
async def start_research(body: ResearchRequest):
    """
    Start a research job for a topic.
    Research runs in the background — poll /api/v2/jobs/{job_id} for status.
    """
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be empty")

    job_id = await db.create_job(topic)
    asyncio.create_task(_run_research_pipeline(job_id, topic))

    return JSONResponse({"job_id": job_id}, status_code=202)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll a research job for status and resulting story IDs."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@router.get("/posts")
async def list_posts(
    status: Optional[Literal["pending", "approved", "rejected"]] = Query(default=None),
):
    """List all posts, optionally filtered by status."""
    posts = await db.list_posts(status=status)
    return posts


@router.get("/posts/{post_id}")
async def get_post(post_id: str):
    """Get a single post by ID."""
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts/{post_id}/approve")
async def approve_post(post_id: str, body: ApproveRequest):
    """
    Approve a post — triggers the publisher immediately.
    If send_to_telegram=True, also forwards to Telegram (opt-in, default off).
    Returns 409 if the post is not in pending state.
    """
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Post is already {post.get('status')}")

    await db.approve_post(post_id)

    story = post.get("story", {})
    slides = post.get("slides", [])
    caption = post.get("caption", "")

    # Trigger publisher (manual export stub)
    register_pending_post(
        story_id=post_id,
        post_data={
            "headline": story.get("headline", ""),
            "export_urls": slides,
            "caption_text": caption,
        },
    )

    # Optionally forward to Telegram
    if body.send_to_telegram and not post.get("telegram_sent", False):
        from src.agents.telegram_bot.bot import send_post_for_approval
        await send_post_for_approval(
            story_id=post_id,
            headline=story.get("headline", ""),
            slide_urls=slides,
            caption_text=caption,
        )
        await db.mark_telegram_sent(post_id)
        logger.info(f"Post {post_id} forwarded to Telegram on approval")

    logger.info(f"Post {post_id} approved via Web UI (telegram={body.send_to_telegram})")
    return JSONResponse({"published": True, "telegram_sent": body.send_to_telegram})


@router.post("/posts/{post_id}/reject")
async def reject_post(post_id: str, body: RejectRequest):
    """
    Reject a post with an optional reason.
    Returns 409 if the post is not in pending state.
    """
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Post is already {post.get('status')}")

    await db.reject_post(post_id, reason=body.reason)
    logger.info(f"Post {post_id} rejected via Web UI")
    return JSONResponse({"rejected": True})


@router.patch("/posts/{post_id}/caption")
async def update_caption(post_id: str, body: UpdateCaptionRequest):
    """Edit a post's caption inline before approving."""
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Can only edit caption of a pending post")

    await db.update_post_caption(post_id, caption=body.caption)
    return JSONResponse({"updated": True})


@router.patch("/posts/{post_id}/slides")
async def update_slides(post_id: str, body: UpdateSlidesRequest):
    """
    Edit a post's render data and re-render all slides.
    Re-renders the entire carousel via Pillow and uploads new PNGs to GCS.
    Returns the updated list of GCS slide URLs.
    """
    from src.utils.carousel_service import create_carousel

    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Can only edit slides of a pending post")

    result = await create_carousel(
        headline=body.headline,
        key_stats=body.key_stats,
        image_url=body.image_url,
        hook_stat_value=body.hook_stat_value,
        hook_stat_label=body.hook_stat_label,
        source_url=body.source_url,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=f"Re-render failed: {result.error}")

    render_data = {
        "headline": body.headline,
        "key_stats": body.key_stats,
        "hook_stat_value": body.hook_stat_value,
        "hook_stat_label": body.hook_stat_label,
        "source_url": body.source_url,
        "image_url": body.image_url,
    }
    await db.update_post_slides_and_render_data(post_id, result.export_urls, render_data)
    logger.info(f"Post {post_id} slides re-rendered ({result.slide_count} slides)")
    return JSONResponse({"slides": result.export_urls, "slide_count": result.slide_count})


@router.delete("/posts/{post_id}/slides/{slide_index}")
async def delete_slide(post_id: str, slide_index: int):
    """
    Remove a single slide by index from a post's slide list.
    Does not re-render — just removes the URL from the array.
    """
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Can only delete slides of a pending post")

    try:
        updated_slides = await db.delete_post_slide(post_id, slide_index)
    except IndexError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse({"slides": updated_slides})


@router.post("/posts/{post_id}/slides/reorder")
async def reorder_slides(post_id: str, body: ReorderSlidesRequest):
    """
    Reorder a post's slides by providing a permutation of current indices.
    e.g. {"order": [2, 0, 1, 3]} moves slide 2 to position 0.
    Does not re-render — just reorders the URL array.
    """
    post = await db.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("status") != "pending":
        raise HTTPException(status_code=409, detail="Can only reorder slides of a pending post")

    try:
        updated_slides = await db.reorder_post_slides(post_id, body.order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse({"slides": updated_slides})


# ---------------------------------------------------------------------------
# Background task — research → validate → pipeline → persist posts
# ---------------------------------------------------------------------------

async def _run_research_pipeline(job_id: str, topic: str) -> None:
    """
    Background task that runs the full v2 pipeline for a research job:
      1. ResearchOrchestrator  — fetch + synthesise stories
      2. ContentValidator      — relevance, freshness, dedup
      3. Per story (parallel): existing v1 pipeline (PostCreator → Caption → Analyzer)
      4. Persist each passing post to Firestore /posts collection
      5. Update job status throughout
    """
    try:
        # Step 1 — Research
        logger.info(f"[job {job_id}] Starting research for '{topic}'")
        try:
            stories = await _research_orchestrator.run(topic)
        except ResearchError as e:
            logger.error(f"[job {job_id}] Research failed: {e}")
            await db.update_job_status(job_id, "failed")
            return

        if not stories:
            logger.warning(f"[job {job_id}] No stories synthesised — marking failed")
            await db.update_job_status(job_id, "failed")
            return

        # Step 2 — Validate
        await db.update_job_status(job_id, "creating")
        validation_results = await _content_validator.run(topic, stories)
        passing_stories = [r.story for r in validation_results if r.passed]

        if not passing_stories:
            logger.warning(f"[job {job_id}] All stories failed validation — marking failed")
            await db.update_job_status(job_id, "failed")
            return

        logger.info(f"[job {job_id}] {len(passing_stories)} stories passed validation")

        # Step 3 — Run existing v1 pipeline per story in parallel
        await db.update_job_status(job_id, "analyzing")
        pipeline_results = await asyncio.gather(
            *[_pipeline._process_story(story) for story in passing_stories],
            return_exceptions=True,
        )

        # Step 4 — Persist passing posts to Firestore
        post_ids: list[str] = []
        for result in pipeline_results:
            if isinstance(result, Exception):
                logger.error(f"[job {job_id}] Pipeline exception: {result}")
                continue
            if not result.passed:
                logger.info(f"[job {job_id}] Story failed pipeline: {result.skip_reason}")
                continue

            slide_urls = result.carousel.export_urls if result.carousel else []
            caption_text = result.caption.full_text if result.caption else ""
            render_data = {
                "headline": result.story.headline,
                "key_stats": result.story.key_stats,
                "hook_stat_value": result.story.hook_stat_value,
                "hook_stat_label": result.story.hook_stat_label,
                "source_url": result.story.url,
                "image_url": result.carousel.image_url if result.carousel else None,
            }

            post_id = await db.create_post(
                story=result.story,
                slides=slide_urls,
                caption=caption_text,
                source="web_ui",
                render_data=render_data,
            )
            post_ids.append(post_id)

        # Step 5 — Mark job ready
        await db.update_job_status(job_id, "ready", story_ids=post_ids)
        logger.info(f"[job {job_id}] Complete — {len(post_ids)} posts ready for approval")

    except Exception as e:
        logger.error(f"[job {job_id}] Unexpected error: {e}", exc_info=True)
        await db.update_job_status(job_id, "failed")
