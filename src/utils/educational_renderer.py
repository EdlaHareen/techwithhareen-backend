"""
Educational Carousel Renderer — dedicated renderer for educational content.

Supports three formats:
  A — Mistakes → Right Way  (1 mistake/fix per slide, BOOKMARK THIS, SEND THIS TO SOMEONE)
  B — Core Concepts/Pillars (1 concept per slide, BOOKMARK THIS, SEND THIS TO SOMEONE)
  C — Cheat Sheet           (3 tips per slide, no bookmark, SAVE THIS CHEAT SHEET)

Legacy educational (carousel_format=None): step-by-step layout (WHAT YOU'LL LEARN).

This module contains only educational rendering logic — no news rendering code.
Shared slide functions are imported from carousel_renderer.
"""

import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from src.utils.carousel_renderer import (
    _slide_bookmark,
    _slide_cheat_batch,
    _slide_cheat_intro,
    _slide_content,
    _slide_cover,
    _slide_cta,
    _slide_cta_engage,
    _slide_cta_save,
    _slide_format_a_hook,
    _slide_hook_stat,
    _slide_learn_preview,
    _slide_listicle_item,
    _slide_mistake,
    _slide_pillar,
    _slide_read_more,
)
from src.utils.carousel_templates import DARK_TECH, TemplateConfig, get_template

logger = logging.getLogger(__name__)


def render_educational_carousel(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes] = None,
    hook_stat_value: str = "",
    hook_stat_label: str = "",
    output_dir: Optional[str] = None,
    source_url: str | None = None,
    carousel_format: Optional[str] = None,
    template_id: str = "dark_tech",
    tool_logos: Optional[dict[str, Optional[bytes]]] = None,
) -> list[str]:
    """
    Render an educational carousel and save PNGs to output_dir.

    Args:
        headline:         Hook headline for the cover slide.
        stats:            Content items — shape depends on carousel_format.
        image_bytes:      Optional cover image bytes.
        hook_stat_value:  Concept count for Format B Slide 2.
        hook_stat_label:  Label for Format B Slide 2.
        output_dir:       Directory to save PNGs. Defaults to /tmp.
        source_url:       Source URL — adds a "Read More" slide if present.
        carousel_format:  "A", "B", "C", or None (legacy step-by-step).
        template_id:      Visual theme — "dark_tech" or "clean_light".

    Returns:
        List of absolute file paths to the generated PNGs.
    """
    template = get_template(template_id)
    out = Path(output_dir or "/tmp")
    out.mkdir(parents=True, exist_ok=True)

    has_read_more = bool(source_url)
    slides: list[Image.Image] = []

    if carousel_format == "listicle":
        slides = _render_listicle(
            headline, stats, image_bytes,
            tool_logos or {},
            hook_stat_value, hook_stat_label,
            source_url, template,
        )

    elif carousel_format == "C":
        slides = _render_format_c(headline, stats, image_bytes, has_read_more, source_url, template)

    elif carousel_format == "A":
        slides = _render_format_a(headline, stats, image_bytes, has_read_more, source_url, template)

    elif carousel_format == "B":
        slides = _render_format_b(
            headline, stats, image_bytes,
            hook_stat_value, hook_stat_label,
            has_read_more, source_url, template,
        )

    else:
        slides = _render_legacy(headline, stats, image_bytes, has_read_more, source_url, template)

    paths: list[str] = []
    for i, slide in enumerate(slides, start=1):
        path = str(out / f"slide{i}.png")
        slide.save(path, "PNG", optimize=True)
        paths.append(path)

    logger.info(
        f"educational_renderer: {len(paths)} slides for '{headline[:50]}' "
        f"(format={carousel_format}, template={template_id})"
    )
    return paths


# ── Format A: Mistakes → Right Way ────────────────────────────────────────────

def _render_format_a(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes],
    has_read_more: bool,
    source_url: Optional[str],
    template: TemplateConfig = DARK_TECH,
) -> list[Image.Image]:
    has_bookmark = len(stats) >= 2
    bookmark_after = len(stats) // 2
    total = 2 + len(stats) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

    slides: list[Image.Image] = [
        _slide_cover(headline, image_bytes, total, template=template),
        _slide_format_a_hook(2, total, template=template),
    ]

    content_slides: list[Image.Image] = []
    bookmark_slide: Optional[Image.Image] = None
    slide_num = 3
    for i, stat in enumerate(stats):
        content_slides.append(_slide_mistake(stat, slide_num, total, template=template))
        slide_num += 1
        if has_bookmark and i == bookmark_after - 1:
            bookmark_slide = _slide_bookmark(slide_num, total, template=template)
            slide_num += 1

    for i, s in enumerate(content_slides):
        slides.append(s)
        if bookmark_slide is not None and i == bookmark_after - 1:
            slides.append(bookmark_slide)
            bookmark_slide = None

    if has_read_more:
        slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
    slides.append(_slide_cta(total, template=template))

    return slides


# ── Format B: Core Concepts / Pillars ─────────────────────────────────────────

def _render_format_b(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes],
    hook_stat_value: str,
    hook_stat_label: str,
    has_read_more: bool,
    source_url: Optional[str],
    template: TemplateConfig = DARK_TECH,
) -> list[Image.Image]:
    has_bookmark = len(stats) >= 2
    bookmark_after = len(stats) // 2
    total = 2 + len(stats) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

    slides: list[Image.Image] = [
        _slide_cover(headline, image_bytes, total, template=template),
        _slide_hook_stat(hook_stat_value, hook_stat_label, total, template=template),
    ]

    content_slides: list[Image.Image] = []
    bookmark_slide: Optional[Image.Image] = None
    slide_num = 3
    for i, stat in enumerate(stats):
        content_slides.append(_slide_pillar(stat, slide_num, total, template=template))
        slide_num += 1
        if has_bookmark and i == bookmark_after - 1:
            bookmark_slide = _slide_bookmark(slide_num, total, template=template)
            slide_num += 1

    for i, s in enumerate(content_slides):
        slides.append(s)
        if bookmark_slide is not None and i == bookmark_after - 1:
            slides.append(bookmark_slide)
            bookmark_slide = None

    if has_read_more:
        slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
    slides.append(_slide_cta(total, template=template))

    return slides


# ── Format C: Cheat Sheet ─────────────────────────────────────────────────────

def _render_format_c(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes],
    has_read_more: bool,
    source_url: Optional[str],
    template: TemplateConfig = DARK_TECH,
) -> list[Image.Image]:
    batches: list[list[str]] = [
        stats[i:i + 3] for i in range(0, max(len(stats), 1), 3)
        if stats[i:i + 3]
    ]
    total = 2 + len(batches) + (1 if has_read_more else 0) + 1

    slides: list[Image.Image] = [
        _slide_cover(headline, image_bytes, total, template=template),
        _slide_cheat_intro(2, total, template=template),
    ]
    slides.extend(
        _slide_cheat_batch(b, 3 + i, total, template=template) for i, b in enumerate(batches)
    )

    if has_read_more:
        slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
    slides.append(_slide_cta_save(total, template=template))

    return slides


# ── Legacy: step-by-step (WHAT YOU'LL LEARN) ──────────────────────────────────

def _render_legacy(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes],
    has_read_more: bool,
    source_url: Optional[str],
    template: TemplateConfig = DARK_TECH,
) -> list[Image.Image]:
    stat_chunks: list[list[str]] = []
    for i in range(0, max(len(stats), 1), 4):
        chunk = stats[i:i + 4]
        if chunk:
            stat_chunks.append(chunk)

    total = 2 + len(stat_chunks) + (1 if has_read_more else 0) + 1

    slides: list[Image.Image] = [
        _slide_cover(headline, image_bytes, total, template=template),
        _slide_learn_preview(stats, total, template=template),
    ]
    for j, chunk in enumerate(stat_chunks, start=1):
        slides.append(_slide_content(chunk, j + 1, total, template=template))

    if has_read_more:
        slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
    slides.append(_slide_cta(total, template=template))

    return slides


# ── Listicle: one tool/product per slide ──────────────────────────────────────

def _render_listicle(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes],
    tool_logos: dict[str, Optional[bytes]],
    hook_stat_value: str,
    hook_stat_label: str,
    source_url: Optional[str],
    template: TemplateConfig = DARK_TECH,
) -> list[Image.Image]:
    """Listicle: cover + 1-tool-per-slide + engagement CTA."""
    total = 1 + len(stats) + 1  # cover + N items + CTA (no bookmark for listicle)

    slides: list[Image.Image] = [
        _slide_cover(headline, image_bytes, total, template=template),
    ]

    for i, stat in enumerate(stats):
        tool_name = stat.split("\n")[0].strip() if "\n" in stat else stat.strip()
        logo = tool_logos.get(tool_name)
        slides.append(
            _slide_listicle_item(template, stat, i + 1, logo, i + 2, total)
        )

    # Engagement CTA — derive keyword from headline or use "LINK"
    keyword = hook_stat_label.split()[-1] if hook_stat_label else "LINK"
    slides.append(_slide_cta_engage(total, template=template, keyword=keyword))

    return slides
