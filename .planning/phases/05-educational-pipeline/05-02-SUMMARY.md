---
phase: 05-educational-pipeline
plan: 02
subsystem: api
tags: [anthropic, pillow, carousel, research-orchestrator, educational, content-type]

# Dependency graph
requires:
  - phase: 05-01
    provides: content_type field on Story and ResearchRequest; educational branch skeleton in _run_research_pipeline
provides:
  - ResearchOrchestrator.run_educational() — full parallel research + educational Claude synthesis returning 1 Story
  - ResearchOrchestrator._synthesise_educational() — Claude haiku prompt producing 5-7 STEP N: VERB\nExplanation key_stats
  - carousel_renderer._slide_learn_preview() — accent-bg WHAT YOU'LL LEARN Slide 2 for educational carousels
  - render_carousel(content_type=) — routes Slide 2 to learn preview or hook stat based on content_type
  - create_carousel(content_type=) — threads content_type through to render_carousel
affects: [05-03, 05-04, post_creator, routes_v2]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Educational synthesis: separate _synthesise_educational() method with distinct Claude prompt — step-by-step guide format instead of news angles"
    - "content_type routing in render_carousel: conditional Slide 2 builder based on content_type param — default 'news' ensures backward compatibility"
    - "Service layer threading: service functions accept and forward content_type with matching default so all existing callers remain unmodified"

key-files:
  created: []
  modified:
    - src/agents/research_orchestrator/orchestrator.py
    - src/utils/carousel_renderer.py
    - src/utils/carousel_service.py

key-decisions:
  - "run_educational() sets story.content_type='educational' after synthesis rather than inside _synthesise_educational — keeps synthesis pure and makes the flag explicit at the public entry point"
  - "_slide_learn_preview uses stats[:4] (first 4 steps from key_stats) for the preview bullets — consistent with the 4-per-slide content slide limit"
  - "content_type param added after source_url in both render_carousel and create_carousel — preserves existing positional call sites"
  - "hook_stat_value and hook_stat_label forced to empty strings in _synthesise_educational prompt and Story constructor — educational stories never use the hook stat slide"

patterns-established:
  - "Educational synthesis prompt pattern: returns single Story JSON (not array), STEP N: VERB\nExplanation format, image_query targets tool UI not news thumbnails"
  - "Accent-bg slide pattern: _slide_learn_preview and _slide_bookmark both use full ACCENT bg — visually distinct from dark navy BG slides"

requirements-completed: [EDU-02, EDU-03]

# Metrics
duration: 6min
completed: 2026-03-31
---

# Phase 5 Plan 02: Educational Synthesis + Slide 2 Builder Summary

**ResearchOrchestrator.run_educational() with step-format Claude synthesis and _slide_learn_preview() accent-bg WHAT YOU'LL LEARN Slide 2, with content_type threaded through carousel_service**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-31T00:00:00Z
- **Completed:** 2026-03-31T00:06:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ResearchOrchestrator gains run_educational() — runs Exa+Tavily+Serper parallel research then calls _synthesise_educational() which prompts Claude to produce 5-7 lesson steps in STEP N: VERB\nExplanation format with empty hook stat fields
- carousel_renderer gains _slide_learn_preview() — renders 1080x1350 ACCENT-bg slide with "WHAT YOU'LL LEARN" Anton header, white divider line, and up to 4 step bullets; render_carousel() routes Slide 2 based on content_type param
- carousel_service.create_carousel() accepts and threads content_type to render_carousel() — all existing callers unchanged via default "news"

## Task Commits

Each task was committed atomically:

1. **Task 1: Add run_educational() and _synthesise_educational() to ResearchOrchestrator** - `8b62cff` (feat)
2. **Task 2: Add educational Slide 2 builder + thread content_type through carousel_service** - `b09648b` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `src/agents/research_orchestrator/orchestrator.py` - Added run_educational() public method and _synthesise_educational() private method with step-format Claude prompt (151 lines added)
- `src/utils/carousel_renderer.py` - Added _slide_learn_preview() builder, added content_type param to render_carousel(), conditional Slide 2 routing
- `src/utils/carousel_service.py` - Added content_type param to create_carousel(), passes content_type=content_type to render_carousel()

## Decisions Made
- run_educational() sets story.content_type='educational' at the public entry point rather than inside _synthesise_educational — keeps synthesis a pure data transformation
- _slide_learn_preview uses stats[:4] (first 4 key_stats items) for bullets — consistent with 4-per-slide content limit throughout the renderer
- content_type param added after source_url in both functions — no positional call site breakage
- hook_stat_value and hook_stat_label forced to "" in the synthesis prompt and Story constructor — educational stories never render the hook stat slide

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 05-01 foundation + Plan 05-02 synthesis/rendering complete — educational pipeline has full research-to-carousel capability
- Plan 05-03 (PDF Guide Agent) and Plan 05-04 (routes_v2 educational endpoint) can proceed — they depend on run_educational() and create_carousel(content_type=) which are now live
- No blockers

## Self-Check: PASSED

- All 3 modified source files exist on disk
- SUMMARY.md created at .planning/phases/05-educational-pipeline/05-02-SUMMARY.md
- Task commit 8b62cff (run_educational + _synthesise_educational) — FOUND
- Task commit b09648b (_slide_learn_preview + content_type threading) — FOUND

---
*Phase: 05-educational-pipeline*
*Completed: 2026-03-31*
