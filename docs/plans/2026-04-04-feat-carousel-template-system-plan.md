---
title: "feat: Carousel Template System — Visual Themes + Listicle Format"
type: feat
status: active
date: 2026-04-04
brainstorm: docs/brainstorms/2026-04-04-carousel-template-system-brainstorm.md
---

# Carousel Template System — Visual Themes + Listicle Format

## Overview

Separate **visual style** (template) from **content structure** (format) in the carousel rendering pipeline. Users pick a template and format in the Web UI, type a topic, and the backend generates carousels using Pillow with the selected template's rendering config. Defaults are saved per-user in Firestore.

**Two templates at launch:**
- **Dark Tech** — current UncoverAI (navy #1A1A2E, periwinkle #8075FF, Anton + Inter)
- **Clean Light** — white/light bg, black text, colored accent highlights, SpaceGrotesk + Inter fonts (inspired by @vishakha.sadhwani)

**New format:** Listicle — one tool/product per slide with logo, category pill, value prop, 3 bullet details.

---

## Problem Statement

| Problem | Root Cause |
|---|---|
| Single visual style doesn't suit all content types | All design tokens hardcoded as module-level constants |
| Tool roundups / listicles look wrong in dark theme | No template abstraction — can't swap colors/fonts |
| No way to save visual preferences | No user_preferences in Firestore |
| Listicle content (one item per slide) has no format | Only News + A/B/C formats exist |

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Rendering engine | Pillow (no change) | Proven, fast, no browser dependency |
| Template = Python dataclass | `TemplateConfig` with colors, fonts, layout | Simple, type-safe, no config files |
| Template × Format | Independent axes | Any template can render any format |
| Font cache | Include template_id in cache key | Prevent font bleed across templates |
| Caption voice | Unchanged by template | Hareen's voice is brand, not design |
| render_data | Store template_id + frozen config snapshot | Re-renders use original template even after defaults change |
| Listicle scope | Works for both news and educational | Not limited to educational-only |
| Logo fallback | Colored initial circle | When Serper returns no usable logo |

---

## Phase 1: TemplateConfig Dataclass + Parameterize Renderer

### 1.1 Create `src/utils/carousel_templates.py`

```python
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class TemplateConfig:
    """Immutable template config — passed to every rendering function."""
    template_id: str

    # Colors (RGB tuples)
    bg_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    secondary_accent: tuple[int, int, int]   # for category pills, highlights
    gray_color: tuple[int, int, int]
    divider_color: tuple[int, int, int]

    # Fonts (logical names — resolved by _font())
    headline_font: str          # "anton" or "space_grotesk_bold"
    body_font: str              # "inter" or "inter"
    body_font_semibold: str     # "inter_sb" or "space_grotesk_medium"

    # Accent background slides (Format A hook, cheat intro, bookmark)
    accent_bg_color: tuple[int, int, int]
    accent_bg_text_color: tuple[int, int, int]

    # Cover slide
    pill_label: str             # "DO YOU KNOW" or "CHECK THIS OUT"
    pill_bg_color: tuple[int, int, int]
    pill_text_color: tuple[int, int, int]
    use_vignette: bool          # Dark Tech = True, Clean Light = False
    cover_image_blend: float    # 0.0–1.0, how much to darken cover image

    # Brand
    brand_handle: str           # "@TECHWITHHAREEN"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TemplateConfig":
        return cls(**d)


# ── Template Registry ─────────────────────────────────────────────────────────

DARK_TECH = TemplateConfig(
    template_id="dark_tech",
    bg_color=(26, 26, 46),           # #1A1A2E
    text_color=(255, 255, 255),      # white
    accent_color=(128, 117, 255),    # #8075FF
    secondary_accent=(128, 117, 255),
    gray_color=(160, 160, 160),
    divider_color=(80, 75, 180),
    headline_font="anton",
    body_font="inter",
    body_font_semibold="inter_sb",
    accent_bg_color=(128, 117, 255),
    accent_bg_text_color=(26, 26, 46),
    pill_label="DO YOU KNOW",
    pill_bg_color=(128, 117, 255),
    pill_text_color=(255, 255, 255),
    use_vignette=True,
    cover_image_blend=0.3,
    brand_handle="@TECHWITHHAREEN",
)

CLEAN_LIGHT = TemplateConfig(
    template_id="clean_light",
    bg_color=(245, 245, 245),        # off-white
    text_color=(30, 30, 30),         # near-black
    accent_color=(220, 53, 69),      # red accent (like Vishakha's)
    secondary_accent=(59, 130, 246), # blue accent for category pills
    gray_color=(120, 120, 120),
    divider_color=(200, 200, 200),
    headline_font="space_grotesk_bold",
    body_font="inter",
    body_font_semibold="space_grotesk_medium",
    accent_bg_color=(255, 230, 50),  # yellow highlight (like Vishakha's)
    accent_bg_text_color=(30, 30, 30),
    pill_label="CHECK THIS OUT",
    pill_bg_color=(220, 53, 69),
    pill_text_color=(255, 255, 255),
    use_vignette=False,
    cover_image_blend=0.1,
    brand_handle="@TECHWITHHAREEN",
)

TEMPLATES: dict[str, TemplateConfig] = {
    "dark_tech": DARK_TECH,
    "clean_light": CLEAN_LIGHT,
}

DEFAULT_TEMPLATE = "dark_tech"
```

### 1.2 Register new fonts in `_font()` (`carousel_renderer.py`)

Add SpaceGrotesk paths to the font resolver:

```python
_SPACE_GROTESK_BOLD = FONTS_DIR / "SpaceGrotesk-Bold.ttf"
_SPACE_GROTESK_MED  = FONTS_DIR / "SpaceGrotesk-Medium.ttf"

@lru_cache(maxsize=64)  # increase from 32 — more font combos
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    paths = {
        "anton":                [_ANTON] + _SYSTEM_BOLD,
        "inter":                [_INTER],
        "inter_sb":             [_INTER_SB, _INTER],
        "space_grotesk_bold":   [_SPACE_GROTESK_BOLD] + _SYSTEM_BOLD,
        "space_grotesk_medium": [_SPACE_GROTESK_MED, _INTER],
    }
    ...
```

### 1.3 Parameterize all `_slide_*` functions

Every slide builder currently reads `BG`, `WHITE`, `ACCENT`, `GRAY` as module globals. Add `template: TemplateConfig` as the **first parameter** to each function. Replace hardcoded colors with template fields.

**Functions to update** (all in `carousel_renderer.py`):

| Function | Key Changes |
|---|---|
| `_slide_cover` | `template.bg_color`, `template.text_color`, `template.accent_color`, `template.pill_label`, `template.pill_bg_color`, `template.use_vignette`, `template.cover_image_blend`, `template.headline_font` |
| `_slide_hook_stat` | `template.accent_color` for number, `template.text_color` for label, `template.headline_font` |
| `_slide_content` | `template.accent_color` for numbers, `template.text_color` for body, `template.divider_color`, `template.body_font` |
| `_slide_bookmark` | `template.accent_bg_color` bg, `template.accent_bg_text_color` text |
| `_slide_read_more` | `template.bg_color`, `template.accent_color` for "LINK IN DESCRIPTION" |
| `_slide_cta` | `template.bg_color`, `template.text_color`, `template.accent_color` for handle |
| `_slide_format_a_hook` | `template.accent_bg_color` bg, text colors |
| `_slide_mistake` | `template.accent_color` for pill + fix prefix, `template.text_color` for body |
| `_slide_pillar` | `template.accent_color` for pill, `template.text_color` for concept |
| `_slide_cheat_intro` | `template.accent_bg_color` bg |
| `_slide_cheat_batch` | `template.accent_color` for numbers, `template.divider_color` |
| `_slide_cta_save` | Same as `_slide_cta` |
| `_draw_brand` | `template.gray_color`, `template.brand_handle` |
| `_draw_alternating` | `template.accent_color`, `template.text_color` |
| `_draw_text_block` | Accept color param (already does, but callers pass hardcoded) |

**Pattern:**
```python
# Before
def _slide_cover(headline, image_bytes, total):
    img = Image.new("RGB", (W, H), BG)
    ...
    _draw_alternating(draw, lines, ..., color_a=ACCENT, color_b=WHITE)

# After
def _slide_cover(template: TemplateConfig, headline, image_bytes, total):
    img = Image.new("RGB", (W, H), template.bg_color)
    ...
    _draw_alternating(draw, lines, ..., color_a=template.accent_color, color_b=template.text_color)
```

### 1.4 Update `render_carousel()` and `render_educational_carousel()`

Add `template_id: str = "dark_tech"` parameter. Resolve to `TemplateConfig` via `TEMPLATES[template_id]`. Pass template to all slide builders.

```python
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
    template_id: str = "dark_tech",          # NEW
) -> list[str]:
    template = TEMPLATES.get(template_id, DARK_TECH)
    ...
```

Same for `render_educational_carousel()`.

### 1.5 Update `carousel_service.create_carousel()`

Thread `template_id` through:

```python
async def create_carousel(
    headline: str,
    key_stats: list[str],
    image_url: Optional[str] = None,
    hook_stat_value: str = "",
    hook_stat_label: str = "",
    source_url: str | None = None,
    content_type: str = "news",
    carousel_format: Optional[str] = None,
    template_id: str = "dark_tech",          # NEW
) -> CarouselResult:
```

---

## Phase 2: Listicle Format

### 2.1 Add FORMAT_INSTRUCTIONS for Listicle

In `src/agents/research_orchestrator/orchestrator.py`, add to `FORMAT_INSTRUCTIONS`:

```python
FORMAT_INSTRUCTIONS["listicle"] = """
Format: LISTICLE (one tool/product per slide)
Each key_stat MUST follow this exact format (four lines, separated by \\n):
"[Tool/Product Name]\\n[Category — 1-2 words, e.g. GitOps, MLOps, AI Agent]\\n[One-liner value prop — what it does in 1 sentence, max 100 chars]\\n[Bullet 1]|||[Bullet 2]|||[Bullet 3]"
Example: "ArgoCD\\nGitOps\\nAutomatically deploys your code from Git to Kubernetes\\nGuides & tutorials for CI/CD|||Integrates with Helm & Crossplane|||Best practices for prod deployments"
Generate 5-8 tools/products. Each must be a REAL, existing tool — do not hallucinate.
hook_stat_value: the total tool count as a string (e.g. "5" or "8").
hook_stat_label: return a personalized list title like "TOOLS I ACTUALLY USE" or "REPOS WORTH BOOKMARKING" (all caps).
image_query: target a collage or grid of the first tool's logo — e.g. "ArgoCD logo".
"""
```

### 2.2 Add listicle slide builders in `carousel_renderer.py`

```python
def _slide_listicle_item(
    template: TemplateConfig,
    stat: str,
    item_num: int,
    logo_bytes: Optional[bytes],
    slide_num: int,
    total: int,
) -> Image.Image:
    """One tool/product per slide: #N, name, logo, category pill, value prop, 3 bullets."""
    ...
```

**Slide layout (Clean Light inspired):**
- Top-left: `#N` in handwritten/bold style
- Below: Tool name in large headline font + logo image (right-aligned)
- Right: Category pill (colored rounded rect)
- Star bullet: one-liner value prop in accent-highlighted text
- Dark card: GitHub-style repo card with org/tool name
- Arrow bullets: 3 detail points with keyword highlighting

### 2.3 Add `_render_listicle()` to `educational_renderer.py`

```python
def _render_listicle(
    template: TemplateConfig,
    headline: str,
    stats: list[str],
    image_bytes: Optional[bytes],
    tool_logos: dict[str, Optional[bytes]],  # tool_name -> logo bytes
    hook_stat_value: str,
    hook_stat_label: str,
    output_dir: str,
    source_url: Optional[str],
) -> list[str]:
    """Listicle: cover + 1-tool-per-slide + CTA."""
    slides = []
    total = 1 + len(stats) + 1  # cover + items + CTA (no bookmark for listicle)

    # Cover — personal framing
    slides.append(_slide_cover(template, headline, image_bytes, total))

    # Per-item slides
    for i, stat in enumerate(stats):
        tool_name = stat.split("\n")[0] if "\n" in stat else stat
        logo = tool_logos.get(tool_name)
        slides.append(_slide_listicle_item(template, stat, i + 1, logo, i + 2, total))

    # CTA — engagement-first
    slides.append(_slide_cta_engage(template, total))  # "Comment [KEYWORD] for links"

    return _save_slides(slides, output_dir)
```

### 2.4 Logo fetching in `carousel_service.py`

For listicle format, fetch logos for each tool before rendering:

```python
async def _fetch_tool_logos(stats: list[str]) -> dict[str, Optional[bytes]]:
    """Fetch logos for each tool in a listicle via Serper image search."""
    logos = {}
    for stat in stats:
        tool_name = stat.split("\n")[0] if "\n" in stat else stat
        query = f"{tool_name} logo transparent png"
        try:
            img_url = await _search_image(query)  # existing Serper helper
            if img_url:
                logos[tool_name] = await _fetch_image_bytes(img_url)
            else:
                logos[tool_name] = None
        except Exception:
            logos[tool_name] = None
    return logos
```

**Fallback for missing logos:** Render a colored circle with the tool's first letter initial in white — handled inside `_slide_listicle_item` when `logo_bytes is None`.

### 2.5 Listicle cover slide

The cover for listicle should use **personal framing** — "My Favorite [X]" or "Best [X] for [Y]". The `headline` from the LLM synthesis should already produce this since the FORMAT_INSTRUCTIONS say to use personal framing. The `_slide_cover` function works as-is with the template config.

### 2.6 Listicle CTA slide

New function `_slide_cta_engage()` — engagement-first CTA:
- "Comment" in text_color
- "[KEYWORD]" in accent_color (highlighted/quoted)
- "to get all the links in your DMs!" in text_color
- Engagement icons (heart, comment, share) rendered as simple shapes

---

## Phase 3: Pipeline Integration

### 3.1 Add `template_id` to Story dataclass

```python
# src/utils/story.py
@dataclass
class Story:
    ...
    carousel_format: Optional[str] = None   # "A" | "B" | "C" | "listicle" | None
    template_id: str = "dark_tech"          # NEW — "dark_tech" | "clean_light"
```

Update `to_dict()` to include `template_id`.

### 3.2 Update PostCreatorAgent

```python
# src/agents/post_creator/agent.py
async def run(self, story: Story, content_type: str = "news") -> CarouselResult:
    return await create_carousel(
        ...
        carousel_format=story.carousel_format,
        template_id=story.template_id,         # NEW — pass through
    )
```

### 3.3 Update API routes (`routes_v2.py`)

**ResearchRequest model:**
```python
class ResearchRequest(BaseModel):
    topic: str
    content_type: Literal["news", "educational"] = "news"
    carousel_format: Optional[str] = None      # "A" | "B" | "C" | "listicle"
    clarifier_answers: Optional[dict[str, str]] = None
    template_id: str = "dark_tech"             # NEW
```

**Thread template_id through the pipeline:**
- `_run_research_pipeline()` sets `story.template_id = request.template_id`
- `render_data` dict includes `template_id` and full `template_config` snapshot

**render_data update:**
```python
render_data = {
    "headline": story.headline,
    "key_stats": story.key_stats,
    "hook_stat_value": story.hook_stat_value,
    "hook_stat_label": story.hook_stat_label,
    "source_url": story.url,
    "image_url": result.image_url,
    "carousel_format": story.carousel_format,
    "template_id": story.template_id,                       # NEW
    "template_config": TEMPLATES[story.template_id].to_dict(),  # NEW — frozen snapshot
}
```

### 3.4 Update re-render endpoint

`PATCH /api/v2/posts/{post_id}/slides` — recover `template_id` from existing `render_data` (same pattern as `carousel_format`):

```python
template_id = existing_render_data.get("template_id", "dark_tech")
# Use stored template_config for consistency, or fall back to registry
```

**Do NOT allow template switching during re-render** at launch. Template is locked per post. This avoids layout mismatches when content was generated for a specific visual style.

### 3.5 Update Firestore `create_post()`

Add `template_id` to the post document:

```python
async def create_post(
    story: Story,
    slides: list[str],
    caption: str,
    render_data: Optional[dict] = None,
    carousel_format: Optional[str] = None,
    template_id: str = "dark_tech",         # NEW
    ...
) -> str:
    doc = {
        ...
        "carousel_format": carousel_format,
        "template_id": template_id,          # NEW
        ...
    }
```

### 3.6 v1 newsletter pipeline

Newsletter posts default to `template_id="dark_tech"`. No UI involvement — v1 is fully automated. Add `template_id` param with default to `InstaHandlerManager` pipeline calls.

---

## Phase 4: User Preferences in Firestore

### 4.1 Add preferences methods to `firestore_client.py`

```python
async def get_user_preferences(user_id: str = "default") -> dict:
    """Fetch user's default template + format preferences."""
    doc = _get_client().collection("user_preferences").document(user_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"default_template": "dark_tech", "default_format": "news"}

async def update_user_preferences(
    user_id: str = "default",
    default_template: Optional[str] = None,
    default_format: Optional[str] = None,
) -> None:
    """Update user's default preferences."""
    updates = {"updated_at": SERVER_TIMESTAMP}
    if default_template:
        updates["default_template"] = default_template
    if default_format:
        updates["default_format"] = default_format
    _get_client().collection("user_preferences").document(user_id).set(
        updates, merge=True
    )
```

### 4.2 Add API endpoints

```python
# GET /api/v2/preferences — fetch defaults
@router.get("/api/v2/preferences")
async def get_preferences():
    prefs = await get_user_preferences()
    return {"preferences": prefs, "available_templates": list(TEMPLATES.keys())}

# PATCH /api/v2/preferences — update defaults
@router.patch("/api/v2/preferences")
async def update_preferences(request: PreferencesRequest):
    await update_user_preferences(
        default_template=request.default_template,
        default_format=request.default_format,
    )
    return {"status": "updated"}
```

---

## Phase 5: Web UI Updates (techwithhareen-web repo)

### 5.1 Template selector component

Add a template picker to the main generate form — shows template thumbnails/cards:
- Dark Tech card: dark navy preview, "UncoverAI" label
- Clean Light card: white preview, "Clean" label
- Default badge on the user's saved default

### 5.2 Format selector

Replace or enhance the existing educational format picker (A/B/C) with a unified format dropdown:
- News (default for non-educational)
- Mistakes (A)
- Pillars (B)
- Cheat Sheet (C)
- Listicle (new)

### 5.3 Fetch preferences on load

On app mount, `GET /api/v2/preferences` → pre-select template and format dropdowns.

### 5.4 Post card badges

In the approval queue, show:
- Template badge (Dark Tech / Clean Light)
- Format badge (existing — Mistakes / Pillars / Cheat Sheet / Listicle / News)

---

## Acceptance Criteria

### Functional

- [ ] `TemplateConfig` dataclass with frozen immutable instances for Dark Tech and Clean Light
- [ ] All `_slide_*` functions accept `template: TemplateConfig` and use template colors/fonts
- [ ] `render_carousel()` and `render_educational_carousel()` accept `template_id` parameter
- [ ] Dark Tech template produces identical output to current renderer (regression check)
- [ ] Clean Light template renders all existing formats (News, A, B, C) with light theme
- [ ] Listicle format: cover + 1-tool-per-slide + engagement CTA
- [ ] Listicle logos auto-fetched via Serper; missing logos get colored initial fallback
- [ ] `template_id` flows through: API request → Story → PostCreator → carousel_service → renderer → Firestore render_data
- [ ] User preferences saved/loaded from Firestore `user_preferences` collection
- [ ] Re-render uses stored `template_id` from render_data (template locked per post)
- [ ] v1 pipeline defaults to `dark_tech` with no behavioral change

### Edge Cases Addressed

- [ ] Serper returns no logo → colored circle with initial letter
- [ ] Unknown template_id in request → falls back to `dark_tech`
- [ ] Empty key_stats → minimum 1 content slide (existing guard)
- [ ] Listicle with > 10 items → render all (no artificial cap)
- [ ] Font cache includes template context → no bleed between templates in same process

---

## Files Changed

### Backend (this repo)

| File | Change |
|---|---|
| `src/utils/carousel_templates.py` | **NEW** — TemplateConfig dataclass + DARK_TECH + CLEAN_LIGHT registry |
| `src/utils/carousel_renderer.py` | Add SpaceGrotesk fonts to `_font()`, add `template` param to all `_slide_*` functions, add `_slide_listicle_item()` and `_slide_cta_engage()` |
| `src/utils/educational_renderer.py` | Add `template_id` param, add `_render_listicle()`, pass template to all imported slide builders |
| `src/utils/carousel_service.py` | Add `template_id` param, add `_fetch_tool_logos()` for listicle, pass template_id to renderers |
| `src/utils/story.py` | Add `template_id: str = "dark_tech"` field |
| `src/utils/firestore_client.py` | Add `get_user_preferences()`, `update_user_preferences()`, add `template_id` to `create_post()` |
| `src/agents/post_creator/agent.py` | Pass `story.template_id` to `create_carousel()` |
| `src/agents/research_orchestrator/orchestrator.py` | Add `FORMAT_INSTRUCTIONS["listicle"]` |
| `src/agents/post_analyzer/agent.py` | Accept listicle CTA style ("Comment [KEYWORD]") as valid |
| `src/api/routes_v2.py` | Add `template_id` to `ResearchRequest`, thread through pipeline, add `/api/v2/preferences` endpoints |
| `src/orchestrator/handler.py` | Add `template_id="dark_tech"` default for v1 pipeline |

### Frontend (techwithhareen-web repo)

| File | Change |
|---|---|
| `src/components/GenerateForm.tsx` | Template selector + unified format selector |
| `src/components/PostCard.tsx` | Template + format badges |
| `src/api/client.ts` | Add `template_id` to research request, add preferences endpoints |
| `src/hooks/usePreferences.ts` | **NEW** — fetch/update user preferences |

---

## Implementation Order

1. **Phase 1** (template infra) — `carousel_templates.py` + parameterize renderer + verify Dark Tech regression
2. **Phase 2** (listicle format) — FORMAT_INSTRUCTIONS + slide builders + logo fetching
3. **Phase 3** (pipeline wiring) — Story field + PostCreator + routes + Firestore
4. **Phase 4** (preferences) — Firestore CRUD + API endpoints
5. **Phase 5** (web UI) — template/format selectors + preferences + badges

Phases 1-3 can be tested via API without Web UI changes. Phase 5 is in a separate repo.

---

## Open Questions (deferred)

- Should we add template preview thumbnails in the Web UI? (nice-to-have, not launch blocker)
- Should clarifier run for listicle format? (currently only for educational — could benefit from angle questions)
- Should listicle work with PDF Guide Agent? (probably not — listicle is a roundup, not a deep-dive)

## References

- Brainstorm: `docs/brainstorms/2026-04-04-carousel-template-system-brainstorm.md`
- Prior plan (educational formats): `docs/plans/2026-03-31-feat-educational-carousel-clarifier-formats-plan.md`
- Inspiration: @vishakha.sadhwani Instagram post `DWHIIjgkfZO`
- Current renderer: `src/utils/carousel_renderer.py`
- Educational renderer: `src/utils/educational_renderer.py`
