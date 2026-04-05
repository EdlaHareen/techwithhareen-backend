"""
Carousel Templates — visual theme configs for the Pillow renderer.

Each template is a frozen dataclass containing colors, font names, and styling
flags.  Templates are the "skin"; formats (A/B/C/listicle/news) are the
"skeleton".  Any template × any format combination should work.

Usage:
    from src.utils.carousel_templates import TEMPLATES, DARK_TECH, TemplateConfig

    template = TEMPLATES.get(template_id, DARK_TECH)
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TemplateConfig:
    """Immutable visual theme passed to every rendering function."""

    template_id: str

    # ── Colours (RGB tuples) ──────────────────────────────────────────────────
    bg_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    secondary_accent: tuple[int, int, int]
    gray_color: tuple[int, int, int]
    divider_color: tuple[int, int, int]

    # ── Fonts (logical names resolved by _font()) ─────────────────────────────
    headline_font: str          # "anton" | "space_grotesk_bold"
    body_font: str              # "inter"
    body_font_semibold: str     # "inter_sb" | "space_grotesk_medium"

    # ── Accent-background slides (Format A hook, cheat intro, bookmark) ───────
    accent_bg_color: tuple[int, int, int]
    accent_bg_text_color: tuple[int, int, int]

    # ── Cover slide ───────────────────────────────────────────────────────────
    pill_label: str
    pill_bg_color: tuple[int, int, int]
    pill_text_color: tuple[int, int, int]
    use_vignette: bool
    cover_image_blend: float    # 0.0–1.0  (not used yet, reserved)

    # ── Brand ─────────────────────────────────────────────────────────────────
    brand_handle: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateConfig":
        # Convert lists back to tuples for colour fields
        colour_fields = {
            "bg_color", "text_color", "accent_color", "secondary_accent",
            "gray_color", "divider_color", "accent_bg_color",
            "accent_bg_text_color", "pill_bg_color", "pill_text_color",
        }
        cleaned = {}
        for k, v in d.items():
            if k in colour_fields and isinstance(v, list):
                cleaned[k] = tuple(v)
            else:
                cleaned[k] = v
        return cls(**cleaned)


# ── Template instances ────────────────────────────────────────────────────────

DARK_TECH = TemplateConfig(
    template_id="dark_tech",
    bg_color=(26, 26, 46),              # #1A1A2E
    text_color=(255, 255, 255),         # white
    accent_color=(128, 117, 255),       # #8075FF
    secondary_accent=(128, 117, 255),
    gray_color=(160, 160, 160),
    divider_color=(80, 75, 180),
    headline_font="anton",
    body_font="inter",
    body_font_semibold="inter_sb",
    accent_bg_color=(128, 117, 255),    # #8075FF
    accent_bg_text_color=(26, 26, 46),  # dark navy on accent bg
    pill_label="DO YOU KNOW",
    pill_bg_color=(128, 117, 255),
    pill_text_color=(255, 255, 255),
    use_vignette=True,
    cover_image_blend=0.3,
    brand_handle="@techwithhareen",
)

CLEAN_LIGHT = TemplateConfig(
    template_id="clean_light",
    bg_color=(245, 245, 245),           # off-white
    text_color=(30, 30, 30),            # near-black
    accent_color=(220, 53, 69),         # red accent
    secondary_accent=(59, 130, 246),    # blue for category pills
    gray_color=(120, 120, 120),
    divider_color=(200, 200, 200),
    headline_font="space_grotesk_bold",
    body_font="inter",
    body_font_semibold="space_grotesk_medium",
    accent_bg_color=(255, 230, 50),     # yellow highlight
    accent_bg_text_color=(30, 30, 30),  # dark text on yellow
    pill_label="CHECK THIS OUT",
    pill_bg_color=(220, 53, 69),        # red pill
    pill_text_color=(255, 255, 255),
    use_vignette=False,
    cover_image_blend=0.1,
    brand_handle="@techwithhareen",
)


# ── Registry ──────────────────────────────────────────────────────────────────

TEMPLATES: dict[str, TemplateConfig] = {
    "dark_tech": DARK_TECH,
    "clean_light": CLEAN_LIGHT,
}

DEFAULT_TEMPLATE_ID = "dark_tech"


def get_template(template_id: str) -> TemplateConfig:
    """Resolve template_id to a TemplateConfig, falling back to DARK_TECH."""
    return TEMPLATES.get(template_id, DARK_TECH)
