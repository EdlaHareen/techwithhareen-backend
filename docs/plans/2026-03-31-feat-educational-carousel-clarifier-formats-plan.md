---
title: "feat: Educational Carousel Redesign — Topic Clarifier + Multi-Format"
type: feat
status: active
date: 2026-03-31
brainstorm: docs/brainstorms/2026-03-31-educational-redesign-brainstorm.md
---

# Educational Carousel Redesign — Topic Clarifier + Multi-Format

## Overview

The current educational pipeline generates generic, wrong-angle carousels because it has no way to understand *what aspect* of a topic Hareen wants, and it supports only one fixed step-by-step slide format.

This plan adds two capabilities:

1. **TopicClarifierAgent** — a thinking model that generates 3–5 dynamic, topic-specific multiple-choice questions before research fires. Hareen answers them in the Web UI, and the research + renderer use the answers to produce exactly the content she had in mind.

2. **Three carousel formats** — Mistakes → Right Way (A), Core Concepts / Pillars (B), Cheat Sheet (C) — each with distinct Slide 2 design, content slide layout, CTA strategy, and synthesis prompt. Format D (Before/After split layout) is deferred.

---

## Problem Statement

| Problem | Root Cause |
|---|---|
| Wrong content angle (e.g. "how to use Manus AI" → marketing steps) | Research has no angle context before firing |
| Slide 2 redundancy — preview list mirrors Slide 3 headings | Single hardcoded "WHAT YOU'LL LEARN" format |
| Step-by-step format doesn't fit all topics | One fixed educational carousel layout |
| Layout/alignment issues on content slides | Existing renderer bugs in `carousel_renderer.py` |

---

## Architecture: What Changes Where

```
Web UI
  ↓ POST /api/v2/clarify (NEW)
TopicClarifierAgent (NEW)
  → 3–5 dynamic questions with options
  ↓
Web UI clarifier step (NEW)
  → Hareen picks answers or skips
  ↓ POST /api/v2/research (carousel_format + clarifier_answers added)
ResearchOrchestrator.run_educational(carousel_format=...) (UPDATED)
  → _synthesise_educational() — format-aware prompt (UPDATED)
  → Story.carousel_format set
  ↓
PostCreatorAgent → carousel_service → carousel_renderer (UPDATED)
  → format-specific slide functions
  ↓
PDFGuideAgent (unchanged)
  ↓
CaptionWriterAgent (unchanged)
  ↓
PostAnalyzerAgent (UPDATED — CTA check format-aware)
  ↓
Firestore — carousel_format stored (UPDATED)
  ↓
Web UI PostCard — format badge (UPDATED)
```

---

## Locked Design Decisions

### 1. API Contract — `POST /api/v2/clarify`

**Request:**
```json
{ "topic": "how to use Manus AI the right way" }
```

**Response:**
```json
{
  "questions": [
    {
      "id": "angle",
      "text": "What aspect of Manus AI are you focusing on?",
      "options": [
        { "value": "setup", "label": "First-time setup & getting started" },
        { "value": "mistakes", "label": "Common mistakes most people make" },
        { "value": "advanced", "label": "Advanced workflows & automation" },
        { "value": "comparison", "label": "Manus AI vs. other agents" }
      ],
      "default": "mistakes"
    },
    {
      "id": "audience",
      "text": "Who is this post for?",
      "options": [
        { "value": "beginner", "label": "People who've never tried it" },
        { "value": "struggling", "label": "People who tried it but feel lost" },
        { "value": "poweruser", "label": "Power users wanting to optimize" }
      ],
      "default": "struggling"
    },
    {
      "id": "format",
      "text": "Which format fits this topic?",
      "options": [
        { "value": "A", "label": "Mistakes → Right Way — what most people get wrong + the fix" },
        { "value": "B", "label": "Core Concepts / Pillars — 3–5 key ideas, each slide standalone" },
        { "value": "C", "label": "Cheat Sheet — dense tips, optimized for saves" }
      ],
      "default": "B"
    }
  ]
}
```

Rules:
- The format question always has `"id": "format"` — frontend extracts `carousel_format` from this
- All questions are single-select multiple choice — no free-text
- 3–5 questions; the thinking model decides how many are needed
- `default` is used when Hareen hits Skip

### 2. `carousel_format` on `Story` dataclass

Add `carousel_format: Optional[str] = None` to `Story` dataclass after `content_type`. Include in `to_dict()`. Set by `run_educational()` after synthesis. This makes it a first-class pipeline field, consistent with the `content_type` pattern.

Backward compat: `carousel_format=None` → existing step-by-step educational behavior (no regression on old posts).

### 3. Format-specific `key_stats` structure

Each format needs a different stat shape. The synthesis prompt generates accordingly:

| Format | `key_stat` item shape | Example |
|---|---|---|
| A — Mistakes | `"MISTAKE: [wrong thing]\nFIX: [correct approach]"` | `"MISTAKE: Setting 10 tasks at once\nFIX: Give Manus one clear goal at a time"` |
| B — Pillars | `"[Concept Name]\n[2-sentence explanation]"` | `"Scope Control\nManus works best when you define the exact output you expect upfront."` |
| C — Cheat Sheet | `"[Tip text — single line, ≤80 chars]"` | `"Use @agent to route a task to a specific Manus sub-agent"` |

The renderer parses the `\n` split and `MISTAKE:` / `FIX:` prefixes to build format-specific layouts.

### 4. Slide 2 design per format

| Format | Slide 2 content | Background |
|---|---|---|
| A | Accent bg. Large white text: bold hook claim about the mistake pattern (e.g. "MOST PEOPLE USE IT COMPLETELY WRONG"). No list. Sets up the mistake series. | `#8075FF` accent |
| B | Navy bg. Large accent number (total concept count, e.g. `"5"`). White label below: `"KEY PRINCIPLES TO MASTER"`. Mirrors the news hook stat structure — standalone. | `#1A1A2E` |
| C | Accent bg. Large white `"CHEAT SHEET"`. Smaller white text below: `"Save this — you'll use it"`. | `#8075FF` accent |

### 5. CTA strategy per format

| Format | Mid-carousel slide | Last slide CTA |
|---|---|---|
| A | BOOKMARK THIS (kept) | SEND THIS TO SOMEONE + @TECHWITHHAREEN |
| B | BOOKMARK THIS (kept) | SEND THIS TO SOMEONE + @TECHWITHHAREEN |
| C | **No BOOKMARK THIS** (redundant for a cheat sheet) | **SAVE THIS CHEAT SHEET** + @TECHWITHHAREEN |

### 6. Content slides — chunks per slide

| Format | Stats per content slide |
|---|---|
| A | 1 mistake per slide (each is a 2-field layout) |
| B | 1 concept per slide (each is a 2-field layout) |
| C | 3 tips per slide (denser, cheat-sheet feel) |

### 7. Clarifier failure fallback

If `POST /api/v2/clarify` fails (timeout, 5xx, malformed JSON):
- Frontend silently skips clarifier step
- Shows Generate button immediately with a muted note: "Using default format"
- `carousel_format` sent as `"B"` (pillar default), no `clarifier_answers`
- No blocking error shown to Hareen

### 8. Re-render backward compatibility

`render_data` stored in Firestore gains `carousel_format` field. The `PATCH /api/v2/posts/{post_id}/slides` re-render endpoint reads `carousel_format` from `render_data` when re-rendering. Legacy posts (`carousel_format=None`) use existing educational path — no regression.

### 9. PostAnalyzer — Format C CTA

Pass `story.carousel_format` into `PostAnalyzerAgent.run()`. For `carousel_format == "C"`, the CTA check accepts `"SAVE THIS CHEAT SHEET"` as valid. All other formats: `"SEND THIS TO SOMEONE"` as before.

### 10. Format C + PDFGuideAgent

All three formats still generate a PDF guide. The PDF is a useful companion regardless of format (cheat sheet PDF is even more on-brand as a lead magnet).

---

## Implementation Plan

### Phase 1 — Data Model + TopicClarifierAgent + API Endpoint
*No renderer changes yet. Lays the data contract for everything downstream.*

#### 1.1 — Add `carousel_format` to `Story`
**File:** `src/utils/story.py`

After line 43 (`content_type: Optional[str] = None`), add:
```python
# Carousel format — set by TopicClarifierAgent for educational posts
# Values: "A" (Mistakes) | "B" (Pillars) | "C" (Cheat Sheet) | None (legacy step-by-step)
carousel_format: Optional[str] = None
```

In `to_dict()` (line 57), add:
```python
"carousel_format": self.carousel_format,
```

#### 1.2 — New `TopicClarifierAgent`
**New files:** `src/agents/topic_clarifier/__init__.py`, `src/agents/topic_clarifier/agent.py`

Model: `claude-sonnet-4-6` with `thinking` enabled (budget_tokens=5000).

Structure (mirrors `src/agents/pdf_guide/agent.py`):

```python
@dataclass
class ClarifierQuestion:
    id: str
    text: str
    options: list[dict]   # [{"value": str, "label": str}]
    default: str

@dataclass
class ClarifierResult:
    questions: list[ClarifierQuestion]

class TopicClarifierAgent:
    def __init__(self):
        self._client = anthropic.AsyncAnthropic()
        self._model = "claude-sonnet-4-6"

    async def run(self, topic: str) -> ClarifierResult:
        ...

    async def _generate_questions(self, topic: str) -> dict:
        # System prompt: "You are generating clarifying questions for an Instagram 
        # educational post creator. Given a topic, generate 3-5 multiple-choice 
        # questions that help understand: the content angle, the target audience, 
        # and the carousel format. The format question MUST always be included with
        # id='format' and options A/B/C. Return valid JSON only."
        # Use extended thinking for question quality
        # Parse JSON, validate format question present, raise ValueError on bad JSON
        ...
```

System prompt rules for the thinking model:
- Always include format question with `id="format"`, values A/B/C
- 3–5 questions total; model decides based on topic complexity
- All questions single-select multiple choice — no free-text
- Include a `default` for each question (model recommends based on topic)

#### 1.3 — `POST /api/v2/clarify` endpoint
**File:** `src/api/routes_v2.py`

Add after the existing singletons (line 36–39):
```python
_topic_clarifier = TopicClarifierAgent()
```

New Pydantic model:
```python
class ClarifyRequest(BaseModel):
    topic: str
```

New endpoint (synchronous — returns questions directly, no background task):
```python
@router.post("/clarify")
async def clarify_topic(body: ClarifyRequest):
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be empty")
    try:
        result = await _topic_clarifier.run(topic)
        return {"questions": [asdict(q) for q in result.questions]}
    except Exception:
        # Return format B defaults on any failure — never block the user
        return {"questions": _default_clarifier_questions()}
```

`_default_clarifier_questions()` returns a hardcoded list with format question only (Format B default). This is the failure fallback.

#### 1.4 — Update `ResearchRequest`
**File:** `src/api/routes_v2.py` line 46

```python
class ResearchRequest(BaseModel):
    topic: str
    content_type: Literal["news", "educational"] = "news"
    carousel_format: Optional[str] = None            # "A" | "B" | "C" — from clarifier
    clarifier_answers: Optional[dict[str, str]] = None  # {question_id: option_value}
```

---

### Phase 2 — Research Orchestrator: Format-Aware Synthesis

#### 2.1 — Update `run_educational()` signature
**File:** `src/agents/research_orchestrator/orchestrator.py` line 194

```python
async def run_educational(
    self,
    topic: str,
    carousel_format: Optional[str] = None,
    clarifier_answers: Optional[dict] = None,
) -> list[Story]:
```

After line 252 where `story.content_type = "educational"` is set, add:
```python
story.carousel_format = carousel_format or "B"
```

#### 2.2 — Format-aware `_synthesise_educational()`
**File:** `src/agents/research_orchestrator/orchestrator.py` line 257

Add `carousel_format` and `clarifier_answers` params to `_synthesise_educational()`.

Build a `format_instruction` string injected into the synthesis prompt:

```python
FORMAT_INSTRUCTIONS = {
    "A": """Format: MISTAKES → RIGHT WAY
Each key_stat must follow this exact format:
"MISTAKE: [the wrong thing people do — concise, 1 line]\\nFIX: [the correct approach — concise, 1 line]"
Generate 6-8 mistake/fix pairs. These are the common errors people make with this topic.
hook_stat_value: leave empty. hook_stat_label: leave empty.
image_query: target the tool logo or interface screenshot.""",

    "B": """Format: CORE CONCEPTS / PILLARS
Each key_stat must follow this exact format:
"[Concept Name — 2-4 words]\\n[2-sentence explanation of this principle]"
Generate 5-7 concepts that form the essential mental model for this topic.
hook_stat_value: the total concept count (e.g. "5"). hook_stat_label: "KEY PRINCIPLES TO MASTER".
image_query: target the tool logo or interface screenshot.""",

    "C": """Format: CHEAT SHEET
Each key_stat is a single short tip, max 80 characters. No newlines. No prefixes.
Example: "Use @agent to route tasks to specific sub-agents"
Generate 9-12 tips. These are the best shortcuts, tricks, and rules for this topic.
hook_stat_value: leave empty. hook_stat_label: leave empty.
image_query: target the tool logo or interface screenshot.""",
}
```

If `clarifier_answers` is present, also inject the angle + audience answers into the synthesis prompt:
```python
angle_instruction = ""
if clarifier_answers:
    angle = clarifier_answers.get("angle", "")
    audience = clarifier_answers.get("audience", "")
    if angle:
        angle_instruction += f"\nContent angle: focus on '{angle}'"
    if audience:
        angle_instruction += f"\nTarget audience: '{audience}'"
```

#### 2.3 — Thread through `_run_research_pipeline()`
**File:** `src/api/routes_v2.py` line 338

Pass `carousel_format` and `clarifier_answers` from `body` into `_run_research_pipeline()`, then into `run_educational()`.

---

### Phase 3 — Carousel Renderer: Three Format Layouts

#### 3.1 — New slide functions
**File:** `src/utils/carousel_renderer.py`

**Format A — `_slide_mistake(stat, index, total)`**
- Parse `stat` on `\n` → `mistake_line` (starts with `"MISTAKE: "`) + `fix_line` (starts with `"FIX: "`)
- Strip prefixes before rendering
- Layout: 1080×1350px, #1A1A2E bg
  - Top: "MISTAKE #N" accent pill (small, top-left, ~y=120)
  - Middle: mistake text in white Anton, large, word-wrapped (~y=400)
  - Divider: thin accent line (~y=750)
  - Bottom: "✓ " in accent + fix text in white Inter (~y=800)
  - Brand + counter as usual

**Format B — `_slide_pillar(stat, index, total)`**
- Parse `stat` on first `\n` → `concept_name` + `explanation`
- Layout:
  - Top: "PRINCIPLE #N" accent pill
  - Middle: `concept_name` in large Anton white
  - Below: `explanation` in Inter gray, 2-line max
  - Brand + counter

**Format C — `_slide_cheat_batch(stats_batch, slide_index, total)`**
- Receives a batch of 3 tips (no `\n` parsing needed)
- Layout: denser — 3 numbered tips stacked, each with accent number + white tip text
- No dividers between tips; consistent spacing
- Fix the current 4-tip alignment issues (correct y-spacing per tip)

**Format A + B Slide 2 — `_slide_format_a_hook(total)`**
- Accent bg (#8075FF)
- Large white Anton text: the hook claim (hardcoded per-format, not from data — this is a static intro card)
- Text: `"MOST PEOPLE\nDO IT\nWRONG."` (Anton, ~180pt, centered)
- Smaller white Inter below: `"Here's what actually works."`
- Brand + counter

**Format B Slide 2 — `_slide_pillar_intro(hook_stat_value, hook_stat_label, total)`**
- Same as existing `_slide_hook_stat()` — reuse it directly. The synthesis prompt for Format B sets `hook_stat_value` = concept count and `hook_stat_label` = "KEY PRINCIPLES TO MASTER".
- No new function needed for Format B Slide 2.

**Format C Slide 2 — `_slide_cheat_intro(total)`**
- Accent bg
- Large white Anton: `"CHEAT\nSHEET"`
- Smaller white Inter: `"Save this — you'll use it"`
- Brand + counter

**Format C CTA — `_slide_cta_save(total)`**
- Same layout as `_slide_cta()` but text: `"SAVE THIS\nCHEAT SHEET"` (top line) + `"@TECHWITHHAREEN"` (accent, bottom)

#### 3.2 — Update `render_carousel()` signature and branching
**File:** `src/utils/carousel_renderer.py` line 605

New signature:
```python
def render_carousel(
    headline, stats, image_bytes, hook_stat_value, hook_stat_label,
    output_dir, source_url,
    content_type="news",
    carousel_format=None,     # NEW
) -> list[str]:
```

Branching logic at line 651 (Slide 2 + content slides + CTA):

```python
if content_type == "educational":
    if carousel_format == "A":
        slide_2 = _slide_format_a_hook(total)
        content_slides = [_slide_mistake(s, i, total) for i, s in enumerate(stats, 1)]
        cta_slide = _slide_cta(total)          # SEND THIS TO SOMEONE
        include_bookmark = True
    elif carousel_format == "C":
        slide_2 = _slide_cheat_intro(total)
        batches = [stats[i:i+3] for i in range(0, len(stats), 3)]
        content_slides = [_slide_cheat_batch(b, i, total) for i, b in enumerate(batches, 1)]
        cta_slide = _slide_cta_save(total)    # SAVE THIS CHEAT SHEET
        include_bookmark = False               # No BOOKMARK THIS for cheat sheets
    else:  # Format B or None (legacy step-by-step)
        slide_2 = _slide_hook_stat(hook_stat_value, hook_stat_label, total)
        content_slides = [_slide_pillar(s, i, total) for i, s in enumerate(stats, 1)]
        cta_slide = _slide_cta(total)
        include_bookmark = True
else:
    # news path — unchanged
    ...
```

Note: Format A uses 1 stat per slide, Format B uses 1 stat per slide, Format C uses 3 stats per slide. Total slide count changes accordingly — the `total` counter must be computed per format before rendering.

#### 3.3 — Fix alignment issues on content slides
While editing `carousel_renderer.py`, fix:
- `_slide_content()`: y-position drift when stat text wraps to 3+ lines — recalculate `y_cursor` after each item using actual rendered line height, not a fixed offset
- Ensure brand name and counter are consistently placed across all slide types

#### 3.4 — Thread `carousel_format` through `carousel_service.py`
**File:** `src/utils/carousel_service.py` line 102

```python
async def create_carousel(
    headline, key_stats, image_url,
    hook_stat_value, hook_stat_label, source_url,
    content_type="news",
    carousel_format=None,    # NEW
) -> CarouselResult:
```

Pass `carousel_format` to `render_carousel()` at line 136.

---

### Phase 4 — Firestore + Re-Render Safety

#### 4.1 — `create_post()` stores `carousel_format`
**File:** `src/utils/firestore_client.py`

Add `carousel_format: Optional[str] = None` to `create_post()`. Store it in the Firestore document.

Also store `carousel_format` in `render_data` dict so the re-render endpoint can recover it:
```python
"render_data": {
    ...existing fields...,
    "carousel_format": carousel_format,
}
```

#### 4.2 — Re-render reads `carousel_format` from `render_data`
**File:** `src/api/routes_v2.py` — `PATCH /api/v2/posts/{post_id}/slides`

When calling `create_carousel()`, extract from `render_data`:
```python
carousel_format = render_data.get("carousel_format")
```

Pass it to `create_carousel()`. Legacy posts where `render_data` has no `carousel_format` key get `None` → falls back to existing step-by-step educational behavior. No regression.

#### 4.3 — Thread `carousel_format` through `_run_educational_story()`
**File:** `src/api/routes_v2.py` line 287

```python
async def _run_educational_story(story, job_id, post_id, carousel_format=None):
```

Pass `carousel_format=story.carousel_format` to `create_carousel()` and to `create_post()`.

---

### Phase 5 — PostAnalyzer: Format-Aware CTA Check

#### 5.1 — Pass `carousel_format` to analyzer
**File:** `src/agents/post_analyzer/agent.py`

Locate the CTA check (searches for "SEND THIS TO SOMEONE" on last slide). Update:
```python
valid_cta = "SEND THIS TO SOMEONE"
if getattr(story, "carousel_format", None) == "C":
    valid_cta = "SAVE THIS CHEAT SHEET"

if valid_cta.lower() not in last_slide_text.lower():
    checks["cta_present"] = False
```

No signature change needed — agent already receives `story` object.

---

### Phase 6 — Web UI

#### 6.1 — `api.ts`: new function + type update
**File:** `/Users/hareenedla/Hareen/techwithhareen-web/src/lib/api.ts`

Add to `Post` interface (line 75):
```typescript
carousel_format?: string;
```

New `ClarifierQuestion` type and `clarifyTopic()` function:
```typescript
export interface ClarifierOption {
  value: string;
  label: string;
}

export interface ClarifierQuestion {
  id: string;
  text: string;
  options: ClarifierOption[];
  default: string;
}

export async function clarifyTopic(topic: string): Promise<ClarifierQuestion[]> {
  const res = await fetch(`${API_URL}/api/v2/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
    signal: AbortSignal.timeout(6000),  // 6s timeout — fallback on failure
  });
  if (!res.ok) throw new Error("clarify failed");
  const data = await res.json();
  return data.questions;
}
```

Update `startResearch()` to accept `carousel_format`:
```typescript
export async function startResearch(
  topic: string,
  contentType: string,
  carouselFormat?: string,
  clarifierAnswers?: Record<string, string>,
): Promise<string>
```

#### 6.2 — New `ClarifierStep` component
**New file:** `/Users/hareenedla/Hareen/techwithhareen-web/src/components/ClarifierStep.tsx`

Props:
```typescript
interface Props {
  questions: ClarifierQuestion[];
  onSubmit: (answers: Record<string, string>) => void;
  onSkip: () => void;
}
```

Renders each question as a pill-selector group (same pill style as the News/Educational toggle in `NewPost.tsx`). "Generate" button enabled only when all questions have a selection. "Skip →" link below — uses all `question.default` values as answers.

Loading state: shown while waiting for `/api/v2/clarify` response. If clarify call fails, component skips itself by calling `onSkip()` silently.

#### 6.3 — Update `NewPost.tsx`
**File:** `/Users/hareenedla/Hareen/techwithhareen-web/src/pages/NewPost.tsx`

Add `"clarifying"` to phase type (line 6).

Update `handleSubmit()` (line 64):
- For `contentType === "educational"`: call `clarifyTopic(topic)` → on success, set `phase = "clarifying"` + store questions in state → ClarifierStep shown
- On `clarifyTopic` failure: skip directly to `handleLaunchResearch({})` with defaults

New `handleLaunchResearch(answers: Record<string, string>)`:
- Extracts `carousel_format` from `answers.format` (or `"B"` if absent)
- Calls `startResearch(topic, contentType, carousel_format, answers)`
- Sets phase to normal research polling

Between topic form and pipeline status display, render conditionally:
```tsx
{phase === "clarifying" && (
  <ClarifierStep
    questions={clarifierQuestions}
    onSubmit={handleLaunchResearch}
    onSkip={() => handleLaunchResearch({})}
  />
)}
```

#### 6.4 — `PostCard.tsx`: format badge
**File:** `/Users/hareenedla/Hareen/techwithhareen-web/src/components/PostCard.tsx`

After the `dm_keyword` badge (line 88):
```tsx
{post.carousel_format && (
  <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">
    {post.carousel_format === "A" ? "Mistakes" : post.carousel_format === "B" ? "Pillars" : "Cheat Sheet"}
  </span>
)}
```

For legacy posts where `carousel_format` is absent: badge is hidden. No error.

---

## Acceptance Criteria

### TopicClarifierAgent
- [ ] Given any topic, generates 3–5 questions with multiple-choice options
- [ ] Always includes a question with `id="format"` and options A/B/C
- [ ] Returns valid JSON — malformed LLM output raises `ValueError` internally
- [ ] On any failure, `POST /api/v2/clarify` returns format-B defaults (never 500s to the browser)
- [ ] Response time: <8s on average (thinking model latency acceptable for this step)

### Format-specific content
- [ ] Format A: `key_stats` items all follow `"MISTAKE: [text]\nFIX: [text]"` structure
- [ ] Format B: `key_stats` items all follow `"[Concept Name]\n[explanation]"` structure
- [ ] Format C: `key_stats` items are all single-line tips, ≤80 chars
- [ ] Research synthesis respects `clarifier_answers` angle + audience when provided

### Carousel renderer
- [ ] Format A: each content slide shows mistake + fix (2-field layout, 1 mistake per slide)
- [ ] Format B: each content slide shows concept name + explanation (2-field layout, 1 concept per slide)
- [ ] Format C: each content slide shows 3 tips (dense layout)
- [ ] Format A Slide 2: accent bg, bold hook claim (no redundant list)
- [ ] Format B Slide 2: concept count as hook stat number
- [ ] Format C Slide 2: "CHEAT SHEET" on accent bg
- [ ] Format C: no BOOKMARK THIS mid-slide; uses SAVE THIS CHEAT SHEET CTA
- [ ] Format A + B: BOOKMARK THIS + SEND THIS TO SOMEONE unchanged
- [ ] Legacy posts (`carousel_format=None`): existing educational step-by-step behavior unchanged
- [ ] Content slide alignment: no y-position drift on text wrap

### Data integrity
- [ ] `carousel_format` stored in Firestore post document
- [ ] `carousel_format` stored in `render_data`
- [ ] Re-render from approval queue preserves original `carousel_format`
- [ ] Legacy posts with no `carousel_format` in `render_data` re-render without error

### PostAnalyzer
- [ ] Format C: "SAVE THIS CHEAT SHEET" passes CTA check
- [ ] Format A + B: "SEND THIS TO SOMEONE" still required

### Web UI
- [ ] Educational flow shows clarifier questions step before Generate fires
- [ ] Skip option uses format B + all question defaults
- [ ] Clarifier failure: UI silently skips to Generate with "Using default format" note
- [ ] PostCard shows format badge for posts with `carousel_format` set
- [ ] Legacy posts (no `carousel_format`): badge is hidden, no error

---

## Files Changed

### Backend (`/Users/hareenedla/Hareen/insta`)

| File | Change |
|---|---|
| `src/utils/story.py` | Add `carousel_format: Optional[str] = None` + `to_dict()` |
| `src/agents/topic_clarifier/__init__.py` | New (empty) |
| `src/agents/topic_clarifier/agent.py` | New — `TopicClarifierAgent` + `ClarifierResult` + `ClarifierQuestion` |
| `src/api/routes_v2.py` | `ResearchRequest` + `carousel_format`, `ClarifyRequest`, `POST /api/v2/clarify`, thread `carousel_format` through pipeline + re-render |
| `src/agents/research_orchestrator/orchestrator.py` | `run_educational(carousel_format, clarifier_answers)`, `_synthesise_educational()` format-aware prompt |
| `src/utils/carousel_renderer.py` | 5 new slide functions, updated `render_carousel()`, alignment fix |
| `src/utils/carousel_service.py` | Thread `carousel_format` through `create_carousel()` |
| `src/utils/firestore_client.py` | `create_post()` + `render_data` store `carousel_format` |
| `src/agents/post_analyzer/agent.py` | Format-aware CTA check |

### Frontend (`/Users/hareenedla/Hareen/techwithhareen-web`)

| File | Change |
|---|---|
| `src/lib/api.ts` | `carousel_format?` on `Post`, `clarifyTopic()`, update `startResearch()` |
| `src/components/ClarifierStep.tsx` | New component — renders questions + Skip |
| `src/pages/NewPost.tsx` | `"clarifying"` phase, `handleLaunchResearch()`, render `ClarifierStep` |
| `src/components/PostCard.tsx` | Format badge |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Thinking model generates invalid JSON | Low | Medium | `_generate_questions()` validates JSON, raises `ValueError`, fallback returns defaults |
| Format A key_stats contain no `MISTAKE:` prefix | Medium | Medium | Renderer falls back to plain 2-line split if prefix not found |
| Alignment fix breaks existing news/educational slides | Low | High | Test with existing posts before shipping. Add regression test fixtures. |
| Re-render loses `carousel_format` on legacy posts | Low | Medium | `render_data.get("carousel_format")` returns `None` safely — fallback is existing behavior |
| Thinking model call is too slow (>10s) | Medium | Low | 6s timeout in frontend — silently falls back to Skip. User still generates post. |

---

## Out of Scope

- Format D (Before/After split layout) — deferred
- ManyChat automation — still manual DM delivery
- Observability logging for clarifier answers — add in Phase 2B if needed
- v1 (Gmail newsletter) educational support — v1 is news-only by design
