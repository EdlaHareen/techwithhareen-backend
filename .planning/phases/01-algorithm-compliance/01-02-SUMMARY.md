---
phase: 01-algorithm-compliance
plan: "02"
subsystem: caption-writer, post-analyzer
tags: [algorithm-compliance, hashtags, caption, instagram-dec-2025]
dependency_graph:
  requires: []
  provides: [ALGO-01, ALGO-05, ALGO-06]
  affects: [caption_writer/agent.py, post_analyzer/agent.py]
tech_stack:
  added: []
  patterns: [validation-at-generation-and-gate]
key_files:
  modified:
    - src/agents/caption_writer/agent.py
    - src/agents/post_analyzer/agent.py
decisions:
  - "Removed niche-hashtag-by-character-length heuristic (len > 9) — unreliable with only 3-5 total tags; LLM prompt handles niche selection at generation time"
  - "DM-share CTA is primary for news/tool stories; save CTA reserved for research/general_news where bookmark value is higher"
  - "_FALLBACK_HASHTAGS replaces BASE_HASHTAGS — 3 tags vs 7, respects the new cap"
metrics:
  duration: "147s"
  completed: "2026-03-26T03:09:12Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 1 Plan 02: Caption Compliance and Post Analyzer Threshold Update Summary

Instagram Dec 2025 algorithm compliance: enforced 3-5 hashtag cap and 120-char hook constraint in both the caption generation layer and the post analyzer quality gate, with DM-share as the primary CTA for news and tool stories.

## What Was Built

### Task 1 — Caption Writer Updates (`src/agents/caption_writer/agent.py`)

- **Module docstring** updated to reflect new CTA strategy and 3-5 hashtag cap.
- **`_FALLBACK_HASHTAGS`** replaces `BASE_HASHTAGS`: 3 tags (`#techwithhareen`, `#AI`, `#Tech`) — within the new cap.
- **LLM prompt** (hashtag block): replaced 15-20 tag instructions with "exactly 3-5" rule, named Instagram Dec 2025 as the reason.
- **LLM prompt** (JSON schema — hashtags field): updated example to show 3 tags.
- **LLM prompt** (JSON schema — cta field): DM-share (`Send this to someone who needs to see it 👇`) is now the primary CTA for news/tool stories; save CTA is secondary for research/general_news.
- **LLM prompt** (JSON schema — hook field): added 120-char constraint with explanation of Instagram's 125-char feed preview truncation.
- **`Caption.is_valid()`**: hashtag validation changed from `< 10` to `< 3 or > 5`. Hook length check added: rejects hooks over 120 characters.

### Task 2 — Post Analyzer Updates (`src/agents/post_analyzer/agent.py`)

- **Module docstring** (`HashtagCheck` line): updated to "3-5 hashtags (Instagram Dec 2025 cap: 15-20 suppresses reach)".
- **`_check_hashtags()`**: replaced `count < 10` check with `count < 3` (min) and `count > 5` (max). Removed the niche-by-length heuristic (`len(h) > 9`) entirely.
- **`_check_hook()`**: added `len > 120` check with a concrete fix instruction.
- **`_check_cta()`**: fix suggestion now references DM-share CTA as primary.

## Verification Results

All checks passed in two test runs:

1. `Caption.is_valid()` correctly rejects 2-tag and 6-tag captions, accepts 3-tag captions, and rejects 121-char hooks.
2. `PostAnalyzerAgent._check_hashtags()` raises issues for both under-3 and over-5 counts.
3. `PostAnalyzerAgent._check_hook()` raises a 120-char issue for a 121-char hook.
4. `_FALLBACK_HASHTAGS` has exactly 3 entries, includes `#techwithhareen`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's verification snippet used wrong dataclass signatures**

- **Found during:** Task 2 verification
- **Issue:** The plan's automated verify block called `Story(... key_stats=[])` without the required `url` positional argument, and `CarouselResult(success=True, slide_urls=[])` with a non-existent `slide_urls` field.
- **Fix:** Corrected test invocations to `Story(headline=..., summary=..., url=None, key_stats=[])` and `CarouselResult(design_id='test', slide_count=6, success=True)`. Also mocked the `PostAnalyzerAgent._client` to avoid needing a live `ANTHROPIC_API_KEY` in the local environment. No production code was changed.
- **Files modified:** None (test invocation only, run inline)
- **Commit:** N/A (inline fix — no separate commit needed)

## Self-Check: PASSED

- `src/agents/caption_writer/agent.py` — FOUND
- `src/agents/post_analyzer/agent.py` — FOUND
- `.planning/phases/01-algorithm-compliance/01-02-SUMMARY.md` — FOUND
- Commit `ba174bc` (caption writer) — FOUND
- Commit `7a57124` (post analyzer) — FOUND
