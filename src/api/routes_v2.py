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
from src.agents.pdf_guide.agent import PDFGuideAgent
from src.agents.research_orchestrator.orchestrator import ResearchError, ResearchOrchestrator
from src.agents.topic_clarifier.agent import ClarifierQuestion, TopicClarifierAgent
from src.orchestrator.handler import InstaHandlerManager, StoryResult
from src.publishing.publisher import register_pending_post
from src.utils import firestore_client as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2")

_research_orchestrator = ResearchOrchestrator()
_content_validator = ContentValidator()
_pipeline = InstaHandlerManager()
_pdf_guide_agent = PDFGuideAgent()
_topic_clarifier = TopicClarifierAgent()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ClarifyRequest(BaseModel):
    topic: str


class ResearchRequest(BaseModel):
    topic: str
    content_type: Literal["news", "educational"] = "news"
    carousel_format: Optional[str] = None            # "A" | "B" | "C" — from clarifier answers
    clarifier_answers: Optional[dict[str, str]] = None  # {question_id: option_value}


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
# Clarifier helpers
# ---------------------------------------------------------------------------

def _default_clarifier_questions() -> list[dict]:
    """
    Hardcoded fallback returned when TopicClarifierAgent fails.
    Always returns just the format question with Format B as default.
    This ensures the pipeline can continue without blocking the user.
    """
    return [
        {
            "id": "format",
            "text": "Which format fits this topic?",
            "options": [
                {"value": "A", "label": "Mistakes → Right Way — what most people get wrong + the fix"},
                {"value": "B", "label": "Core Concepts / Pillars — 3–5 key ideas, each slide standalone"},
                {"value": "C", "label": "Cheat Sheet — dense tips, optimized for saves"},
            ],
            "default": "B",
        }
    ]


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@router.post("/clarify")
async def clarify_topic(body: ClarifyRequest):
    """
    Generate clarifying questions for an educational topic.
    Returns questions immediately (synchronous — no background task).
    On any failure, returns hardcoded Format B defaults — never 500s to the browser.
    """
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be empty")
    try:
        from dataclasses import asdict
        result = await _topic_clarifier.run(topic)
        questions = []
        for q in result.questions:
            questions.append({
                "id": q.id,
                "text": q.text,
                "options": [{"value": o.value, "label": o.label} for o in q.options],
                "default": q.default,
            })
        return {"questions": questions}
    except Exception as exc:
        logger.warning("TopicClarifierAgent failed for topic '%s': %s — returning defaults", topic, exc)
        return {"questions": _default_clarifier_questions()}


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
    asyncio.create_task(_run_research_pipeline(
        job_id, topic,
        content_type=body.content_type,
        carousel_format=body.carousel_format,
        clarifier_answers=body.clarifier_answers,
    ))

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

    # Recover carousel_format and content_type from existing render_data for re-render
    existing_render_data = post.get("render_data") or {}
    carousel_format = existing_render_data.get("carousel_format")
    content_type = post.get("content_type") or "news"

    result = await create_carousel(
        headline=body.headline,
        key_stats=body.key_stats,
        image_url=body.image_url,
        hook_stat_value=body.hook_stat_value,
        hook_stat_label=body.hook_stat_label,
        source_url=body.source_url,
        content_type=content_type,
        carousel_format=carousel_format,
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
        "carousel_format": carousel_format,  # preserve for future re-renders
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

async def _run_educational_pipeline(job_id: str, story) -> StoryResult:
    """
    Per-story pipeline for educational posts.
    Calls carousel, PDFGuide, CaptionWriter, and PostAnalyzer individually
    so dm_keyword can be threaded through to CaptionWriter.

    Cannot use _pipeline._process_story() because that calls CaptionWriter internally
    without dm_keyword support — it is v1 infrastructure and must not be modified.

    story.carousel_format is used by PostCreatorAgent and PostAnalyzerAgent.
    """
    import uuid
    story_id = str(uuid.uuid4())[:8]
    result = StoryResult(story_id=story_id, story=story)
    try:
        # 1. Run carousel — pass content_type='educational' and carousel_format
        carousel = await _pipeline._post_creator.run(story, content_type='educational')
        result.carousel = carousel

        # 2. Run PDFGuideAgent — produces pdf_url + dm_keyword
        pdf_url: Optional[str] = None
        dm_keyword: Optional[str] = None
        try:
            pdf_result = await _pdf_guide_agent.run(story)
            pdf_url = pdf_result.pdf_url
            dm_keyword = pdf_result.dm_keyword
        except Exception as e:
            logger.error(f"[job {job_id}] PDFGuideAgent failed: {e}")
            # Non-fatal: proceed without PDF

        # 3. CaptionWriter with dm_keyword injected
        caption = await _pipeline._caption_writer.run(story, carousel, dm_keyword=dm_keyword)
        result.caption = caption

        # 4. PostAnalyzer
        analysis = await _pipeline._post_analyzer.run(story, carousel, caption)
        result.analysis = analysis
        result.passed = analysis.passed
        if not analysis.passed:
            result.skip_reason = f"Failed analysis: {'; '.join(analysis.issues)}"

        # Attach pdf_url and dm_keyword to story for Firestore persistence
        story._edu_pdf_url = pdf_url
        story._edu_dm_keyword = dm_keyword

    except Exception as e:
        logger.error(f"[job {job_id}] Educational pipeline exception: {e}", exc_info=True)
        result.passed = False
        result.skip_reason = str(e)
    return result


async def _run_research_pipeline(
    job_id: str,
    topic: str,
    content_type: str = "news",
    carousel_format: Optional[str] = None,
    clarifier_answers: Optional[dict] = None,
) -> None:
    """
    Background task that runs the full v2 pipeline for a research job:
      1. ResearchOrchestrator  — fetch + synthesise stories
      2. ContentValidator      — relevance, freshness, dedup (news only; skipped for educational)
      3. Per story (parallel): existing v1 pipeline (PostCreator → Caption → Analyzer)
      4. Persist each passing post to Firestore /posts collection
      5. Update job status throughout

    content_type: "news" (default) | "educational"
      - "news": full pipeline including ContentValidator, 1–5 stories
      - "educational": ContentValidator skipped, hard-capped to 1 story, pdf_url/dm_keyword stubs
    carousel_format: "A" | "B" | "C" — set by TopicClarifierAgent; passed to run_educational()
    clarifier_answers: {question_id: option_value} — injected into synthesis prompt
    """
    try:
        # Step 1 — Research (always runs; educational path uses run_educational stub)
        logger.info(f"[job {job_id}] Starting research for '{topic}' (type={content_type}, format={carousel_format})")
        try:
            if content_type == "educational":
                stories = await _research_orchestrator.run_educational(
                    topic,
                    carousel_format=carousel_format,
                    clarifier_answers=clarifier_answers,
                )
            else:
                stories = await _research_orchestrator.run(topic)
        except ResearchError as e:
            logger.error(f"[job {job_id}] Research failed: {e}")
            await db.update_job_status(job_id, "failed")
            return

        if not stories:
            logger.warning(f"[job {job_id}] No stories synthesised — marking failed")
            await db.update_job_status(job_id, "failed")
            return

        # Step 2 — Validate (news only) or pass through (educational)
        await db.update_job_status(job_id, "creating")
        if content_type == "news":
            validation_results = await _content_validator.run(topic, stories)
            passing_stories = [r.story for r in validation_results if r.passed]

            if not passing_stories:
                logger.warning(f"[job {job_id}] All stories failed validation — marking failed")
                await db.update_job_status(job_id, "failed")
                return

            logger.info(f"[job {job_id}] {len(passing_stories)} stories passed validation")
        else:
            # Educational: skip ContentValidator entirely — 1 pre-authored topic story
            passing_stories = stories[:1]  # hard-cap: exactly 1 educational story
            logger.info(f"[job {job_id}] Educational path — ContentValidator skipped, {len(passing_stories)} story in pipeline")

        logger.info(f"[job {job_id}] {len(passing_stories)} stories in pipeline")

        # Step 3 — Run pipeline per story
        await db.update_job_status(job_id, "analyzing")

        if content_type == "educational":
            # Educational branch: call agents individually to allow dm_keyword injection.
            # _process_story() runs CaptionWriter internally without dm_keyword support,
            # so we cannot use it for educational posts.
            pipeline_results = []
            for story in passing_stories:
                edu_result = await _run_educational_pipeline(job_id, story)
                pipeline_results.append(edu_result)
        else:
            # News branch: unchanged — use existing _process_story via asyncio.gather
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
                "carousel_format": result.story.carousel_format,  # stored for re-render
            }

            # Educational-only fields — populated by _run_educational_story via story temp attrs
            pdf_url: Optional[str] = getattr(result.story, '_edu_pdf_url', None)
            dm_keyword: Optional[str] = getattr(result.story, '_edu_dm_keyword', None)

            post_id = await db.create_post(
                story=result.story,
                slides=slide_urls,
                caption=caption_text,
                source="web_ui",
                render_data=render_data,
                pdf_url=pdf_url,
                dm_keyword=dm_keyword,
                content_type=content_type if content_type == "educational" else None,
                carousel_format=result.story.carousel_format,
            )
            post_ids.append(post_id)

        # Step 5 — Mark job ready
        await db.update_job_status(job_id, "ready", story_ids=post_ids)
        logger.info(f"[job {job_id}] Complete — {len(post_ids)} posts ready for approval")

    except Exception as e:
        logger.error(f"[job {job_id}] Unexpected error: {e}", exc_info=True)
        await db.update_job_status(job_id, "failed")
