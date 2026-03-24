# techwithhareen — Insta Handler Manager

## Project Overview

Automated multi-agent system that runs the Instagram page **@techwithhareen** — an AI-powered feed for Tech, AI, and Startups.

The system has two entry points:
- **v1** — reads the daily rundownai newsletter from Gmail, creates carousel posts, writes captions, analyzes quality, and sends to the owner via Telegram for approval
- **v2** — owner types any topic in a web UI, parallel research agents gather content, and the same pipeline produces posts for approval in the browser

## Agent Architecture

### Insta Handler Manager (Orchestrator)
- Coordinates all agents
- v1: triggered by Gmail Pub/Sub event when rundownai newsletter arrives
- Manages per-story pipeline execution (parallel)
- Routes failures to Telegram alerts

### Content Fetching Agent (v1 only)
- Parses rundownai newsletter HTML from Gmail
- Extracts all stories via LLM (no deduplication — trust the source)
- Passes each story downstream as a Story object

### Research Orchestrator (v2 only)
- Accepts a topic string from the Web UI
- Runs 3 sub-agents in parallel:
  - **Exa Agent** — semantic/neural search (articles, thought pieces)
  - **Tavily Agent** — deep content extraction (full article body)
  - **Serper Agent** — Google News (current events, trending angles)
- LLM synthesis pass: aggregates + deduplicates → 1–5 Story objects
- Raises `ResearchError` if all agents fail

### Content Validator (v2 only)
- Runs after Research Orchestrator, before Post Creator
- LLM relevance check — is each story on-topic?
- Freshness check — flags stories older than 30 days
- Deduplication — drops same-angle stories within a batch
- Non-blocking: failing stories are logged, others continue

### Post Creator Agent
- Searches Serper.dev Google Images for a story-relevant image
- Generates carousel PNG slides locally using **Pillow** (no Canva)
- Design system: "UncoverAI" — 1080×1350px, black bg, neon periwinkle accent (#8075FF), Anton + Inter fonts
- Slide structure (6–10+ slides):
  - Slide 1 — Cover: story image + "DO YOU KNOW" pill + bold headline (word-level accent alternation)
  - Slide 2 — Hook Stat: large accent number + white context label + "SWIPE TO FIND OUT WHY"
  - Slide 3+ — Content: numbered stat bullets (accent numbers, white text), max 4 per slide, as many slides as needed
  - Second-to-last slide — Read More: "READ MORE" in accent + source URL (only when story.url is present)
  - Last slide — CTA: "FOLLOW FOR MORE" + "@TECHWITHHAREEN" in accent
- LLM is prompted to generate 8–12 key_stats per story (was 3–6); renderer chunks them into content slides automatically
- Slides saved as PNGs to `/tmp/carousel_{id}/`
- Returns `CarouselResult` with `file://` URLs

### Caption Writer Agent
- Dedicated agent for Instagram captions
- Uses `anthropic.AsyncAnthropic` (async client — not sync)
- System/user prompt split for prompt injection hardening
- Persona instruction adapts tone to story type (product launch, funding, research, general)
- Output format:
  ```
  [Hook line — tone adapted to story type]
  [3-4 sentence summary of the story]
  [CTA — e.g., "Save this post 🔖"]
  [Link in Description 🔗\n<url>  ← only when story.url is present]
  [15-20 AI-generated hashtags]
  ```

### Post Analyzer Agent
- Checks every post before it reaches the user:
  - ✅ Design consistency (fonts, colors, brand name)
  - ✅ Hook strength (cover slide)
  - ✅ Hashtags present and relevant
  - ✅ Caption quality and formatting
  - ✅ CTA on last slide
- **1 auto-fix retry** if checks fail
- If still failing after retry → skip story + send Telegram alert to owner

### Telegram Bot
- v1: burst-sends all post previews + captions after processing
- v2: opt-in per post (default off — Web UI is primary approval channel)
- Owner replies approve/reject per post
- On approve → triggers publisher immediately
- On failure alert → notifies owner with story title + reason

### Publishing Module (stub)
- Manual export — owner downloads PNGs and posts to Instagram manually
- Instagram Graph API not integrated (deferred to v3)
- Triggered on Telegram or Web UI approval

## Pipeline Flow

### v1 — Gmail Newsletter
```
Gmail Pub/Sub (rundownai arrives)
            ↓
[Content Fetching Agent]
 - Parse HTML, extract all stories via LLM
            ↓ (per story, parallel)
[Post Creator Agent]
 - Serper image search → download image
 - Pillow PNG renderer → 4-7 slides
            ↓
[Caption Writer Agent]
 - Hook + summary + CTA + hashtags
            ↓
[Post Analyzer Agent]
 - Quality check → 1 auto-retry → skip + alert if still failing
            ↓
[Telegram Bot]
 - Burst send all posts for approval
 - Approve → publisher stub
            ↓
[Publishing Module — manual]
```

### v2 — Web UI Topic Research
```
Web UI (topic input)
            ↓
POST /api/v2/research
            ↓
[Research Orchestrator]
 ┌────────────────────────────────┐
 │  [Exa]  [Tavily]  [Serper]    │  (parallel)
 └────────────────────────────────┘
 - Aggregate → deduplicate → LLM synthesis → Story objects
            ↓
[Content Validator]
 - Relevance + freshness + dedup
            ↓ (per story, parallel)
[Same v1 pipeline: Post Creator → Caption Writer → Post Analyzer]
            ↓
Firestore /posts collection (pending approval)
            ↓
Web UI approval queue
 - Approve / Reject / Edit caption
 - Optional: also send to Telegram
            ↓
[Publishing Module — manual]
```

## Infrastructure (GCP)

| Service | Purpose |
|---|---|
| **Cloud Run** | Host and run all agents (FastAPI) — `https://insta-handler-371034138276.us-central1.run.app` |
| **Pub/Sub** | Gmail push notification trigger |
| **Secret Manager** | Store API keys (Gmail, Telegram, Serper, Exa, Tavily, Anthropic, CORS) |
| **Firestore** | Job tracking, post approval queue, failure logging |
| **Memorystore (Redis)** | Telegram bot FSM state persistence |
| **Cloud Storage** | Carousel PNG storage — `techwithhareen-carousel-assets` (public read) |
| **Artifact Registry** | Docker image storage |
| **Cloud Build** | CI/CD — `infra/cloudbuild.yaml` |

## Resolved Architecture Decisions

| Decision | Choice |
|---|---|
| Carousel creation | Pillow PNG renderer — no Canva, fully local; GCS uploads parallelised with asyncio.gather |
| Design system | "UncoverAI" — black bg, neon periwinkle (#8075FF), Anton + Inter fonts |
| LLM API | Direct Anthropic API key — no Vertex AI |
| Image search | Serper.dev Google Images |
| Research APIs | Exa.ai (semantic) + Tavily (deep extraction) + Serper (Google News) |
| Instagram publishing | Manual export stub — owner posts PNGs manually |
| Telegram bot library | aiogram 3.x |
| Web frontend | React 19 + Vite + Tailwind v4 — separate repo `techwithhareen-web`, deployed to Vercel |
| Backend API | FastAPI — v1 routes in `api/routes_v1.py`, v2 in `api/routes_v2.py` |
| Firestore mode | Native mode (not Datastore mode, not Bigtable) — free tier, well within limits |
| Firestore status filtering | Client-side filtering only — no composite index on (status, created_at) |
| Slide count | 8–12 key_stats per story → 6–10+ slides; renderer chunks 4 stats per content slide |
| Vercel SPA routing | vercel.json rewrite `/(.*) → /index.html`; .npmrc legacy-peer-deps for Vite 8 compat |
| GitHub repos | Backend: github.com/EdlaHareen/techwithhareen-backend — Frontend: github.com/EdlaHareen/techwithhareen-web |
| Telegram caption | Full caption sent as separate message (not inline) — Telegram caps inline captions at 1024 chars |

## Key Constraints

- **Always manual approval** before any post goes live (Telegram or Web UI)
- **Burst mode** — all posts sent to Telegram at once, no drip/digest
- **Publish immediately** on approval, no scheduling
- **Skip + alert** on failure (no complex retry loops)
- **No deduplication** on v1 — trust rundownai not to repeat stories

## Key Files

```
src/
  agents/
    content_fetcher/        — newsletter HTML parser (v1)
    research_orchestrator/  — Exa + Tavily + Serper + LLM synthesis (v2)
    content_validator/      — relevance/freshness/dedup checks (v2)
    post_creator/           — Pillow carousel generator + image fetcher
    caption_writer/         — Instagram caption LLM agent
    post_analyzer/          — 5-check quality gate with auto-retry
    telegram_bot/           — aiogram bot, approval flow
  orchestrator/
    handler.py              — InstaHandlerManager, parallel per-story pipeline
  api/
    routes_v1.py            — Gmail webhook, Telegram webhook, test endpoints
    routes_v2.py            — Web UI research, job polling, post approval queue
  utils/
    story.py                — shared Story dataclass (v1 + v2)
    carousel_renderer.py    — Pillow PNG slide generator (UncoverAI design)
    carousel_service.py     — async wrapper: image download + render + CarouselResult
    carousel_result.py      — CarouselResult dataclass
    firestore_client.py     — Firestore CRUD (jobs, posts, failures, gmail state)
    gmail_client.py         — OAuth2 Gmail service, Pub/Sub decoder
  publishing/
    publisher.py            — manual export stub
  main.py                   — FastAPI app, CORS, router registration

# Frontend: /Users/hareenedla/Hareen/techwithhareen-web (separate repo)
```
