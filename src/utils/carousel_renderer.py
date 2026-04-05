"""
Carousel Renderer — Pillow-based PNG generator for @techwithhareen Instagram carousels.

Design language: "UncoverAI" style
  - Dark navy background (#1A1A2E)
  - Accent: neon periwinkle #8075FF
  - Font: Anton (heavy condensed) for headlines, Inter for body
  - Layout: top 50% = story image (with vignette), bottom 50% = massive ALL CAPS text
  - Word-level color alternation: key words in accent, rest in white

Produces 6–10+ slides at 1080×1350 (portrait 4:5):
  Slide 1 — Cover:     Story image top + "DO YOU KNOW" label + bold headline bottom
  Slide 2 — Hook Stat: Large accent number + white context label (standalone, no swipe prompt)
  Slide 3+ — Content:  Stat bullets (accent numbers, white text), max 4 per slide
  Mid-carousel — Bookmark: "BOOKMARK THIS" on accent bg (injected when total >= 8 slides)
  Second-to-last — Read More: "LINK IN DESCRIPTION" — no URL on slide
  Last — CTA: "SEND THIS TO SOMEONE" + "@TECHWITHHAREEN"
"""

import io
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.utils.carousel_templates import DARK_TECH, TemplateConfig, get_template

logger = logging.getLogger(__name__)

# ── Canvas ─────────────────────────────────────────────────────────────────────
W, H = 1080, 1350

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = (26, 26, 46)      # #1A1A2E — dark navy (not pure black — avoids halation)
WHITE   = (255, 255, 255)
ACCENT  = (128, 117, 255)   # #8075FF — neon periwinkle
GRAY    = (160, 160, 160)

# ── Asset paths ────────────────────────────────────────────────────────────────
FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

_ANTON   = FONTS_DIR / "Anton-Regular.ttf"
_INTER   = FONTS_DIR / "Inter-Regular.ttf"
_INTER_SB = FONTS_DIR / "Inter-SemiBold.ttf"
_SPACE_GROTESK_BOLD = FONTS_DIR / "SpaceGrotesk-Bold.ttf"
_SPACE_GROTESK_MED  = FONTS_DIR / "SpaceGrotesk-Medium.ttf"

_SYSTEM_BOLD = [
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


@lru_cache(maxsize=64)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    paths = {
        "anton":                [_ANTON] + _SYSTEM_BOLD,
        "inter":                [_INTER],
        "inter_sb":             [_INTER_SB, _INTER],
        "space_grotesk_bold":   [_SPACE_GROTESK_BOLD] + _SYSTEM_BOLD,
        "space_grotesk_medium": [_SPACE_GROTESK_MED, _INTER],
    }
    for p in paths.get(name, [_ANTON]):
        if Path(p).exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if dummy.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    bb = font.getbbox("Ag")
    return bb[3] - bb[1]


def _text_block_height(text: str, font: ImageFont.FreeTypeFont, max_w: int, spacing: int = 8) -> int:
    lines = _wrap(text.upper(), font, max_w)
    lh = _line_height(font)
    return len(lines) * lh + max(0, len(lines) - 1) * spacing


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int, y: int,
    font: ImageFont.FreeTypeFont,
    color,
    max_w: int,
    spacing: int = 8,
    align: str = "left",
) -> int:
    """Draw wrapped text. Returns y after last line."""
    lines = _wrap(text.upper(), font, max_w)
    lh = _line_height(font)
    for line in lines:
        lw = draw.textlength(line, font=font)
        if align == "center":
            dx = x + (max_w - lw) // 2
        elif align == "right":
            dx = x + max_w - lw
        else:
            dx = x
        draw.text((dx, y), line, font=font, fill=color)
        y += lh + spacing
    return y


def _draw_alternating(
    draw: ImageDraw.ImageDraw,
    words: list[str],
    accent_indices: set[int],
    x: int, y: int,
    font: ImageFont.FreeTypeFont,
    max_w: int,
    spacing: int = 10,
    align: str = "center",
    color_accent: tuple = ACCENT,
    color_default: tuple = WHITE,
) -> int:
    """
    Draw a list of words with alternating colors (white vs accent).
    accent_indices: set of word positions that should be ACCENT colored.
    Words are wrapped to fit max_w. Returns y after last line.
    """
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lh = _line_height(font)
    sp = int(dummy.textlength(" ", font=font))

    # Build lines with word-index tracking
    lines: list[list[tuple[str, int]]] = []  # [(word, original_index), ...]
    cur_line: list[tuple[str, int]] = []
    cur_w = 0

    for i, word in enumerate(words):
        ww = int(dummy.textlength(word.upper(), font=font))
        needed = ww if not cur_line else ww + sp
        if cur_w + needed <= max_w or not cur_line:
            cur_line.append((word, i))
            cur_w += needed
        else:
            lines.append(cur_line)
            cur_line = [(word, i)]
            cur_w = ww

    if cur_line:
        lines.append(cur_line)

    for line in lines:
        line_w = sum(int(dummy.textlength(w.upper(), font=font)) for w, _ in line) + sp * (len(line) - 1)
        if align == "center":
            dx = x + (max_w - line_w) // 2
        else:
            dx = x

        for w, idx in line:
            color = color_accent if idx in accent_indices else color_default
            ww = int(dummy.textlength(w.upper(), font=font))
            draw.text((dx, y), w.upper(), font=font, fill=color)
            dx += ww + sp

        y += lh + spacing

    return y


# ── Background & image helpers ─────────────────────────────────────────────────

def _bg_canvas(template: TemplateConfig = DARK_TECH) -> Image.Image:
    return Image.new("RGB", (W, H), template.bg_color)


def _place_image_top(base: Image.Image, image_bytes: bytes, frac: float = 0.52, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Place a story image in the top `frac` of the canvas with a bottom vignette
    so it blends into the black bottom section.
    """
    img_h = int(H * frac)
    try:
        story = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # Crop to fill the top band (center crop)
        sw, sh = story.size
        target_ratio = W / img_h
        src_ratio = sw / sh
        if src_ratio > target_ratio:
            new_w = int(sh * target_ratio)
            left = (sw - new_w) // 2
            story = story.crop((left, 0, left + new_w, sh))
        else:
            new_h = int(sw / target_ratio)
            top = (sh - new_h) // 2
            story = story.crop((0, top, sw, top + new_h))
        story = story.resize((W, img_h), Image.LANCZOS)

        # Bottom vignette — gradient from transparent to bg color
        bg = template.bg_color
        vignette = Image.new("RGBA", (W, img_h), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        vig_start = int(img_h * 0.45)
        for row in range(vig_start, img_h):
            alpha = int(255 * (row - vig_start) / (img_h - vig_start))
            vd.line([(0, row), (W, row)], fill=(bg[0], bg[1], bg[2], alpha))

        story_rgba = story.convert("RGBA")
        story_rgba = Image.alpha_composite(story_rgba, vignette)

        base.paste(story_rgba.convert("RGB"), (0, 0))
    except Exception as e:
        logger.warning(f"Could not place image: {e}")

    return base


def _vignette_edges(img: Image.Image, strength: int = 140, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """Subtle edge vignette on a canvas slide.  Skipped for light templates."""
    if not template.use_vignette:
        return img
    bg = template.bg_color
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(vig)
    steps = 80
    for i in range(steps):
        alpha = int(strength * (i / steps) ** 2)
        margin = i * 6
        d.rectangle(
            [margin, margin, W - margin, H - margin],
            outline=(bg[0], bg[1], bg[2], strength - alpha),
            width=6,
        )
    return Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")


# ── Brand label ────────────────────────────────────────────────────────────────

def _draw_brand(draw: ImageDraw.ImageDraw, template: TemplateConfig = DARK_TECH, y_top: int = 36) -> None:
    """Top-left: small brand handle in accent color."""
    f = _font(template.body_font_semibold, 26)
    draw.text((44, y_top), template.brand_handle, font=f, fill=template.accent_color)


def _draw_slide_counter(draw: ImageDraw.ImageDraw, current: int, total: int, template: TemplateConfig = DARK_TECH) -> None:
    """Top-right: '1 / 4' in gray."""
    f = _font(template.body_font, 24)
    label = f"{current} / {total}"
    lw = draw.textlength(label, font=f)
    draw.text((W - 44 - lw, 36), label, font=f, fill=template.gray_color)


# ── Slide builders ─────────────────────────────────────────────────────────────

def _slide_cover(headline: str, image_bytes: Optional[bytes], total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Slide 1 — Cover.
    Top 52%: story image with bottom vignette.
    Bottom 48%: pill label + massive headline, word-level accent highlights.
    """
    img = _bg_canvas(template)

    if image_bytes:
        img = _place_image_top(img, image_bytes, frac=0.52, template=template)

    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, 1, total, template)

    pad = 44
    text_zone_top = int(H * 0.50)
    max_w = W - 2 * pad

    # Pill label
    label_f = _font(template.body_font_semibold, 28)
    label = template.pill_label
    lw = int(draw.textlength(label, font=label_f))
    lh = _line_height(label_f)
    pill_pad_x, pill_pad_y = 18, 10
    pill_x = (W - lw - 2 * pill_pad_x) // 2
    pill_y = text_zone_top + 10
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + lw + 2 * pill_pad_x, pill_y + lh + 2 * pill_pad_y],
        radius=20, fill=template.pill_bg_color,
    )
    draw.text((pill_x + pill_pad_x, pill_y + pill_pad_y), label, font=label_f, fill=template.pill_text_color)

    # Headline — large, word-level accent on first 2 key words
    headline_f = _font(template.headline_font, 108)
    words = headline.split()
    accent_idx = {0}
    for i, w in enumerate(words[:len(words) // 2 + 1]):
        if len(w) > 5:
            accent_idx.add(i)
            break

    y = pill_y + lh + 2 * pill_pad_y + 24
    _draw_alternating(
        draw, words, accent_idx, pad, y, headline_f, max_w,
        spacing=6, align="center",
        color_accent=template.accent_color, color_default=template.text_color,
    )

    return img


def _slide_hook_stat(hook_stat_value: str, hook_stat_label: str, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Slide 2 — Hook Stat.
    Black bg. The single most shocking number blown up in accent color.
    Short context label in white underneath.

    Falls back to a generic teaser if no hook stat is available.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=60, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, 2, total, template)

    pad = 44
    max_w = W - 2 * pad

    if hook_stat_value:
        # Big number — as large as it can go (auto-size to fit)
        for size in range(320, 80, -10):
            f_num = _font(template.headline_font, size)
            if draw.textlength(hook_stat_value.upper(), font=f_num) <= max_w:
                break

        f_label = _font(template.headline_font, 72)

        num_h = _line_height(f_num) + 20   # extra breathing room below number
        label_h = _text_block_height(hook_stat_label, f_label, max_w, spacing=4) if hook_stat_label else 0
        gap = 28
        block_h = num_h + (gap + label_h if hook_stat_label else 0)
        y = (H - block_h) // 2

        # Big accent number
        nw = int(draw.textlength(hook_stat_value.upper(), font=f_num))
        draw.text(((W - nw) // 2, y), hook_stat_value.upper(), font=f_num, fill=template.accent_color)
        y += num_h

        # Context label in white
        if hook_stat_label:
            y += gap
            _draw_text_block(draw, hook_stat_label, pad, y, f_label, template.text_color, max_w, spacing=4, align="center")
            y += label_h

    else:
        # Fallback: accent bg with generic teaser
        img = Image.new("RGB", (W, H), template.accent_bg_color)
        draw = ImageDraw.Draw(img)
        _draw_brand(draw, template)
        _draw_slide_counter(draw, 2, total, template)

        f = _font(template.headline_font, 120)
        h1 = _text_block_height("THIS IS", f, max_w, spacing=0)
        h2 = _text_block_height("INSANE.", f, max_w, spacing=0)
        gap = 30
        y = (H - h1 - gap - h2) // 2
        _draw_text_block(draw, "THIS IS", pad, y, f, template.accent_bg_text_color, max_w, spacing=0, align="center")
        y += h1 + gap
        _draw_text_block(draw, "INSANE.", pad, y, f, template.text_color, max_w, spacing=0, align="center")

    return img


def _slide_content(stats: list[str], slide_num: int, total: int, start_num: int = 0, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Slide 3+ — Content bullets.
    Each stat is formatted as "HEADLINE\nExplanation sentence".
    Black bg, accent number, white headline, gray explanation.
    Items are distributed evenly to fill the full slide height.
    Numbering is continuous across content slides via start_num.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=80, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    num_f = _font(template.headline_font, 68)
    headline_f = _font(template.body_font_semibold, 38)
    body_f = _font(template.body_font, 30)
    max_w = W - 2 * pad

    n = min(len(stats), 4)
    top = 130
    bottom = H - 60
    slot_h = (bottom - top) // n

    for i, stat in enumerate(stats[:4]):
        # Parse headline and explanation
        parts = stat.split("\n", 1)
        headline = parts[0].strip()
        explanation = parts[1].strip() if len(parts) > 1 else ""

        num_str = f"{start_num + i + 1:02d}"
        num_w = int(draw.textlength(num_str, font=num_f)) + 20
        num_h = _line_height(num_f)
        text_x = pad + num_w

        # Measure content block height
        headline_lines = _wrap(headline, headline_f, max_w - num_w)
        headline_h = len(headline_lines) * (_line_height(headline_f) + 4)
        body_lines = _wrap(explanation, body_f, max_w - num_w) if explanation else []
        body_h = len(body_lines) * (_line_height(body_f) + 3) if body_lines else 0
        gap = 10
        text_block_h = headline_h + (gap + body_h if body_h else 0)
        content_h = max(num_h, text_block_h)

        # Center content block within its slot
        slot_top = top + i * slot_h
        y = slot_top + (slot_h - content_h) // 2

        # Draw accent number
        draw.text((pad, y), num_str, font=num_f, fill=template.accent_color)

        # Draw headline — vertically aligned to number top
        hy = y + max(0, (num_h - text_block_h) // 2)
        for line in headline_lines:
            draw.text((text_x, hy), line.upper(), font=headline_f, fill=template.text_color)
            hy += _line_height(headline_f) + 4

        # Draw explanation below headline
        if body_lines:
            by = y + max(0, (num_h - text_block_h) // 2) + headline_h + gap
            for line in body_lines:
                draw.text((text_x, by), line, font=body_f, fill=template.gray_color)
                by += _line_height(body_f) + 3

        # Divider between items
        if i < n - 1:
            div_y = slot_top + slot_h - 1
            draw.line([(pad, div_y), (W - pad, div_y)], fill=template.divider_color, width=1)

    return img


def _slide_read_more(url: str, slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Read More slide — second-to-last.
    Black bg, accent 'LINK IN' + white 'DESCRIPTION' — no URL on slide.
    The actual URL lives in the caption only.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=100, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad

    f_big = _font(template.headline_font, 118)

    h1 = _text_block_height("LINK IN", f_big, max_w, 0)
    h2 = _text_block_height("DESCRIPTION", f_big, max_w, 0)
    gap = 16
    block_h = h1 + gap + h2
    y = (H - block_h) // 2

    _draw_text_block(draw, "LINK IN", pad, y, f_big, template.accent_color, max_w, spacing=0, align="center")
    y += h1 + gap
    _draw_text_block(draw, "DESCRIPTION", pad, y, f_big, template.text_color, max_w, spacing=0, align="center")

    return img


def _slide_bookmark(slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Mid-carousel bookmark slide — inserted when total slides >= 8.
    Accent bg with 'BOOKMARK THIS' in large white Anton type.
    Reinforces save behaviour mid-scroll.
    """
    img = Image.new("RGB", (W, H), template.accent_bg_color)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad
    f = _font(template.headline_font, 118)
    f_sub = _font(template.body_font_semibold, 40)

    h1 = _text_block_height("BOOKMARK", f, max_w, 0)
    h2 = _text_block_height("THIS", f, max_w, 0)
    h3 = _line_height(f_sub)
    gap = 20
    total_h = h1 + gap + h2 + gap + h3
    y = (H - total_h) // 2

    _draw_text_block(draw, "BOOKMARK", pad, y, f, template.text_color, max_w, spacing=0, align="center")
    y += h1 + gap
    _draw_text_block(draw, "THIS", pad, y, f, template.accent_bg_text_color, max_w, spacing=0, align="center")
    y += h2 + gap
    sub = "SAVE THIS FOR LATER"
    sw = int(draw.textlength(sub, font=f_sub))
    draw.text(((W - sw) // 2, y), sub, font=f_sub, fill=template.text_color)

    return img


def _slide_learn_preview(steps_preview: list[str], total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Slide 2 — What You'll Learn (educational carousels only).
    Accent bg, "WHAT YOU'LL LEARN" header, 3-4 step bullet lines in white.
    Replaces the hook stat slide when content_type='educational'.
    """
    img = Image.new("RGB", (W, H), template.accent_bg_color)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, 2, total, template)

    pad = 44
    max_w = W - 2 * pad

    # Title: "WHAT YOU'LL LEARN"
    title_f = _font(template.headline_font, 88)
    title_h = _text_block_height("WHAT YOU'LL LEARN", title_f, max_w, spacing=0)

    # Divider
    divider_h = 4
    divider_margin_top = 24
    divider_margin_bottom = 40

    # Measure bullets (first line of each step only)
    bullet_f = _font(template.body_font_semibold, 36)
    bullet_lh = _line_height(bullet_f)
    bullet_spacing = 54
    items = steps_preview[:4] if steps_preview else []
    bullet_labels = []
    for step in items:
        first_line = step.split("\n")[0].strip()
        bullet_labels.append(f"• {first_line}")

    bullets_total_h = len(bullet_labels) * bullet_lh + max(0, len(bullet_labels) - 1) * (bullet_spacing - bullet_lh)

    # Center the whole block vertically
    block_h = title_h + divider_margin_top + divider_h + divider_margin_bottom + bullets_total_h
    y = (H - block_h) // 2

    # Draw title
    _draw_text_block(draw, "WHAT YOU'LL LEARN", pad, y, title_f, template.text_color, max_w, spacing=0, align="center")
    y += title_h + divider_margin_top

    # Draw divider
    divider_alpha_color = (255, 255, 255, 100)  # white at ~40% opacity
    divider_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    div_draw = ImageDraw.Draw(divider_img)
    div_draw.line([(pad, y), (W - pad, y)], fill=divider_alpha_color, width=divider_h)
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, divider_img)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)
    y += divider_h + divider_margin_bottom

    # Draw bullet lines
    for label in bullet_labels:
        draw.text((pad, y), label, font=bullet_f, fill=template.text_color)
        y += bullet_spacing

    return img


def _slide_cta(total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Slide 4 — CTA (evergreen).
    Black bg, massive white text, accent handle.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=100, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, total, total, template)

    f_big = _font(template.headline_font, 118)
    f_handle = _font(template.headline_font, 72)
    pad = 44
    max_w = W - 2 * pad

    lines_big = ["SEND THIS TO", "SOMEONE"]
    h_big = sum(_text_block_height(l, f_big, max_w, 0) for l in lines_big) + 10
    h_handle = _text_block_height("@TECHWITHHAREEN", f_handle, max_w, 0)
    gap = 32
    total_h = h_big + gap + h_handle
    y = (H - total_h) // 2

    for line in lines_big:
        lh = _text_block_height(line, f_big, max_w, 0)
        _draw_text_block(draw, line, pad, y, f_big, template.text_color, max_w, spacing=0, align="center")
        y += lh + 10

    y += gap
    _draw_text_block(draw, template.brand_handle, pad, y, f_handle, template.accent_color, max_w, spacing=0, align="center")

    return img


# ── Format A: Mistakes → Right Way slides ─────────────────────────────────────

def _slide_format_a_hook(slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Format A Slide 2 — accent bg with bold hook claim.
    Sets up the mistake series: "MOST PEOPLE DO IT WRONG."
    """
    img = Image.new("RGB", (W, H), template.accent_bg_color)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad
    f_big = _font(template.headline_font, 140)
    f_sub = _font(template.body_font_semibold, 40)

    lines = ["MOST PEOPLE", "DO IT", "WRONG."]
    heights = [_text_block_height(l, f_big, max_w, 0) for l in lines]
    sub_h = _line_height(f_sub)
    gap = 20
    block_h = sum(heights) + (len(heights) - 1) * gap + 48 + sub_h
    y = (H - block_h) // 2

    for i, line in enumerate(lines):
        color = template.accent_bg_text_color if i < 2 else template.text_color
        _draw_text_block(draw, line, pad, y, f_big, color, max_w, spacing=0, align="center")
        y += heights[i] + gap

    y += 28
    sub = "HERE'S WHAT ACTUALLY WORKS."
    sw = int(draw.textlength(sub, font=f_sub))
    draw.text(((W - sw) // 2, y), sub, font=f_sub, fill=template.text_color)

    return img


def _slide_mistake(stat: str, slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Format A content slide — one mistake + fix per slide.
    Parses stat as "MISTAKE: [text]\\nFIX: [text]".
    Falls back to plain 2-line split if prefix not found.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=80, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad

    # Parse mistake / fix lines
    parts = stat.split("\n", 1)
    mistake_line = parts[0].strip()
    fix_line = parts[1].strip() if len(parts) > 1 else ""

    # Strip "MISTAKE: " and "FIX: " prefixes if present
    if mistake_line.upper().startswith("MISTAKE:"):
        mistake_line = mistake_line[len("MISTAKE:"):].strip()
    if fix_line.upper().startswith("FIX:"):
        fix_line = fix_line[len("FIX:"):].strip()

    # Derive mistake number from slide position (slide 3 = mistake 1, etc.)
    # We display the number from the slide counter context — use a pill label instead
    # Extract the content slide index from slide_num: slide 3 = #1 for Format A
    # For simplicity, we don't track index here — caller (render_carousel) numbers it.
    # We display "MISTAKE #N" using a pill at the top.

    f_pill = _font(template.body_font_semibold, 28)
    f_mistake = _font(template.headline_font, 68)
    f_fix_label = _font(template.body_font_semibold, 32)
    f_fix = _font(template.body_font, 34)

    # Pill: "MISTAKE #N" — we need the content index. Use slide_num - 2 as proxy.
    mistake_num = max(1, slide_num - 2)
    pill_text = f"MISTAKE #{mistake_num}"
    pill_lw = int(draw.textlength(pill_text, font=f_pill))
    pill_lh = _line_height(f_pill)
    pill_pad_x, pill_pad_y = 20, 10
    pill_x = pad
    pill_y = 100

    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_lw + 2 * pill_pad_x, pill_y + pill_lh + 2 * pill_pad_y],
        radius=20, fill=template.accent_color,
    )
    draw.text((pill_x + pill_pad_x, pill_y + pill_pad_y), pill_text, font=f_pill, fill=template.text_color)

    # Mistake text — large Anton white
    mistake_h = _text_block_height(mistake_line, f_mistake, max_w, spacing=4)
    mistake_y = pill_y + pill_lh + 2 * pill_pad_y + 50

    _draw_text_block(draw, mistake_line, pad, mistake_y, f_mistake, template.text_color, max_w, spacing=4, align="left")

    # Divider line
    divider_y = mistake_y + mistake_h + 50
    draw.line([(pad, divider_y), (W - pad, divider_y)], fill=template.accent_color, width=2)

    # Fix section
    fix_label_y = divider_y + 30
    check_str = "✓ FIX:"
    draw.text((pad, fix_label_y), check_str, font=f_fix_label, fill=template.accent_color)
    check_w = int(draw.textlength(check_str, font=f_fix_label))

    fix_x = pad + check_w + 12
    fix_w = max_w - check_w - 12
    fix_lines = _wrap(fix_line, f_fix, fix_w)
    fix_lh = _line_height(f_fix)
    fy = fix_label_y
    for line in fix_lines:
        draw.text((fix_x, fy), line, font=f_fix, fill=template.text_color)
        fy += fix_lh + 4

    return img


# ── Format B: Core Concepts / Pillars slides ───────────────────────────────────

def _slide_pillar(stat: str, slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Format B content slide — one concept/pillar per slide.
    Parses stat as "[Concept Name]\\n[2-sentence explanation]".
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=80, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad

    parts = stat.split("\n", 1)
    concept_name = parts[0].strip()
    explanation = parts[1].strip() if len(parts) > 1 else ""

    f_pill = _font(template.body_font_semibold, 28)
    f_concept = _font(template.headline_font, 88)
    f_explain = _font(template.body_font, 34)

    # Pill: "PRINCIPLE #N"
    principle_num = max(1, slide_num - 2)
    pill_text = f"PRINCIPLE #{principle_num}"
    pill_lw = int(draw.textlength(pill_text, font=f_pill))
    pill_lh = _line_height(f_pill)
    pill_pad_x, pill_pad_y = 20, 10
    pill_y = 100

    draw.rounded_rectangle(
        [pad, pill_y, pad + pill_lw + 2 * pill_pad_x, pill_y + pill_lh + 2 * pill_pad_y],
        radius=20, fill=template.accent_color,
    )
    draw.text((pad + pill_pad_x, pill_y + pill_pad_y), pill_text, font=f_pill, fill=template.text_color)

    # Concept name — large Anton white
    concept_y = pill_y + pill_lh + 2 * pill_pad_y + 60
    concept_h = _text_block_height(concept_name, f_concept, max_w, spacing=4)
    _draw_text_block(draw, concept_name, pad, concept_y, f_concept, template.text_color, max_w, spacing=4, align="left")

    # Explanation — Inter gray
    if explanation:
        explain_y = concept_y + concept_h + 36
        explain_lines = _wrap(explanation, f_explain, max_w)
        explain_lh = _line_height(f_explain)
        for line in explain_lines:
            if explain_y + explain_lh > H - 80:
                break
            draw.text((pad, explain_y), line, font=f_explain, fill=template.gray_color)
            explain_y += explain_lh + 6

    return img


# ── Format C: Cheat Sheet slides ───────────────────────────────────────────────

def _slide_cheat_intro(slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Format C Slide 2 — accent bg with "CHEAT SHEET" + save prompt.
    """
    img = Image.new("RGB", (W, H), template.accent_bg_color)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad
    f_big = _font(template.headline_font, 160)
    f_sub = _font(template.body_font_semibold, 42)

    h1 = _text_block_height("CHEAT", f_big, max_w, 0)
    h2 = _text_block_height("SHEET", f_big, max_w, 0)
    h_sub = _line_height(f_sub)
    gap = 12
    block_h = h1 + gap + h2 + 40 + h_sub
    y = (H - block_h) // 2

    _draw_text_block(draw, "CHEAT", pad, y, f_big, template.text_color, max_w, spacing=0, align="center")
    y += h1 + gap
    _draw_text_block(draw, "SHEET", pad, y, f_big, template.accent_bg_text_color, max_w, spacing=0, align="center")
    y += h2 + 40

    sub = "SAVE THIS — YOU'LL USE IT"
    sw = int(draw.textlength(sub, font=f_sub))
    draw.text(((W - sw) // 2, y), sub, font=f_sub, fill=template.text_color)

    return img


def _slide_cheat_batch(stats_batch: list[str], slide_num: int, total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Format C content slide — up to 3 tips stacked vertically.
    Each tip is a single line (no \\n parsing needed).
    Dense cheat-sheet layout with accent numbers + white tip text.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=80, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad

    f_num = _font(template.headline_font, 72)
    f_tip = _font(template.body_font_semibold, 36)

    tips = stats_batch[:3]
    n = len(tips)

    top = 130
    bottom = H - 80
    available_h = bottom - top
    slot_h = available_h // max(n, 1)

    for i, tip in enumerate(tips):
        num_str = f"{i + 1:02d}"
        num_w = int(draw.textlength(num_str, font=f_num)) + 16
        num_h = _line_height(f_num)
        tip_x = pad + num_w
        tip_w = max_w - num_w

        tip_lines = _wrap(tip, f_tip, tip_w)
        tip_lh = _line_height(f_tip)
        tip_block_h = len(tip_lines) * (tip_lh + 4)
        content_h = max(num_h, tip_block_h)

        slot_top = top + i * slot_h
        y = slot_top + (slot_h - content_h) // 2

        # Accent number
        draw.text((pad, y), num_str, font=f_num, fill=template.accent_color)

        # Tip text aligned with number top
        ty = y + max(0, (num_h - tip_block_h) // 2)
        for line in tip_lines:
            draw.text((tip_x, ty), line, font=f_tip, fill=template.text_color)
            ty += tip_lh + 4

        # Subtle divider between tips
        if i < n - 1:
            div_y = slot_top + slot_h - 1
            draw.line([(pad, div_y), (W - pad, div_y)], fill=template.divider_color, width=1)

    return img


def _slide_cta_save(total: int, template: TemplateConfig = DARK_TECH) -> Image.Image:
    """
    Format C last slide — "SAVE THIS CHEAT SHEET" + "@TECHWITHHAREEN".
    Replaces the standard "SEND THIS TO SOMEONE" CTA for cheat sheet format.
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=100, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, total, total, template)

    f_big = _font(template.headline_font, 104)
    f_handle = _font(template.headline_font, 64)
    pad = 44
    max_w = W - 2 * pad

    lines_big = ["SAVE THIS", "CHEAT SHEET"]
    h_big = sum(_text_block_height(l, f_big, max_w, 0) for l in lines_big) + 10
    h_handle = _text_block_height("@TECHWITHHAREEN", f_handle, max_w, 0)
    gap = 32
    total_h = h_big + gap + h_handle
    y = (H - total_h) // 2

    for line in lines_big:
        _draw_text_block(draw, line, pad, y, f_big, template.text_color, max_w, spacing=0, align="center")
        y += _text_block_height(line, f_big, max_w, 0) + 10

    y += gap - 10
    _draw_text_block(draw, template.brand_handle, pad, y, f_handle, template.accent_color, max_w, spacing=0, align="center")

    return img


# ── Format: Listicle slides ───────────────────────────────────────────────────

def _logo_fallback(template: TemplateConfig, letter: str, size: int = 120) -> Image.Image:
    """Render a coloured circle with the tool's initial as logo fallback."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size - 1, size - 1], fill=template.accent_color)
    f = _font(template.headline_font, size // 2)
    lw = draw.textlength(letter.upper(), font=f)
    lh = _line_height(f)
    draw.text(
        ((size - lw) // 2, (size - lh) // 2),
        letter.upper(), font=f, fill=(255, 255, 255),
    )
    return img


def _slide_listicle_item(
    template: TemplateConfig,
    stat: str,
    item_num: int,
    logo_bytes: Optional[bytes],
    slide_num: int,
    total: int,
) -> Image.Image:
    """
    Listicle content slide — one tool/product per slide.
    Parses stat as "[Name]\\n[Category]\\n[Value prop]\\n[Bullet1]|||[Bullet2]|||[Bullet3]".
    """
    img = _bg_canvas(template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, slide_num, total, template)

    pad = 44
    max_w = W - 2 * pad

    # Parse stat lines
    parts = stat.split("\n")
    tool_name = parts[0].strip() if len(parts) > 0 else "Tool"
    category = parts[1].strip() if len(parts) > 1 else ""
    value_prop = parts[2].strip() if len(parts) > 2 else ""
    bullets_raw = parts[3].strip() if len(parts) > 3 else ""
    bullets = [b.strip() for b in bullets_raw.split("|||")] if bullets_raw else []

    y = 90

    # ── Item number: "#N" ──
    f_num = _font(template.headline_font, 64)
    num_str = f"#{item_num}"
    draw.text((pad, y), num_str, font=f_num, fill=template.accent_color)
    y += _line_height(f_num) + 24

    # ── Tool name + logo row ──
    f_name = _font(template.headline_font, 72)
    logo_size = 100

    # Place logo
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        except Exception:
            logo = _logo_fallback(template, tool_name[0] if tool_name else "?", logo_size)
    else:
        logo = _logo_fallback(template, tool_name[0] if tool_name else "?", logo_size)

    img.paste(logo, (pad, y), logo if logo.mode == "RGBA" else None)

    # Tool name next to logo
    name_x = pad + logo_size + 20
    name_max_w = max_w - logo_size - 20
    name_lines = _wrap(tool_name, f_name, name_max_w)
    name_y = y + (logo_size - _line_height(f_name) * len(name_lines)) // 2
    for nl in name_lines:
        draw.text((name_x, name_y), nl.upper(), font=f_name, fill=template.text_color)
        name_y += _line_height(f_name) + 2

    # Category pill (top-right area)
    if category:
        f_cat = _font(template.body_font_semibold, 24)
        cat_text = category.upper()
        cat_w = int(draw.textlength(cat_text, font=f_cat))
        cat_h = _line_height(f_cat)
        cat_pad_x, cat_pad_y = 16, 8
        cat_x = W - pad - cat_w - 2 * cat_pad_x
        cat_y = y + 10
        draw.rounded_rectangle(
            [cat_x, cat_y, cat_x + cat_w + 2 * cat_pad_x, cat_y + cat_h + 2 * cat_pad_y],
            radius=14, fill=template.secondary_accent,
        )
        draw.text((cat_x + cat_pad_x, cat_y + cat_pad_y), cat_text, font=f_cat, fill=(255, 255, 255))

    y += logo_size + 30

    # ── Value prop (one-liner with accent highlights) ──
    if value_prop:
        f_prop = _font(template.body_font_semibold, 36)
        # Highlight key words (those that are capitalised or technical terms)
        words = value_prop.split()
        accent_idx = set()
        for i, w in enumerate(words):
            clean = w.strip(".,!?;:")
            if len(clean) > 3 and (clean[0].isupper() or any(c in clean for c in ".-_/")):
                accent_idx.add(i)

        star_f = _font(template.headline_font, 36)
        draw.text((pad, y), "★", font=star_f, fill=template.accent_color)
        prop_x = pad + 36
        prop_w = max_w - 36
        prop_lines = _wrap(value_prop, f_prop, prop_w)
        prop_lh = _line_height(f_prop)
        for pl in prop_lines:
            draw.text((prop_x, y), pl, font=f_prop, fill=template.text_color)
            y += prop_lh + 4
        y += 20

    # ── Repo-style card (dark rounded rect) ──
    card_h = 70
    card_color = (40, 40, 60) if template.template_id == "dark_tech" else (230, 230, 235)
    draw.rounded_rectangle(
        [pad, y, W - pad, y + card_h],
        radius=16, fill=card_color,
    )
    f_repo = _font(template.body_font, 30)
    repo_text = tool_name.lower().replace(" ", "-")
    repo_icon = "📦"
    repo_label = f"{repo_icon}  {repo_text}"
    repo_lh = _line_height(f_repo)
    draw.text((pad + 20, y + (card_h - repo_lh) // 2), repo_label, font=f_repo, fill=template.text_color)

    # "Public" badge
    f_badge = _font(template.body_font, 22)
    badge_text = "Public"
    badge_w = int(draw.textlength(badge_text, font=f_badge))
    badge_h = _line_height(f_badge)
    badge_pad = 10
    badge_x = W - pad - badge_w - 2 * badge_pad - 20
    badge_y = y + (card_h - badge_h - 2 * badge_pad) // 2
    badge_outline = template.gray_color
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w + 2 * badge_pad, badge_y + badge_h + 2 * badge_pad],
        radius=10, outline=badge_outline, width=1,
    )
    draw.text((badge_x + badge_pad, badge_y + badge_pad), badge_text, font=f_badge, fill=template.gray_color)

    y += card_h + 30

    # ── Bullet points (3 details with arrow prefix) ──
    f_bullet = _font(template.body_font, 30)
    f_bullet_highlight = _font(template.body_font_semibold, 30)
    bullet_lh = _line_height(f_bullet)
    arrow_f = _font(template.body_font_semibold, 30)
    arrow_color = template.accent_color

    # Vertical connector line
    if bullets:
        line_x = pad + 10
        line_top = y + 5
        line_bottom = y + len(bullets) * (bullet_lh + 50) - 30
        draw.line([(line_x, line_top), (line_x, line_bottom)], fill=template.accent_color, width=3)

    for bi, bullet in enumerate(bullets[:3]):
        # Arrow marker
        arrow_y = y + 2
        draw.text((pad + 22, arrow_y), "→", font=arrow_f, fill=arrow_color)

        # Bullet text with keyword highlighting
        bx = pad + 54
        bw = max_w - 54
        b_lines = _wrap(bullet, f_bullet, bw)
        for bl in b_lines:
            # Simple highlight: underline key terms (words with capitals)
            draw.text((bx, y), bl, font=f_bullet, fill=template.text_color)
            y += bullet_lh + 4
        y += 16

    return img


def _slide_cta_engage(total: int, template: TemplateConfig = DARK_TECH, keyword: str = "LINK") -> Image.Image:
    """
    Listicle CTA slide — engagement-first.
    "Comment [KEYWORD] to get all the links in your DMs!"
    """
    img = _bg_canvas(template)
    img = _vignette_edges(img, strength=100, template=template)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw, template)
    _draw_slide_counter(draw, total, total, template)

    pad = 44
    max_w = W - 2 * pad

    f_big = _font(template.headline_font, 96)
    f_keyword = _font(template.headline_font, 110)
    f_sub = _font(template.body_font_semibold, 38)
    f_handle = _font(template.headline_font, 64)

    # Layout: "Comment" / "[KEYWORD]" / "to get all the" / "links in your DMs!"
    lines = [
        ("COMMENT", f_big, template.text_color),
        (f'"{keyword}"', f_keyword, template.accent_color),
        ("TO GET ALL THE", f_big, template.text_color),
        ("LINKS IN YOUR DMS!", f_big, template.text_color),
    ]

    # Measure total height
    total_h = sum(_text_block_height(t, f, max_w, 0) for t, f, _ in lines)
    total_h += (len(lines) - 1) * 12  # gaps
    handle_h = _text_block_height(template.brand_handle.upper(), f_handle, max_w, 0)
    total_h += 40 + handle_h

    y = (H - total_h) // 2

    for text, font, color in lines:
        h = _text_block_height(text, font, max_w, 0)
        _draw_text_block(draw, text, pad, y, font, color, max_w, spacing=0, align="center")
        y += h + 12

    y += 28
    _draw_text_block(draw, template.brand_handle, pad, y, f_handle, template.accent_color, max_w, spacing=0, align="center")

    return img


# ── Public API ─────────────────────────────────────────────────────────────────

def render_carousel(
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes] = None,
    hook_stat_value: str = "",
    hook_stat_label: str = "",
    output_dir: Optional[str] = None,
    source_url: str | None = None,
    content_type: str = "news",
    carousel_format: Optional[str] = None,
    template_id: str = "dark_tech",
) -> list[str]:
    """
    Render a 4+ slide carousel and save PNGs to output_dir (default: /tmp).

    Args:
        headline:          Hook headline for the cover slide.
        stats:             Bullet-point stats for content slide(s).
        image_bytes:       Optional raw bytes of a JPEG/PNG for the cover slide.
        hook_stat_value:   Big number for slide 2 (e.g. "70%"). Used by Format B.
        hook_stat_label:   Context for slide 2. Used by Format B.
        output_dir:        Directory to save PNGs. Defaults to /tmp.
        source_url:        Source article URL — adds a "Read More" slide if present.
        content_type:      "news" (default) or "educational".
        carousel_format:   "A" (Mistakes), "B" (Pillars), "C" (Cheat Sheet), or None (legacy).
        template_id:       Visual theme — "dark_tech" or "clean_light".

    Returns:
        List of absolute file paths to the generated PNGs.
    """
    template = get_template(template_id)
    out = Path(output_dir or "/tmp")
    out.mkdir(parents=True, exist_ok=True)

    has_read_more = bool(source_url)

    if content_type == "educational" and carousel_format in ("A", "B", "C"):
        # ── v5 Phase 2: multi-format educational path ──────────────────────────
        if carousel_format == "C":
            # Format C: 3 tips per slide, no bookmark, save CTA
            batches: list[list[str]] = []
            for i in range(0, max(len(stats), 1), 3):
                batch = stats[i:i + 3]
                if batch:
                    batches.append(batch)

            has_bookmark = False
            total = 2 + len(batches) + (1 if has_read_more else 0) + 1

            slide_2 = _slide_cheat_intro(2, total, template=template)
            content_slides = [_slide_cheat_batch(b, 3 + i, total, template=template) for i, b in enumerate(batches)]
            cta_slide = _slide_cta_save(total, template=template)

        elif carousel_format == "A":
            # Format A: 1 mistake per slide, bookmark, send CTA
            content_slides_data = stats  # 1 stat per slide
            has_bookmark = len(content_slides_data) >= 2
            bookmark_after = len(content_slides_data) // 2

            # Pre-compute total: cover + slide2 + n content + bookmark? + read_more? + cta
            total = 2 + len(content_slides_data) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

            slide_2 = _slide_format_a_hook(2, total, template=template)

            # Build content slides with correct slide numbers (accounting for bookmark insertion)
            content_slides = []
            bookmark_slide = None
            slide_num = 3
            for i, stat in enumerate(content_slides_data):
                content_slides.append(_slide_mistake(stat, slide_num, total, template=template))
                slide_num += 1
                if has_bookmark and i == bookmark_after - 1:
                    bookmark_slide = _slide_bookmark(slide_num, total, template=template)
                    slide_num += 1

            cta_slide = _slide_cta(total, template=template)

        else:
            # Format B (Pillars): 1 concept per slide, bookmark, send CTA
            content_slides_data = stats
            has_bookmark = len(content_slides_data) >= 2
            bookmark_after = len(content_slides_data) // 2

            total = 2 + len(content_slides_data) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

            slide_2 = _slide_hook_stat(hook_stat_value, hook_stat_label, total, template=template)

            content_slides = []
            bookmark_slide = None
            slide_num = 3
            for i, stat in enumerate(content_slides_data):
                content_slides.append(_slide_pillar(stat, slide_num, total, template=template))
                slide_num += 1
                if has_bookmark and i == bookmark_after - 1:
                    bookmark_slide = _slide_bookmark(slide_num, total, template=template)
                    slide_num += 1

            cta_slide = _slide_cta(total, template=template)

        # Assemble slides list
        slides: list[Image.Image] = [
            _slide_cover(headline, image_bytes, total, template=template),
            slide_2,
        ]

        if carousel_format == "C":
            slides.extend(content_slides)
        else:
            # For A and B, interleave bookmark after halfway point
            slide_num = 3
            bookmark_after = len(stats) // 2
            for i, s in enumerate(content_slides):
                slides.append(s)
                if has_bookmark and carousel_format != "C":
                    # bookmark_slide was built during content slide loop above
                    if bookmark_slide is not None and i == bookmark_after - 1:
                        slides.append(bookmark_slide)
                        bookmark_slide = None  # only insert once

        if has_read_more:
            slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
        slides.append(cta_slide)

    elif content_type == "educational":
        # ── Legacy educational (no carousel_format): step-by-step ─────────────
        stat_chunks: list[list[str]] = []
        for i in range(0, max(len(stats), 1), 4):
            chunk = stats[i:i + 4]
            if chunk:
                stat_chunks.append(chunk)

        has_bookmark = len(stat_chunks) >= 2
        bookmark_after_chunk = len(stat_chunks) // 2
        total = 2 + len(stat_chunks) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

        slides = [
            _slide_cover(headline, image_bytes, total, template=template),
            _slide_learn_preview(stats[:4], total, template=template),
        ]
        start_num = 0
        for idx, chunk in enumerate(stat_chunks):
            slides.append(_slide_content(chunk, len(slides) + 1, total, start_num=start_num, template=template))
            start_num += len(chunk)
            if has_bookmark and idx == bookmark_after_chunk - 1:
                slides.append(_slide_bookmark(len(slides) + 1, total, template=template))
        if has_read_more:
            slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
        slides.append(_slide_cta(total, template=template))

    else:
        # ── News path ─────────────────────────────────────────────────────────
        stat_chunks = []
        for i in range(0, max(len(stats), 1), 4):
            chunk = stats[i:i + 4]
            if chunk:
                stat_chunks.append(chunk)

        has_bookmark = len(stat_chunks) >= 2
        bookmark_after_chunk = len(stat_chunks) // 2
        total = 2 + len(stat_chunks) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

        slides = [
            _slide_cover(headline, image_bytes, total, template=template),
            _slide_hook_stat(hook_stat_value, hook_stat_label, total, template=template),
        ]
        start_num = 0
        for idx, chunk in enumerate(stat_chunks):
            slides.append(_slide_content(chunk, len(slides) + 1, total, start_num=start_num, template=template))
            start_num += len(chunk)
            if has_bookmark and idx == bookmark_after_chunk - 1:
                slides.append(_slide_bookmark(len(slides) + 1, total, template=template))
        if has_read_more:
            slides.append(_slide_read_more(source_url, len(slides) + 1, total, template=template))
        slides.append(_slide_cta(total, template=template))

    paths = []
    for i, slide in enumerate(slides, start=1):
        path = str(out / f"slide{i}.png")
        slide.save(path, "PNG", optimize=True)
        slide.close()  # free pixel buffer immediately after saving
        paths.append(path)

    logger.info(f"render_carousel: {len(paths)} slides for '{headline[:50]}' (content_type={content_type}, format={carousel_format})")
    return paths
