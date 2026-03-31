---
phase: 05-educational-pipeline
plan: "01"
subsystem: api
tags: [fastapi, firestore, pydantic, story, content_type, educational]

# Dependency graph
requires: []
provides:
  - content_type field on Story dataclass (canonical CLASS-01 resolution)
  - Story.to_dict() serialises content_type to Firestore
  - ResearchRequest.content_type Literal["news","educational"] with default "news"
  - start_research endpoint threads content_type into _run_research_pipeline
  - _run_research_pipeline branches on content_type with educational skeleton
  - create_post() extended with pdf_url, dm_keyword, content_type optional params
affects:
  - 05-02 (PDFGuideAgent — calls run_educational stub)
  - 05-03 (pdf_url/dm_keyword wiring — calls create_post with these params)
  - 05-04 (educational story pipeline — replaces _process_story for educational)
  - phase-02 content classifier (sets Story.content_type, does not add it)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - content_type as Literal on API boundary (ResearchRequest) + Optional[str] on internal Story dataclass
    - Educational branch skeleton pattern — stub method call + hard-cap before real implementation

key-files:
  created: []
  modified:
    - src/utils/story.py
    - src/api/routes_v2.py
    - src/utils/firestore_client.py

key-decisions:
  - "Story.content_type uses Optional[str] (not Literal) so Phase 2 classifier can expand values without breaking merge"
  - "ResearchRequest.content_type uses Literal['news','educational'] — strict API boundary; internal model stays flexible"
  - "Educational branch calls run_educational stub that raises AttributeError until Plan 02 — acceptable, news path unaffected"
  - "create_post stores content_type=None for news posts, content_type='educational' for educational — avoids polluting news docs"

patterns-established:
  - "Boundary Literal / internal Optional pattern: use Literal on Pydantic models (strict input), Optional[str] on dataclasses (extensible internals)"
  - "Wiring stub pattern: add branch + None stubs now, implement in dedicated plan — keeps waves independent"

requirements-completed: [EDU-08, EDU-09, EDU-10, CLASS-01]

# Metrics
duration: 3min
completed: "2026-03-31"
---

# Phase 5 Plan 01: Educational Pipeline Data Model Foundation Summary

**content_type field threaded from API request through Story dataclass, research pipeline branching, and Firestore persistence — educational skeleton wired with ContentValidator skip and 1-story hard-cap**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-31T06:21:00Z
- **Completed:** 2026-03-31T06:23:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `content_type: Optional[str] = None` to Story dataclass with `to_dict()` serialisation — canonical CLASS-01 resolution that unblocks Phase 2 classifier
- Added `content_type: Literal["news", "educational"] = "news"` to `ResearchRequest` and threaded it through `start_research` → `_run_research_pipeline`
- Implemented educational branch skeleton in `_run_research_pipeline`: ContentValidator skipped, hard-capped to `stories[:1]`, `run_educational` stub called, `pdf_url`/`dm_keyword` None stubs wired into `create_post`
- Extended `create_post()` with `pdf_url`, `dm_keyword`, `content_type` optional params stored in Firestore document

## Task Commits

Each task was committed atomically:

1. **Task 1: Add content_type to Story dataclass and ResearchRequest** - `9fa5e9a` (feat)
2. **Task 2: Educational branch skeleton in _run_research_pipeline + extend create_post** - `7303430` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/utils/story.py` — Added `content_type: Optional[str] = None` field and `"content_type": self.content_type` in `to_dict()`
- `src/api/routes_v2.py` — Added `ResearchRequest.content_type`, threaded kwarg to `_run_research_pipeline`, implemented educational branch skeleton with ContentValidator skip and 1-story hard-cap
- `src/utils/firestore_client.py` — Extended `create_post()` with `pdf_url`, `dm_keyword`, `content_type` optional params stored in Firestore doc

## Decisions Made

- `Story.content_type` uses `Optional[str]` not `Literal` — keeps the internal model extensible so Phase 2 classifier can add "news_and_announcements" and "tool_and_product" values without a merge conflict
- `ResearchRequest.content_type` uses `Literal["news", "educational"]` — strict API boundary prevents invalid input from the web UI
- Educational branch calls `_research_orchestrator.run_educational(topic)` stub that will raise `AttributeError` until Plan 02 implements the method — acceptable because the news path is completely unaffected by this branch
- `create_post` stores `content_type='educational'` only for educational posts; `None` for news posts — avoids polluting existing news Firestore documents with a new field

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The Telegram token validation error during verification was a known environment issue (no token set in local test env), not a code defect. Verification was completed via source inspection and direct Story/firestore_client imports which do not trigger the Telegram bot init.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 2 plans (Plan 02 — ResearchOrchestrator educational method, Plan 03 — PDFGuideAgent) can now proceed independently
- Plan 02 needs to add `run_educational(topic)` to `ResearchOrchestrator` to resolve the AttributeError stub
- Plan 03 needs to populate `pdf_url` and `dm_keyword` via `PDFGuideAgent` and update the `create_post` call
- Plan 04 will supersede Step 3 of `_run_research_pipeline` for the educational branch only (replace `_process_story` with `_run_educational_story`)
- Phase 2 content classifier can set `story.content_type` directly — field exists on Story, no schema change needed

---
*Phase: 05-educational-pipeline*
*Completed: 2026-03-31*
