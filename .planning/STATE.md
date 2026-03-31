# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** Every approved post sounds like Hareen — opinionated, direct, signal-not-noise — with zero extra effort beyond the approval click.
**Current focus:** Phase 5 — Educational Pipeline

## Current Position

Phase: 5 of 5 (Educational Pipeline)
Plan: 1 of 4 complete in current phase
Status: In progress
Last activity: 2026-03-31 — Plan 05-01 complete: content_type added to Story dataclass, ResearchRequest, educational branch skeleton in _run_research_pipeline, create_post extended with pdf_url/dm_keyword/content_type

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: ~75 sec
- Total execution time: ~5.5 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-algorithm-compliance | 2 | ~5.5 min | ~2.75 min |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Recent decisions affecting v4 work (full log in PROJECT.md):

- Classifier: 3 types only (news_and_announcements / tool_and_product / educational) — 5-type system had misclassification edge cases
- Reels Script: on-demand per post, not auto-generated — ties generation to recording intent
- Stories: teaser card only for v4 — poll/insight cards deferred to v5 (need 5K+ community)
- Hashtags: cap at 3–5 (Instagram Dec 2025 algorithm; 15–20 delivered negligible extra reach)
- v1–v3 all shipped and live, no regressions
- [01-01] BG constant (26,26,46) replaces BLACK — sole remaining black draw call uses literal (0,0,0) for text-on-accent contrast
- [01-01] Bookmark threshold set to len(stat_chunks) >= 2 — maps cleanly to 8+ slide carousels
- [01-01] Slide numbering uses len(slides)+1 dynamically — eliminates off-by-one when bookmark is conditionally injected
- [01-02] Niche-hashtag-by-character-length heuristic removed — unreliable at 3-5 tags; LLM prompt handles niche selection at generation time
- [01-02] DM-share CTA is primary for news/tool stories; save CTA reserved for research/general_news
- [01-02] _FALLBACK_HASHTAGS (3 tags) replaces BASE_HASHTAGS (7 tags) — within the new cap
- [05-01] Story.content_type uses Optional[str] not Literal — keeps internal model extensible for Phase 2 classifier value expansion
- [05-01] ResearchRequest.content_type uses Literal["news","educational"] — strict API boundary; internal Story stays flexible
- [05-01] create_post stores content_type=None for news posts, "educational" for educational — avoids polluting existing news Firestore docs
- [05-01] Educational branch calls run_educational stub that raises AttributeError until Plan 02 — acceptable; news path unaffected

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-31
Stopped at: Completed 05-educational-pipeline plan 05-01 (content_type data model foundation — Story, ResearchRequest, educational branch skeleton, create_post extended)
Resume file: None
