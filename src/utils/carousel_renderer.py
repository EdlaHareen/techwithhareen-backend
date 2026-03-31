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

_SYSTEM_BOLD = [
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


@lru_cache(maxsize=32)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    paths = {
        "anton":    [_ANTON] + _SYSTEM_BOLD,
        "inter":    [_INTER],
        "inter_sb": [_INTER_SB, _INTER],
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
            color = ACCENT if idx in accent_indices else WHITE
            ww = int(dummy.textlength(w.upper(), font=font))
            draw.text((dx, y), w.upper(), font=font, fill=color)
            dx += ww + sp

        y += lh + spacing

    return y


# ── Background & image helpers ─────────────────────────────────────────────────

def _black_canvas() -> Image.Image:
    return Image.new("RGB", (W, H), BG)


def _place_image_top(base: Image.Image, image_bytes: bytes, frac: float = 0.52) -> Image.Image:
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

        # Bottom vignette — gradient from transparent to black
        vignette = Image.new("RGBA", (W, img_h), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        vig_start = int(img_h * 0.45)
        for row in range(vig_start, img_h):
            alpha = int(255 * (row - vig_start) / (img_h - vig_start))
            vd.line([(0, row), (W, row)], fill=(0, 0, 0, alpha))

        story_rgba = story.convert("RGBA")
        story_rgba = Image.alpha_composite(story_rgba, vignette)

        base.paste(story_rgba.convert("RGB"), (0, 0))
    except Exception as e:
        logger.warning(f"Could not place image: {e}")

    return base


def _vignette_edges(img: Image.Image, strength: int = 140) -> Image.Image:
    """Subtle edge vignette on a full black canvas slide."""
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(vig)
    steps = 80
    for i in range(steps):
        alpha = int(strength * (i / steps) ** 2)
        margin = i * 6
        d.rectangle(
            [margin, margin, W - margin, H - margin],
            outline=(0, 0, 0, strength - alpha),
            width=6,
        )
    return Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")


# ── Brand label ────────────────────────────────────────────────────────────────

def _draw_brand(draw: ImageDraw.ImageDraw, y_top: int = 36) -> None:
    """Top-left: small '@techwithhareen' in accent color."""
    f = _font("inter_sb", 26)
    draw.text((44, y_top), "@techwithhareen", font=f, fill=ACCENT)


def _draw_slide_counter(draw: ImageDraw.ImageDraw, current: int, total: int) -> None:
    """Top-right: '1 / 4' in gray."""
    f = _font("inter", 24)
    label = f"{current} / {total}"
    lw = draw.textlength(label, font=f)
    draw.text((W - 44 - lw, 36), label, font=f, fill=GRAY)


# ── Slide builders ─────────────────────────────────────────────────────────────

def _slide_cover(headline: str, image_bytes: Optional[bytes], total: int) -> Image.Image:
    """
    Slide 1 — Cover.
    Top 52%: story image with bottom vignette.
    Bottom 48%: "DO YOU KNOW" label + massive headline, word-level accent highlights.
    """
    img = _black_canvas()

    if image_bytes:
        img = _place_image_top(img, image_bytes, frac=0.52)

    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, 1, total)

    pad = 44
    text_zone_top = int(H * 0.50)
    max_w = W - 2 * pad

    # "DO YOU KNOW" pill label
    label_f = _font("inter_sb", 28)
    label = "DO YOU KNOW"
    lw = int(draw.textlength(label, font=label_f))
    lh = _line_height(label_f)
    pill_pad_x, pill_pad_y = 18, 10
    pill_x = (W - lw - 2 * pill_pad_x) // 2
    pill_y = text_zone_top + 10
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + lw + 2 * pill_pad_x, pill_y + lh + 2 * pill_pad_y],
        radius=20, fill=ACCENT,
    )
    draw.text((pill_x + pill_pad_x, pill_y + pill_pad_y), label, font=label_f, fill=WHITE)

    # Headline — Anton, large, word-level accent on first 2 key words
    headline_f = _font("anton", 108)
    words = headline.split()
    # Accent the first word + any word longer than 5 chars in first half
    accent_idx = {0}
    for i, w in enumerate(words[:len(words) // 2 + 1]):
        if len(w) > 5:
            accent_idx.add(i)
            break

    y = pill_y + lh + 2 * pill_pad_y + 24
    _draw_alternating(draw, words, accent_idx, pad, y, headline_f, max_w, spacing=6, align="center")

    return img


def _slide_hook_stat(hook_stat_value: str, hook_stat_label: str, total: int) -> Image.Image:
    """
    Slide 2 — Hook Stat.
    Black bg. The single most shocking number blown up in accent color.
    Short context label in white underneath.

    Falls back to a generic teaser if no hook stat is available.
    """
    img = _black_canvas()
    img = _vignette_edges(img, strength=60)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, 2, total)

    pad = 44
    max_w = W - 2 * pad

    if hook_stat_value:
        # Big number — as large as it can go (auto-size to fit)
        for size in range(320, 80, -10):
            f_num = _font("anton", size)
            if draw.textlength(hook_stat_value.upper(), font=f_num) <= max_w:
                break

        f_label = _font("anton", 72)

        num_h = _line_height(f_num) + 20   # extra breathing room below number
        label_h = _text_block_height(hook_stat_label, f_label, max_w, spacing=4) if hook_stat_label else 0
        gap = 28
        block_h = num_h + (gap + label_h if hook_stat_label else 0)
        y = (H - block_h) // 2

        # Big accent number
        nw = int(draw.textlength(hook_stat_value.upper(), font=f_num))
        draw.text(((W - nw) // 2, y), hook_stat_value.upper(), font=f_num, fill=ACCENT)
        y += num_h

        # Context label in white
        if hook_stat_label:
            y += gap
            _draw_text_block(draw, hook_stat_label, pad, y, f_label, WHITE, max_w, spacing=4, align="center")
            y += label_h

    else:
        # Fallback: accent bg with generic teaser
        img = Image.new("RGB", (W, H), ACCENT)
        draw = ImageDraw.Draw(img)
        _draw_brand(draw)
        _draw_slide_counter(draw, 2, total)

        f = _font("anton", 120)
        h1 = _text_block_height("THIS IS", f, max_w, spacing=0)
        h2 = _text_block_height("INSANE.", f, max_w, spacing=0)
        gap = 30
        y = (H - h1 - gap - h2) // 2
        _draw_text_block(draw, "THIS IS", pad, y, f, (0, 0, 0), max_w, spacing=0, align="center")
        y += h1 + gap
        _draw_text_block(draw, "INSANE.", pad, y, f, WHITE, max_w, spacing=0, align="center")

    return img


def _slide_content(stats: list[str], slide_num: int, total: int, start_num: int = 0) -> Image.Image:
    """
    Slide 3+ — Content bullets.
    Each stat is formatted as "HEADLINE\nExplanation sentence".
    Black bg, accent number, white headline, gray explanation.
    Items are distributed evenly to fill the full slide height.
    Numbering is continuous across content slides via start_num.
    """
    img = _black_canvas()
    img = _vignette_edges(img, strength=80)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, slide_num, total)

    pad = 44
    num_f = _font("anton", 68)
    headline_f = _font("inter_sb", 38)
    body_f = _font("inter", 30)
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
        draw.text((pad, y), num_str, font=num_f, fill=ACCENT)

        # Draw headline — vertically aligned to number top
        hy = y + max(0, (num_h - text_block_h) // 2)
        for line in headline_lines:
            draw.text((text_x, hy), line.upper(), font=headline_f, fill=WHITE)
            hy += _line_height(headline_f) + 4

        # Draw explanation below headline
        if body_lines:
            by = y + max(0, (num_h - text_block_h) // 2) + headline_h + gap
            for line in body_lines:
                draw.text((text_x, by), line, font=body_f, fill=GRAY)
                by += _line_height(body_f) + 3

        # Divider between items
        if i < n - 1:
            div_y = slot_top + slot_h - 1
            draw.line([(pad, div_y), (W - pad, div_y)], fill=(80, 75, 180), width=1)

    return img


def _slide_read_more(url: str, slide_num: int, total: int) -> Image.Image:
    """
    Read More slide — second-to-last.
    Black bg, accent 'LINK IN' + white 'DESCRIPTION' — no URL on slide.
    The actual URL lives in the caption only.
    """
    img = _black_canvas()
    img = _vignette_edges(img, strength=100)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, slide_num, total)

    pad = 44
    max_w = W - 2 * pad

    f_big = _font("anton", 118)

    h1 = _text_block_height("LINK IN", f_big, max_w, 0)
    h2 = _text_block_height("DESCRIPTION", f_big, max_w, 0)
    gap = 16
    block_h = h1 + gap + h2
    y = (H - block_h) // 2

    _draw_text_block(draw, "LINK IN", pad, y, f_big, ACCENT, max_w, spacing=0, align="center")
    y += h1 + gap
    _draw_text_block(draw, "DESCRIPTION", pad, y, f_big, WHITE, max_w, spacing=0, align="center")

    return img


def _slide_bookmark(slide_num: int, total: int) -> Image.Image:
    """
    Mid-carousel bookmark slide — inserted when total slides >= 8.
    Accent bg with 'BOOKMARK THIS' in large white Anton type.
    Reinforces save behaviour mid-scroll.
    """
    img = Image.new("RGB", (W, H), ACCENT)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, slide_num, total)

    pad = 44
    max_w = W - 2 * pad
    f = _font("anton", 118)
    f_sub = _font("inter_sb", 40)

    h1 = _text_block_height("BOOKMARK", f, max_w, 0)
    h2 = _text_block_height("THIS", f, max_w, 0)
    h3 = _line_height(f_sub)
    gap = 20
    total_h = h1 + gap + h2 + gap + h3
    y = (H - total_h) // 2

    _draw_text_block(draw, "BOOKMARK", pad, y, f, WHITE, max_w, spacing=0, align="center")
    y += h1 + gap
    _draw_text_block(draw, "THIS", pad, y, f, (0, 0, 0), max_w, spacing=0, align="center")
    y += h2 + gap
    sub = "SAVE THIS FOR LATER"
    sw = int(draw.textlength(sub, font=f_sub))
    draw.text(((W - sw) // 2, y), sub, font=f_sub, fill=WHITE)

    return img


def _slide_learn_preview(steps_preview: list[str], total: int) -> Image.Image:
    """
    Slide 2 — What You'll Learn (educational carousels only).
    Accent bg, "WHAT YOU'LL LEARN" header, 3-4 step bullet lines in white.
    Replaces the hook stat slide when content_type='educational'.
    """
    img = Image.new("RGB", (W, H), ACCENT)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, 2, total)

    pad = 44
    max_w = W - 2 * pad

    # Title: "WHAT YOU'LL LEARN"
    title_f = _font("anton", 88)
    title_h = _text_block_height("WHAT YOU'LL LEARN", title_f, max_w, spacing=0)

    # Divider
    divider_h = 4
    divider_margin_top = 24
    divider_margin_bottom = 40

    # Measure bullets (first line of each step only)
    bullet_f = _font("inter_sb", 36)
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
    _draw_text_block(draw, "WHAT YOU'LL LEARN", pad, y, title_f, WHITE, max_w, spacing=0, align="center")
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
        draw.text((pad, y), label, font=bullet_f, fill=WHITE)
        y += bullet_spacing

    return img


def _slide_cta(total: int) -> Image.Image:
    """
    Slide 4 — CTA (evergreen).
    Black bg, massive white text, accent handle.
    """
    img = _black_canvas()
    img = _vignette_edges(img, strength=100)
    draw = ImageDraw.Draw(img)
    _draw_brand(draw)
    _draw_slide_counter(draw, total, total)

    f_big = _font("anton", 118)
    f_handle = _font("anton", 72)
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
        _draw_text_block(draw, line, pad, y, f_big, WHITE, max_w, spacing=0, align="center")
        y += lh + 10

    y += gap
    _draw_text_block(draw, "@techwithhareen", pad, y, f_handle, ACCENT, max_w, spacing=0, align="center")

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
) -> list[str]:
    """
    Render a 4+ slide carousel and save PNGs to output_dir (default: /tmp).

    Args:
        headline:          Hook headline for the cover slide.
        stats:             Bullet-point stats for content slide(s). Max 4 per slide.
        image_bytes:       Optional raw bytes of a JPEG/PNG for the cover slide.
        hook_stat_value:   Big number for slide 2 (e.g. "70%").
        hook_stat_label:   Context for slide 2 (e.g. "OF SAMSUNG RAM GOES TO NVIDIA").
        output_dir:        Directory to save PNGs. Defaults to /tmp.
        source_url:        Source article URL — adds a "Read More" slide if present.
        content_type:      "news" (default) or "educational". When "educational",
                           Slide 2 shows WHAT YOU'LL LEARN instead of the hook stat.

    Returns:
        List of absolute file paths to the generated PNGs.
    """
    out = Path(output_dir or "/tmp")
    out.mkdir(parents=True, exist_ok=True)

    # Split stats into content slides (max 4 per slide)
    stat_chunks: list[list[str]] = []
    for i in range(0, max(len(stats), 1), 4):
        chunk = stats[i:i + 4]
        if chunk:
            stat_chunks.append(chunk)

    has_read_more = bool(source_url)

    # Determine if a mid-carousel bookmark slide is needed
    has_bookmark = len(stat_chunks) >= 2  # 8+ total slides means 2+ content slides
    bookmark_after_chunk = len(stat_chunks) // 2  # insert after halfway content slide

    # Recalculate total including bookmark slide
    total = 2 + len(stat_chunks) + (1 if has_bookmark else 0) + (1 if has_read_more else 0) + 1

    if content_type == "educational":
        slide_2 = _slide_learn_preview(stats[:4], total)
    else:
        slide_2 = _slide_hook_stat(hook_stat_value, hook_stat_label, total)

    slides: list[Image.Image] = [
        _slide_cover(headline, image_bytes, total),
        slide_2,
    ]
    start_num = 0
    for idx, chunk in enumerate(stat_chunks):
        slides.append(_slide_content(chunk, len(slides) + 1, total, start_num=start_num))
        start_num += len(chunk)
        # Insert bookmark slide after the halfway content slide
        if has_bookmark and idx == bookmark_after_chunk - 1:
            slides.append(_slide_bookmark(len(slides) + 1, total))
    if has_read_more:
        slides.append(_slide_read_more(source_url, len(slides) + 1, total))
    slides.append(_slide_cta(total))

    paths = []
    for i, slide in enumerate(slides, start=1):
        path = str(out / f"slide{i}.png")
        slide.save(path, "PNG", optimize=True)
        slide.close()  # free pixel buffer immediately after saving
        paths.append(path)

    logger.info(f"render_carousel: {len(paths)} slides for '{headline[:50]}'")
    return paths
