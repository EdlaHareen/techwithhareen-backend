# Milestones

## v3.0 — Content Voice + Slide Editor (Complete)
**Completed:** 2026-03-25
**Phases:** 1–3

### What shipped
- Phase 1: Source Link CTA + SSRF protection + AsyncAnthropic migration + font cache
- Phase 2: Personal Touch Captions — Hareen's voice, 4 story types (tool_feature / funding_acquisition / research_finding / general_news)
- Phase 3: Carousel Slide Editor — edit/reorder/delete slides in web UI + PATCH/DELETE/reorder API endpoints
- Fix: Read More slide shows "LINK IN DESCRIPTION" — no URL on slide (URL in caption only)

### What was validated
- Hareen's voice captions (4 story types) — significantly better than generic LLM output
- Slide editor — eliminates the need to re-generate full carousels for minor slide changes
- SSRF protection — Serper image URLs validated before download

---

## v2.0 — Web UI Research Pipeline (Complete)
**Completed:** 2026-03-15

### What shipped
- Web UI (React 19 + Vite + Tailwind v4 on Vercel)
- Research Orchestrator: Exa + Tavily + Serper parallel agents → LLM synthesis → Story objects
- Content Validator: relevance, freshness, dedup
- Firestore /jobs and /posts collections
- Web UI approval queue (approve/reject/edit caption/edit slides)

---

## v1.0 — Gmail Newsletter Pipeline (Complete)
**Completed:** 2026-02-01

### What shipped
- Gmail Pub/Sub trigger (rundownai newsletter)
- Content Fetcher: HTML parse → Story objects
- Post Creator: Serper image search + Pillow PNG renderer (UncoverAI design)
- Caption Writer: initial caption agent
- Post Analyzer: 5-check quality gate + 1 auto-retry
- Telegram Bot: aiogram 3.x, approve/reject
- GCS upload + public URLs
- Cloud Run deployment + Cloud Build CI/CD
