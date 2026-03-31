---
date: 2026-03-31
topic: educational-carousel-redesign
---

# Educational Carousel Redesign — Topic Clarifier + Multi-Format

## What We're Building

Two things that solve the same root problem: educational posts currently produce generic, wrong-angle content because the pipeline has no clarification step and only one fixed format.

**1. Topic Clarifier Agent** — a thinking model that runs *before* research starts. Given a topic, it generates 3–5 dynamic multiple-choice questions tailored to that specific topic. Hareen answers them in the Web UI, then research fires with full context.

**2. Four carousel formats** — the pipeline and renderer support 4 distinct educational layouts. Format is always one of the clarifier questions.

---

## Problems Being Solved

| Problem | Root Cause | Fix |
|---|---|---|
| Wrong content angle ("how to use Manus AI" → marketing steps) | Research has no angle context | Clarifier questions capture angle before research |
| Slide 2 redundancy (headings in Slide 2 = headings in Slide 3) | "WHAT YOU'LL LEARN" preview mirrors content slides | Format-specific Slide 2 designs, no redundant preview |
| Step-by-step format doesn't fit all topics | Single hardcoded format | 4 formats — user picks per post |
| Layout/alignment issues on content slides | Existing renderer bugs | Fix as part of format redesign |

---

## Topic Clarifier Agent

### How it works

1. Hareen types topic + selects "Educational" in Web UI
2. Web UI calls `POST /api/v2/clarify` with the topic
3. **TopicClarifierAgent** (thinking model — `claude-opus-4` or `claude-sonnet-4-6` with extended thinking) analyzes the topic and returns 3–5 questions with 3–4 options each
4. Web UI renders questions as a **step before "Generate"** — Hareen selects options
5. Hareen hits "Generate" — answers posted along with topic to `/api/v2/research`
6. Research pipeline uses answers to shape queries + content

### Format question is always included

The clarifier always includes the format question as one of its questions. It may suggest a default based on the topic, but Hareen overrides.

### Question structure (returned by agent)

```json
{
  "questions": [
    {
      "id": "angle",
      "question": "What aspect of Manus AI are you focusing on?",
      "options": [
        {"id": "a", "label": "First-time setup & getting started"},
        {"id": "b", "label": "Advanced workflows & automation"},
        {"id": "c", "label": "Common mistakes most people make"},
        {"id": "d", "label": "Manus vs. other AI agents"}
      ]
    },
    {
      "id": "audience",
      "question": "Who is this post for?",
      "options": [
        {"id": "a", "label": "People who've never heard of Manus"},
        {"id": "b", "label": "People who tried it but feel lost"},
        {"id": "c", "label": "Power users who want to get more out of it"}
      ]
    },
    {
      "id": "format",
      "question": "Which format fits this topic?",
      "options": [
        {"id": "A", "label": "Mistakes → Right Way — what most people get wrong + the fix"},
        {"id": "B", "label": "Core Concepts / Pillars — 3–5 key ideas, each slide standalone"},
        {"id": "C", "label": "Cheat Sheet — dense tips/shortcuts, high save rate"},
        {"id": "D", "label": "Before / After — beginner approach vs. expert approach"}
      ]
    }
  ]
}
```

---

## Four Carousel Formats

### Format A — Mistakes → Right Way

**Best for:** "How to use X the right way", "Stop doing X", "X mistakes"

**Slide structure:**
- Slide 1: Cover — "X MISTAKES WITH [TOPIC]" or "YOU'RE USING [TOOL] WRONG"
- Slide 2: Hook stat or bold claim — standalone, no preview list
- Slides 3+: Each slide = 1 mistake. Format per slide:
  - Top: "MISTAKE #N" label (accent)
  - Middle: The wrong thing people do (white, concise)
  - Bottom: "✓ INSTEAD:" + the fix (accent)
- Second-to-last: Link in description
- Last: SEND THIS TO SOMEONE CTA

### Format B — Core Concepts / Pillars

**Best for:** "Understanding X", "X explained", "principles of X"

**Slide structure:**
- Slide 1: Cover — "THE [N] PRINCIPLES OF [TOPIC]"
- Slide 2: Why these principles matter — a single bold statement (no list preview)
- Slides 3+: Each slide = 1 principle. Format per slide:
  - Top: "PRINCIPLE #N" label (accent)
  - Middle: Principle name in large type
  - Bottom: 2-line explanation
- Second-to-last: Link in description
- Last: SEND THIS TO SOMEONE CTA

### Format C — Cheat Sheet

**Best for:** "Tips for X", "shortcuts for X", "X hacks"

**Slide structure:**
- Slide 1: Cover — "[TOPIC] CHEAT SHEET" or "[N] TIPS FOR [TOPIC]"
- Slide 2: Single most impactful tip (large, standalone — earns the save)
- Slides 3+: 2–3 tips per slide (denser layout — this is the cheat sheet feel)
  - Each tip: accent number + tip text
- Second-to-last: Link in description
- Last: SAVE THIS POST (primary CTA for cheat sheets, not send)

### Format D — Before / After *(deferred — not in this build)*

Requires two-column split layout in renderer. Deferred to next feature iteration.

---

## Pipeline Changes

### New: TopicClarifierAgent
- File: `src/agents/topic_clarifier/agent.py`
- Model: thinking model (claude-opus-4 or claude-sonnet-4-6 extended thinking)
- Input: topic string
- Output: list of 3–5 questions with options
- New API: `POST /api/v2/clarify` → returns questions JSON

### Modified: ResearchRequest
- Add `clarifier_answers: dict[str, str]` — the question_id → option_id map
- Passed into research pipeline as context for synthesis prompt

### Modified: ResearchOrchestrator
- `run_educational()` uses `clarifier_answers` to tune search queries and synthesis prompt
- Angle + audience answers shape what the LLM looks for
- Format answer passed downstream

### Modified: Story
- Add `carousel_format: Literal["A", "B", "C", "D"] = "B"` — set from clarifier answers

### Modified: carousel_renderer.py
- 4 format-specific render paths
- Fix alignment issues in content slides

### Modified: Web UI (techwithhareen-web)
- New clarifier step between topic input and Generate button
- Renders questions + options dynamically from API response
- "Generate" disabled until all questions answered

---

## What We're NOT Building Now

- **Format D (Before/After)** — deferred to next feature. Requires a two-column split layout in the renderer which is a significant new pattern. Build A, B, C first.
- Auto-format suggestion (clarifier always asks, never decides silently)
- ManyChat automation (still manual DM delivery)

---

## Decisions

- **Clarifier step is skippable** — Hareen can hit "Skip" to bypass questions and use defaults. Defaults: Format B (Core Concepts), audience = general, angle = broad overview.
- **Formats in scope: A, B, C only** — D added when renderer split-layout pattern is proven.

## Next Steps

→ `/compound-engineering:workflows:plan` to create implementation plan
