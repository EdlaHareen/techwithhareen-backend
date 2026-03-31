"""
PDFGuideAgent — generates a branded educational PDF guide for a story topic.

Pipeline:
  1. LLM generates guide content (intro, steps, tips) + a short DM keyword.
  2. ReportLab renders the PDF into a BytesIO buffer (no temp file writes).
  3. PDF is uploaded to GCS at guides/{topic_slug}.pdf and a public URL is returned.

The dm_keyword returned in PDFGuideResult is used by the Caption Writer educational
voice mode to prompt followers to DM the keyword to receive the full guide.
"""

import asyncio
import io
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import anthropic
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from src.utils.story import Story

logger = logging.getLogger(__name__)

# ── UncoverAI brand colours — expressed as 0.0-1.0 for ReportLab ──────────────
_BG_R, _BG_G, _BG_B = 26 / 255, 26 / 255, 46 / 255      # #1A1A2E dark navy
_AC_R, _AC_G, _AC_B = 128 / 255, 117 / 255, 255 / 255    # #8075FF periwinkle
_WH_R, _WH_G, _WH_B = 1.0, 1.0, 1.0

# ── GCS config ─────────────────────────────────────────────────────────────────
GCS_BUCKET = "techwithhareen-carousel-assets"
GCS_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}"

# ── Font paths — same assets/fonts/ directory used by carousel_renderer.py ─────
_FONTS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "fonts"


def _register_fonts() -> None:
    """Register Anton and Inter TTF fonts with ReportLab. Falls back silently if files are missing."""
    for name, filename in [
        ("Anton", "Anton-Regular.ttf"),
        ("Inter", "Inter-Regular.ttf"),
        ("InterSB", "Inter-SemiBold.ttf"),
    ]:
        path = _FONTS_DIR / filename
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
            except Exception as exc:  # noqa: BLE001
                logger.warning("PDFGuideAgent: failed to register font %s: %s", name, exc)
        else:
            logger.warning("PDFGuideAgent: font not found at %s, ReportLab will use fallback", path)


_register_fonts()  # called at module load — must run before any Canvas() call


@dataclass
class PDFGuideResult:
    pdf_url: str       # public GCS https:// URL, e.g. https://storage.googleapis.com/…/guides/claude.pdf
    dm_keyword: str    # uppercase, max 8 chars, e.g. "CLAUDE"


class PDFGuideAgent:
    """
    Generates a branded educational PDF guide from a Story and uploads it to GCS.

    Usage::

        agent = PDFGuideAgent()
        result = await agent.run(story)
        # result.pdf_url  — GCS public URL
        # result.dm_keyword — e.g. "CLAUDE"
    """

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic()
        self._model = "claude-haiku-4-5-20251001"

    async def run(self, story: Story) -> PDFGuideResult:
        """
        Full pipeline: LLM content generation → PDF render → GCS upload.

        Args:
            story: Story object. story.topic (or story.headline) is used as the guide topic.

        Returns:
            PDFGuideResult with pdf_url and dm_keyword.
        """
        guide_data = await self._generate_guide_content(story)
        pdf_bytes = self._render_pdf(guide_data)
        topic_slug = _slugify(story.topic or story.headline)
        pdf_url = await asyncio.to_thread(
            self._upload_pdf_sync, pdf_bytes, f"guides/{topic_slug}.pdf"
        )
        return PDFGuideResult(pdf_url=pdf_url, dm_keyword=guide_data["dm_keyword"])

    # ── LLM content generation ──────────────────────────────────────────────────

    async def _generate_guide_content(self, story: Story) -> dict:
        """
        Single LLM call that returns a structured guide dict containing:
        - dm_keyword: str  (uppercase, max 8 chars)
        - intro: str       (2-3 sentence framing paragraph)
        - steps: list[{title: str, body: str}]
        - tips: list[str]  (2-3 quick-win tips)
        """
        topic = story.topic or story.headline
        steps_context = "\n".join(f"- {s}" for s in story.key_stats) if story.key_stats else "(no steps provided)"

        system_prompt = (
            "You write concise educational guides for the Instagram account @techwithhareen. "
            "You must return valid JSON only — no markdown fences, no extra text."
        )
        user_prompt = (
            f"Topic: {topic}\n\n"
            f"Lesson steps (one per key_stat):\n{steps_context}\n\n"
            "Return a JSON object with exactly these keys:\n"
            '  "dm_keyword": A single uppercase word, max 8 characters, used as the DM trigger keyword '
            "for this guide (e.g. CLAUDE, NOTION, CHATGPT, RUNWAY). Must be memorable and directly "
            "related to the tool or skill being taught.\n"
            '  "intro": A 2-3 sentence paragraph framing why this guide is valuable.\n'
            '  "steps": A list of objects, one per lesson step, each with:\n'
            '      "title": The step heading (e.g. "STEP 1: OPEN CLAUDE")\n'
            '      "body": 2-3 sentence expansion — what to actually do, not just what it means.\n'
            '  "tips": A list of 2-3 practical quick-win tips, each a single sentence.'
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()
        try:
            guide_data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"PDFGuideAgent: LLM returned invalid JSON: {exc}\nRaw: {raw[:200]}") from exc

        # Normalise dm_keyword — ensure uppercase and max 8 chars
        kw = str(guide_data.get("dm_keyword", "GUIDE")).upper()[:8]
        guide_data["dm_keyword"] = kw

        return guide_data

    # ── PDF render ──────────────────────────────────────────────────────────────

    def _render_pdf(self, guide_data: dict) -> bytes:
        """
        Render the guide as a PDF using ReportLab canvas into a BytesIO buffer.

        Page layout: A4 portrait (595 x 842 points).

        CRITICAL ordering: showPage() → save() → getvalue().
        Never call getvalue() before save() — buffer is empty before save() flushes.
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(595, 842))

        registered = pdfmetrics.getRegisteredFontNames()
        _has_anton = "Anton" in registered
        _has_inter = "Inter" in registered
        _has_inter_sb = "InterSB" in registered

        font_title = "Anton" if _has_anton else "Helvetica-Bold"
        font_body = "Inter" if _has_inter else "Helvetica"
        font_heading = "InterSB" if _has_inter_sb else "Helvetica-Bold"

        dm_keyword = guide_data.get("dm_keyword", "GUIDE")
        intro = guide_data.get("intro", "")
        steps = guide_data.get("steps", [])
        tips = guide_data.get("tips", [])

        # ── Page 1: Cover ──────────────────────────────────────────────────────
        self._fill_bg(c)

        # Brand name near top
        c.setFillColorRGB(_AC_R, _AC_G, _AC_B)
        c.setFont(font_body, 12)
        c.drawString(40, 802, "@techwithhareen")

        # Guide title
        c.setFillColorRGB(_WH_R, _WH_G, _WH_B)
        c.setFont(font_title, 38)
        title_lines = _wrap_text(f"YOUR {dm_keyword} GUIDE", max_width=515, font_name=font_title, font_size=38, canvas_obj=c)
        y = 720
        for line in title_lines:
            c.drawString(40, y, line)
            y -= 46

        # Intro paragraph
        c.setFont(font_body, 13)
        y -= 10
        for line in _wrap_text(intro, max_width=515, font_name=font_body, font_size=13, canvas_obj=c):
            if y < 80:
                break
            c.drawString(40, y, line)
            y -= 18

        # DM CTA at bottom
        c.setFillColorRGB(_AC_R, _AC_G, _AC_B)
        c.setFont(font_heading, 14)
        c.drawString(40, 50, f"DM {dm_keyword} for this guide")

        c.showPage()

        # ── Pages 2+: Steps ────────────────────────────────────────────────────
        self._fill_bg(c)
        y = 800

        for step in steps:
            title_text = step.get("title", "")
            body_text = step.get("body", "")

            # Step title
            c.setFillColorRGB(_WH_R, _WH_G, _WH_B)
            c.setFont(font_heading, 15)
            title_lines = _wrap_text(title_text, max_width=515, font_name=font_heading, font_size=15, canvas_obj=c)

            needed = len(title_lines) * 20 + 10
            body_lines = _wrap_text(body_text, max_width=515, font_name=font_body, font_size=12, canvas_obj=c)
            needed += len(body_lines) * 17 + 20

            if y - needed < 60:
                c.showPage()
                self._fill_bg(c)
                y = 800

            for line in title_lines:
                c.setFillColorRGB(_AC_R, _AC_G, _AC_B)
                c.setFont(font_heading, 15)
                c.drawString(40, y, line)
                y -= 20

            c.setFillColorRGB(_WH_R, _WH_G, _WH_B)
            c.setFont(font_body, 12)
            for line in body_lines:
                c.drawString(40, y, line)
                y -= 17

            y -= 20  # spacing between steps

        # ── Final page: Tips ───────────────────────────────────────────────────
        if tips:
            # Decide whether to add a new page or continue if space allows
            if y < 180:
                c.showPage()
                self._fill_bg(c)
                y = 800

            # "QUICK WINS" header
            c.setFillColorRGB(_AC_R, _AC_G, _AC_B)
            c.setFont(font_title, 22)
            c.drawString(40, y, "QUICK WINS")
            y -= 34

            c.setFillColorRGB(_WH_R, _WH_G, _WH_B)
            c.setFont(font_body, 12)
            for tip in tips:
                tip_lines = _wrap_text(f"• {tip}", max_width=515, font_name=font_body, font_size=12, canvas_obj=c)
                for line in tip_lines:
                    if y < 60:
                        c.showPage()
                        self._fill_bg(c)
                        y = 800
                    c.drawString(40, y, line)
                    y -= 17
                y -= 6

        # CRITICAL: showPage then save THEN getvalue
        c.showPage()
        c.save()
        return buffer.getvalue()

    @staticmethod
    def _fill_bg(c: canvas.Canvas) -> None:
        """Fill the current page with the dark navy background colour."""
        c.setFillColorRGB(_BG_R, _BG_G, _BG_B)
        c.rect(0, 0, 595, 842, fill=1, stroke=0)

    # ── GCS upload ─────────────────────────────────────────────────────────────

    @staticmethod
    def _upload_pdf_sync(pdf_bytes: bytes, object_name: str) -> str:
        """
        Synchronous GCS upload. Run via asyncio.to_thread to avoid blocking the event loop.

        Returns the public HTTPS URL of the uploaded PDF.
        """
        from google.cloud import storage  # noqa: PLC0415

        project_id = os.environ.get("GCP_PROJECT_ID")
        client = storage.Client(project=project_id)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(object_name)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")
        url = f"{GCS_BASE_URL}/{object_name}"
        logger.info("PDFGuideAgent: uploaded PDF to %s", url)
        return url


# ── Module-level helpers ────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert a topic string to a safe GCS object name component."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50]  # cap length for GCS key safety


def _wrap_text(
    text: str,
    max_width: float,
    font_name: str,
    font_size: float,
    canvas_obj: canvas.Canvas,
) -> list[str]:
    """
    Wrap a single text string to fit within max_width points.

    Uses ReportLab's stringWidth for accurate measurement.
    Returns a list of line strings.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: PLC0415

    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines or [""]
