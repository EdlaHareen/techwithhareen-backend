# techwithhareen — v2 Product Requirements Document

**Version:** 2.0
**Date:** 2026-03-14
**Branch:** `feature/v2`
**Status:** Draft

---

## 1. Overview

v1 automates content creation from the daily rundownai newsletter — Gmail triggers a pipeline that builds carousels, writes captions, and sends them to Telegram for approval.

v2 extends the system with a second content entry point: a web UI where the owner types any topic, parallel research agents gather content from Exa, Tavily, and Serper, and the same v1 pipeline produces posts for approval — now in the browser (Telegram stays as an optional delivery channel).

The existing v1 pipeline is **not modified**. v2 wraps around it.

---

## 2. Goals

| Goal | Success Criterion |
|---|---|
| Topic-driven content creation | Owner types a topic → posts are ready for approval within 3 minutes |
| Web-based approval UI | Approve/reject posts in browser, no Telegram required |
| Research quality | At least 3 distinct, accurate source angles per topic |
| Pipeline reuse | Zero changes to existing carousel/caption/analyzer/publisher code |
| Code clarity | New developer reads folder structure → understands system in < 5 minutes |

---

## 3. Non-Goals (v2)

- Multi-user / team accounts (deferred to v3)
- Scheduling / drip publishing (deferred to v3)
- NotebookLM integration (no public API)
- Automated Instagram publishing (manual export stub stays)

---

## 4. Architecture

### 4.1 Entry Points

```
v1 path:  Gmail Pub/Sub → [existing pipeline] → Telegram
v2 path:  Web UI → Research Orchestrator → [existing pipeline] → Web UI (+ optional Telegram)
```

The two paths share everything from the Post Creator onward. The shared unit is the **Story object** — v2 research agents must produce the same Story schema that the newsletter parser outputs.

### 4.2 New Components

#### Web UI
- Full SaaS-style single-page app (React + Tailwind)
- Sidebar navigation: Dashboard, New Post, History
- Topic input → triggers research pipeline via REST call to backend
- Post queue: pending / approved / rejected states
- Per-post actions: approve, reject, preview slides, edit caption
- Toggle: "Also send to Telegram" (default: off)
- Real-time pipeline status (SSE or polling)

#### Research Orchestrator Agent
- Accepts a topic string from the Web UI
- Spawns 3 sub-agents in parallel:
  - **Exa Agent** — semantic search (articles, Reddit, tweets by concept)
  - **Tavily Agent** — deep content extraction (full article body for LLM context)
  - **Serper Agent** — Google News (current events, trending angles)
- Aggregates all results, deduplicates by angle/source
- Synthesises into 1–N Story objects (same schema as newsletter parser output)
- Passes each Story into the existing pipeline

#### Content Validator
- Runs before the Post Creator (between Research Orchestrator and existing pipeline)
- Checks each Story:
  - Is the content factually grounded? (LLM verification pass against raw sources)
  - Is it relevant to the topic as entered?
  - Is it too old? (flag if > 30 days unless the topic is evergreen)
  - Is it a duplicate angle of another Story in this batch?
- Passing Story → continues to Post Creator
- Failing Story → logged, owner notified in Web UI (not a hard stop for other stories)

### 4.3 Story Object Schema

```python
@dataclass
class Story:
    headline: str       # short headline for carousel cover
    summary: str        # 2–4 sentence body for caption + content slide
    url: str            # source URL
    source: str         # "newsletter" | "exa" | "tavily" | "serper"
    topic: str | None   # populated by research path; None for newsletter path
    image_query: str    # search query for Serper image fetch
```

### 4.4 Updated System Diagram

```
Gmail Pub/Sub ──────────────────────────────────┐
                                                 ↓
                                    [Content Fetching Agent]
                                    Parse HTML → Story objects
                                                 ↓
Web UI (topic input) ───────────────────────────┐
                                                 ↓
                              [Research Orchestrator Agent]
                              ┌──────┬──────────┬───────┐
                          [Exa]  [Tavily]   [Serper]
                              └──────┴──────────┴───────┘
                              Aggregate → deduplicate → Story objects
                                                 ↓
                              [Content Validator]
                              Accuracy + relevance + freshness check
                                                 ↓ (per story, parallel)
                    ┌────────────────────────────────────────────┐
                    │         EXISTING v1 PIPELINE               │
                    │  [Post Creator] → [Caption Writer]         │
                    │  → [Post Analyzer] → 1 auto-retry          │
                    └────────────────────────────────────────────┘
                                                 ↓
                              [Web UI — approval queue]
                              + optional [Telegram Bot]
                                                 ↓
                              [Publishing Module — manual stub]
```

---

## 5. Feature Requirements

### 5.1 Web UI

| ID | Requirement |
|---|---|
| UI-01 | Sidebar with: Dashboard, New Post, History, Settings |
| UI-02 | New Post page: single text input for topic, "Create Posts" button |
| UI-03 | Pipeline status shown in real-time: Researching → Creating → Analyzing → Ready |
| UI-04 | Each post card shows: slide preview thumbnails, caption, source, status badge |
| UI-05 | Approve action triggers publisher immediately |
| UI-06 | Reject action archives post with optional rejection reason |
| UI-07 | Caption is editable inline before approving |
| UI-08 | "Send to Telegram" toggle per post (default: off) |
| UI-09 | History tab lists all posts with date, topic/source, status |
| UI-10 | Failed posts shown with failure reason (from Post Analyzer) |

### 5.2 Research Orchestrator

| ID | Requirement |
|---|---|
| RO-01 | All 3 sub-agents run in parallel (not sequential) |
| RO-02 | Total research time target: < 60 seconds |
| RO-03 | Each agent returns a list of raw Result objects (title, body, url, date) |
| RO-04 | Orchestrator deduplicates by URL and by semantic similarity (LLM pass) |
| RO-05 | Synthesises 1–5 Story objects per topic depending on material quality |
| RO-06 | If all 3 agents fail → return error to Web UI, do not enter pipeline |
| RO-07 | If 1–2 agents fail → continue with available results, log partial failure |

### 5.3 Content Validator

| ID | Requirement |
|---|---|
| CV-01 | Runs after Research Orchestrator, before Post Creator |
| CV-02 | LLM cross-checks each Story's claims against its source URL content |
| CV-03 | Flags stories older than 30 days (owner sees warning, not hard block) |
| CV-04 | Removes Stories that are clearly off-topic vs. the input topic |
| CV-05 | Removes duplicate-angle stories within the same batch |
| CV-06 | Validation result attached to Story object, visible in Web UI |

### 5.4 Telegram (updated behavior)

| ID | Requirement |
|---|---|
| TG-01 | Telegram remains fully functional for newsletter path (v1 behavior unchanged) |
| TG-02 | For web UI path, Telegram is opt-in per post via UI toggle |
| TG-03 | Approval via Telegram still triggers immediate publish (same as v1) |
| TG-04 | Approval via Web UI also triggers immediate publish |
| TG-05 | No duplicate sends — if approved in Web UI, Telegram notification is suppressed |

---

## 6. API Contracts

### 6.1 New Backend Endpoints

```
POST /api/v2/research
  Body: { "topic": "string" }
  Returns: { "job_id": "string" }

GET /api/v2/jobs/{job_id}
  Returns: { "status": "researching|creating|analyzing|ready|failed", "stories": [...] }

GET /api/v2/posts
  Returns: list of all posts with status

POST /api/v2/posts/{post_id}/approve
  Returns: { "published": true }

POST /api/v2/posts/{post_id}/reject
  Body: { "reason": "string" (optional) }

PATCH /api/v2/posts/{post_id}/caption
  Body: { "caption": "string" }
```

### 6.2 Existing Endpoints (unchanged)

```
POST /gmail/webhook         — Gmail Pub/Sub trigger (v1, unchanged)
POST /telegram/webhook      — Telegram bot (v1, unchanged)
POST /test/story            — manual pipeline test (v1, unchanged)
```

---

## 7. Research API Integration

| API | Use | Credential |
|---|---|---|
| Exa.ai | Semantic search | `exa-api-key` (new secret) |
| Tavily | Deep content extraction | `tavily-api-key` (new secret) |
| Serper.dev | Google News + images | `serper-api-key` (existing) |

All keys stored in GCP Secret Manager. New secrets must be added before deployment.

---

## 8. Data Model

### Firestore Collections (additions)

```
/jobs/{job_id}
  topic: string
  status: "researching" | "creating" | "analyzing" | "ready" | "failed"
  created_at: timestamp
  story_ids: [string]

/posts/{post_id}
  story: Story
  slides: [string]          # GCS URLs or base64 PNGs
  caption: string
  status: "pending" | "approved" | "rejected"
  source: "newsletter" | "web_ui"
  telegram_sent: bool
  created_at: timestamp
  approved_at: timestamp | null
  rejection_reason: string | null
```

v1 currently only logs failures to Firestore. v2 persists all posts for the approval queue and history view.

---

## 9. Folder Structure

```
src/
  agents/
    content_fetcher/        # v1 — unchanged
    post_creator/           # v1 — unchanged
    caption_writer/         # v1 — unchanged
    post_analyzer/          # v1 — unchanged
    telegram_bot/           # v1 — unchanged (minor: Telegram toggle)
    research_orchestrator/  # NEW
      orchestrator.py
      exa_agent.py
      tavily_agent.py
      serper_agent.py       # repurposed from image-only use
    content_validator/      # NEW
      validator.py
  orchestrator/
    handler.py              # v1 — unchanged
  publishing/
    publisher.py            # v1 — unchanged
  api/
    routes_v1.py            # existing routes extracted here
    routes_v2.py            # NEW v2 endpoints
  utils/
    image_renderer.py       # v1 — unchanged
    firestore_client.py     # extended for posts/jobs collections
    story.py                # Story dataclass (shared)

# Web frontend lives in a separate repo: techwithhareen-web
# Deployed to Vercel. Calls this backend via CORS_ORIGINS env var.
```

---

## 10. Infrastructure Changes

| Resource | Change |
|---|---|
| Cloud Run | Backend only — no frontend served here |
| Vercel | Hosts the React frontend (separate repo: `techwithhareen-web`) |
| Firestore | Add `/jobs` and `/posts` collections (schema above) |
| Secret Manager | Add `exa-api-key`, `tavily-api-key`, `cors-origins` |
| GCS bucket | Store carousel PNGs (currently returned inline — persist for Web UI) |
| IAM | No new service accounts needed |

### CORS
Backend reads `CORS_ORIGINS` env var (comma-separated list of allowed origins).
- Production: set to the Vercel deployment URL
- Local dev: `http://localhost:5173` (Vite default)

---

## 11. Code Quality Requirements

- Each agent in its own file, one responsibility
- All agent files have module-level docstring explaining: what it does, inputs, outputs
- No cross-agent imports except via the Story dataclass in `utils/story.py`
- Backend uses FastAPI (existing), new routes in `api/routes_v2.py`
- Frontend uses React + Tailwind — no component library (keep it lean)
- New Firestore logic goes in `utils/firestore_client.py` (extend existing client)

---

## 12. Out of Scope for v2

| Feature | Reason |
|---|---|
| Multi-user auth | Deferred to v3 |
| Post scheduling | Deferred to v3 |
| Analytics dashboard | Deferred to v3 |
| Instagram Graph API publishing | Manual stub sufficient for now |
| Mobile app | Not planned |

---

## 13. Resolved Decisions

| Question | Decision |
|---|---|
| Host web frontend on same Cloud Run service or separate? | **Same service** — FastAPI serves React build as static files. Avoids second deploy pipeline and CORS complexity. |
| GCS bucket for PNG storage — existing or new? | **New dedicated bucket** — `techwithhareen-carousel-assets`. Clean IAM, 30-day lifecycle rule, no cross-contamination. |
| Exa + Tavily free tier sufficient for initial usage? | **Yes** — both offer 1,000 searches/month free. Sign up, add keys to Secret Manager, monitor first 2 weeks. |

---

## 14. Build Order

1. `utils/story.py` — shared Story dataclass (foundation for all agents)
2. `utils/firestore_client.py` — extend with posts/jobs collections
3. `agents/research_orchestrator/` — Exa + Tavily + Serper agents + orchestrator
4. `agents/content_validator/` — validation logic
5. `api/routes_v2.py` — backend endpoints
6. `web/` — React frontend
7. Integration test: topic → research → pipeline → approval in browser
8. Telegram toggle wiring (minor update to telegram_bot agent)
9. Deploy to Cloud Run on `feature/v2` (separate revision for testing)
10. Merge to `main` when stable
