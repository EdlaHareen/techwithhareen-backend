---
date: 2026-04-01
topic: educational-separate-pipeline
---

# Educational Separate Pipeline

## What We're Building

Decouple the educational carousel pipeline from the news pipeline so they share zero rendering logic. Educational posts have never rendered correctly because they were patched into the news flow at every layer. The fix is a dedicated `educational_renderer.py` and a dedicated background task `_run_educational_pipeline()` — no more `if content_type == "educational"` branches in shared code.

## Why This Approach

Considered two options:
- **A (chosen):** Dedicated renderer file + separate background task — clean separation at the rendering layer, research agents (Exa/Tavily/Serper) stay shared since they already work.
- **B:** Fully separate route + orchestrator — cleaner long-term but more code; overkill when the root issue is the renderer.

## Key Decisions

- **Shared:** Research agents (Exa/Tavily/Serper), Firestore storage, Web UI approval queue, PDFGuideAgent, CaptionWriterAgent
- **Separate (new):** `src/utils/educational_renderer.py` — 3 clean format functions, no legacy fallbacks, no `if content_type` checks
- **Separate (new):** `_run_educational_pipeline()` background task in `routes_v2.py` — replaces the patched `_run_educational_story()` + educational branch in `_run_research_pipeline()`
- **Formats:** A (Mistakes→Right Way), B (Pillars), C (Cheat Sheet) — all 3 supported from day one
- **Clarifier questions:** Keep as-is (already working after timeout fix)
- **carousel_format flows:** clarifier → ResearchRequest → run_educational() → Story → _run_educational_pipeline() → educational_renderer — no sharing with news renderer at any point

## Open Questions

- None — scope is clear

## Next Steps

→ `/workflows:plan` for implementation details
