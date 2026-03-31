# techwithhareen — Insta Handler Manager

## Project Overview

Automated multi-agent system that runs the Instagram page **@techwithhareen** — an AI-powered feed for Tech, AI, and Startups.

The system has two entry points:
- **v1** — reads the daily rundownai newsletter from Gmail, creates carousel posts, writes captions, analyzes quality, and sends to the owner via Telegram for approval
- **v2** — owner types any topic in a web UI, parallel research agents gather content, and the same pipeline produces posts for approval in the browser

**Current version: v4 Phase 1 + v5 Phase 1 shipped. v5 Phase 2 (Educational Redesign) in progress.**

## Version History

| Version | Status | Key Features |
|---------|--------|--------------|
| v1 | ✅ Live | Gmail newsletter → carousel → Telegram approval |
| v2 | ✅ Live | Web UI topic research (Exa+Tavily+Serper) → carousel → web approval queue |
| v3 | ✅ Live | Slide editor, personal-voice captions (Hareen's tone), Read More → "LINK IN DESCRIPTION" |
| v4 Phase 1 | ✅ Shipped | Algorithm compliance: 3–5 hashtags, #1A1A2E bg, BOOKMARK THIS mid-slide, SEND THIS TO SOMEONE CTA, 120-char hook, Slide 2 standalone stat |
| v5 Phase 1 | ✅ Shipped | Educational content pipeline: "Educational" toggle in Web UI, lesson-step carousel, PDF Guide Agent (ReportLab + GCS), auto DM keyword, educational caption voice |
| v5 Phase 2 | 🔧 In Progress | Educational redesign: TopicClarifierAgent (thinking model, 3–5 dynamic questions) + 3 carousel formats (A: Mistakes→Right Way, B: Pillars, C: Cheat Sheet). Branch: `feat/educational-carousel-clarifier-formats` |
| v4 Phases 2–4 | 🔲 Planned | Content classifier, Reels Script Agent, Series + Stories |

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
- **Skipped for educational posts** — single-topic, pre-authored story

### Topic Clarifier Agent (v5 Phase 2 — in progress)
- Triggered for `content_type="educational"` posts, runs BEFORE research
- `POST /api/v2/clarify` — synchronous, returns questions immediately
- Uses `claude-sonnet-4-6` with extended thinking (budget_tokens=5000)
- Generates 3–5 dynamic multiple-choice questions tailored to the topic
- Always includes format question (`id="format"`, options A/B/C)
- On any failure → returns hardcoded Format B defaults (never blocks the user)
- Web UI shows questions as pill-selectors; Hareen answers then hits Generate
- Skip option uses all question defaults (Format B + broad angle)
- Answers passed to research as `clarifier_answers` + `carousel_format`
- File: `src/agents/topic_clarifier/agent.py`

### PDF Guide Agent (v5 — shipped)
- Triggered for `content_type="educational"` posts only
- LLM generates structured guide content (intro + steps + tips) + DM keyword (uppercase, max 8 chars)
- Renders branded A4 PDF using ReportLab (BytesIO — no /tmp writes) with UncoverAI design
- Uploads to GCS at `guides/{slug}.pdf`, returns public URL + dm_keyword
- File: `src/agents/pdf_guide/agent.py`

### Post Creator Agent
- Searches Serper.dev Google Images for a story-relevant image
- For educational posts: image query targets tool visuals (logo/screenshot), not news thumbnails
- Generates carousel PNG slides locally using **Pillow** (no Canva)
- Design system: "UncoverAI" — 1080×1350px, dark navy bg (#1A1A2E), neon periwinkle accent (#8075FF), Anton + Inter fonts
- Slide structure varies by `carousel_format` (v5 Phase 2):
  - Slide 1 — Cover: always the same (image + "DO YOU KNOW" pill + headline)
  - Slide 2 (news) — Hook Stat: large accent number + white context label
  - Slide 2 (Format A) — Accent bg: "MOST PEOPLE DO IT WRONG." — sets up mistake series
  - Slide 2 (Format B) — Hook Stat reused: concept count as number, "KEY PRINCIPLES TO MASTER" label
  - Slide 2 (Format C) — Accent bg: "CHEAT SHEET" + "Save this — you'll use it"
  - Slide 2 (legacy educational, no format) — "WHAT YOU'LL LEARN" accent bg with step bullets
  - Slides 3+ (Format A) — 1 mistake per slide: "MISTAKE #N" pill + wrong approach + divider + "✓ FIX:"
  - Slides 3+ (Format B) — 1 concept per slide: "PRINCIPLE #N" pill + concept name + explanation
  - Slides 3+ (Format C) — 3 tips per slide: accent numbers + white tip text (dense cheat-sheet layout)
  - Mid-carousel — BOOKMARK THIS (Format A + B only; omitted for Format C)
  - Second-to-last — "LINK IN DESCRIPTION"
  - Last (Format A + B) — "SEND THIS TO SOMEONE" + "@TECHWITHHAREEN"
  - Last (Format C) — "SAVE THIS CHEAT SHEET" + "@TECHWITHHAREEN"
- `carousel_format` stored on Story + passed through to renderer + Firestore render_data
- Slides saved as PNGs to `/tmp/carousel_{id}/`, uploaded to GCS
- Returns `CarouselResult` with GCS `https://` URLs + `image_url` (for re-render)

### Caption Writer Agent
- Dedicated agent for Instagram captions
- Uses `anthropic.AsyncAnthropic` (async client — not sync)
- System/user prompt split for prompt injection hardening
- Accepts optional `dm_keyword` param — injected into CTA for educational posts
- **Hareen's voice** — 5 story type modes with distinct tone:
  - `tool_feature` → Translator ("Okay this one's actually useful...")
  - `funding_acquisition` → Contrarian ("Let's be real — $X doesn't mean...")
  - `research_finding` → Accessible + actionable ("This one's worth your time...")
  - `general_news` → Conversational analyst ("What this really signals is...")
  - `educational` → Teacher ("Here's how to [X] — the part most people skip...") + CTA: "DM me [KEYWORD] for the full guide 📩"
- Output format:
  ```
  [Hook line — Hareen's direct take, ≤120 chars, complete sentence]
  [3-4 sentences — Hareen's opinionated take, NOT a neutral summary]
  [CTA — "Send this to someone who needs to see it 👇" (primary) or "Save this post 🔖"]
  [Link in Description 🔗\n<url>  ← only when story.url is present]
  [3-5 story-specific hashtags]
  ```
- `story_type` field logged for observability

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
- Instagram Graph API not integrated (deferred to v5+)
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
 - Pillow PNG renderer → 6-10+ slides
            ↓
[Caption Writer Agent]
 - Hareen's voice hook + opinionated body + DM-share CTA + 3-5 hashtags
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

### v2 — Web UI Topic Research (News)
```
Web UI (topic input, content_type="news")
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
Firestore /posts collection (pending approval) — includes render_data for re-render
            ↓
Web UI approval queue
 - Approve / Reject / Edit caption / Edit slides (reorder, delete, re-render)
 - Optional: also send to Telegram
            ↓
[Publishing Module — manual]
```

### v5 — Web UI Educational Content (Phase 2 redesign in progress)
```
Web UI (topic input, content_type="educational")
            ↓
POST /api/v2/clarify  ← NEW (v5 Phase 2)
            ↓
[TopicClarifierAgent] ← NEW
  - claude-sonnet-4-6 with extended thinking
  - Generates 3–5 topic-specific questions with options
  - Always includes format question (A/B/C)
            ↓
Web UI shows clarifier questions → Hareen picks answers (or skips → Format B defaults)
            ↓
POST /api/v2/research (with carousel_format + clarifier_answers)
            ↓
[ResearchOrchestrator.run_educational(carousel_format, clarifier_answers)]
  - Exa+Tavily+Serper (tutorial/how-to queries)
  - _synthesise_educational() prompt adapts per format (A/B/C)
  - Format A key_stats: "MISTAKE: [text]\nFIX: [text]"
  - Format B key_stats: "[Concept Name]\n[explanation]"
  - Format C key_stats: single-line tips ≤80 chars
  - Returns exactly 1 Story with story.carousel_format set
  - image_query targets tool visuals (logo, screenshot)
            ↓
[ContentValidator SKIPPED]
            ↓
[PostCreatorAgent] (content_type="educational", carousel_format=A/B/C)
  - format-specific Slide 2 + content slides + CTA
            ↓
[PDFGuideAgent] (runs before CaptionWriter)
  - LLM generates guide content + dm_keyword
  - ReportLab PDF → GCS guides/{slug}.pdf
            ↓
[CaptionWriterAgent] (educational voice + dm_keyword)
  - CTA: "DM me [KEYWORD] for the full guide 📩"
            ↓
[PostAnalyzerAgent] (Format C: accepts "SAVE THIS CHEAT SHEET" CTA)
            ↓
Firestore /posts (pdf_url, dm_keyword, content_type, carousel_format in doc + render_data)
            ↓
Web UI approval queue
  - Carousel preview + PDF preview link + DM keyword badge + format badge (Mistakes/Pillars/Cheat Sheet)
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
| Design system | "UncoverAI" — dark navy bg (#1A1A2E), neon periwinkle (#8075FF), Anton + Inter fonts |
| Background colour | #1A1A2E (not pure #000000 — causes halation) |
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
| Hashtag count | 3–5 per post (Instagram Dec 2025 cap — 15-20 is penalised) |
| CTA strategy | DM-share primary ("Send this to someone") + mid-carousel bookmark soft CTA |
| Read More slide | "LINK IN DESCRIPTION" only — no URL on slide; URL lives in caption |
| Vercel SPA routing | vercel.json rewrite `/(.*) → /index.html`; .npmrc legacy-peer-deps for Vite 8 compat |
| GitHub repos | Backend: github.com/EdlaHareen/techwithhareen-backend — Frontend: github.com/EdlaHareen/techwithhareen-web |
| Telegram caption | Full caption sent as separate message (not inline) — Telegram caps inline captions at 1024 chars |
| render_data | Stored in Firestore per post — enables slide re-render from web UI |

## Key Constraints

- **Always manual approval** before any post goes live (Telegram or Web UI)
- **Burst mode** — all posts sent to Telegram at once, no drip/digest
- **Publish immediately** on approval, no scheduling
- **Skip + alert** on failure (no complex retry loops)
- **No deduplication** on v1 — trust rundownai not to repeat stories
- **Hashtags: 3–5 max** — Instagram Dec 2025 algorithm cap

## v4 Roadmap (docs/BRD-v4.md + docs/PRD-v4.md)

### Phase 1 — Algorithm Compliance (next to build)
- F1.1: Hashtags 3–5 enforced in caption writer
- F1.2: Background colour #1A1A2E in renderer
- F1.3: Two-CTA strategy (mid-carousel bookmark slide + DM-share final CTA)
- F1.4: Caption first 125 chars as standalone hook
- F1.5: Slide 2 standalone hook (remove "SWIPE TO FIND OUT WHY")

### Phase 2 — Content Engine
- F2.1: Content type classifier (breaking_news / tool_review / research_finding / opinion_hot_take / evergreen_explainer)
- F2.2: Reels Script Agent — writes 15–60s scripts for Hareen to record
- F2.3: Recurring series templates (Monday roundup / Wednesday "Worth It or Hype?" / Friday Hot Take)
- F2.4: Stories pipeline — 3 Story cards (1080×1920) per approved post

## Key Files

```
src/
  agents/
    content_fetcher/        — newsletter HTML parser (v1)
    research_orchestrator/  — Exa + Tavily + Serper + LLM synthesis (v2)
    content_validator/      — relevance/freshness/dedup checks (v2)
    post_creator/           — Pillow carousel generator + image fetcher
    caption_writer/         — Instagram caption LLM agent (Hareen's voice, 4 story types)
    pdf_guide/              — PDFGuideAgent: ReportLab PDF + GCS upload + DM keyword gen (v5)
    post_analyzer/          — 5-check quality gate with auto-retry
    telegram_bot/           — aiogram bot, approval flow
  orchestrator/
    handler.py              — InstaHandlerManager, parallel per-story pipeline
  api/
    routes_v1.py            — Gmail webhook, Telegram webhook, test endpoints
    routes_v2.py            — Web UI research, job polling, post approval, slide editor
  utils/
    story.py                — shared Story dataclass (v1 + v2)
    carousel_renderer.py    — Pillow PNG slide generator (UncoverAI design)
    carousel_service.py     — async wrapper: image download + render + CarouselResult
    carousel_result.py      — CarouselResult dataclass (includes image_url for re-render)
    firestore_client.py     — Firestore CRUD (jobs, posts, failures, gmail state, slide ops)
    gmail_client.py         — OAuth2 Gmail service, Pub/Sub decoder
  publishing/
    publisher.py            — manual export stub
  main.py                   — FastAPI app, CORS, router registration
docs/
  BRD-v4.md                 — Business Requirements Document for v4
  PRD-v4.md                 — Product Requirements Document for v4 (5 features, 2 phases)
  insta-playbook.md         — Deep research: Instagram AI/tech creator best practices 2025
  HANDBOOK.md               — General project handbook

# Frontend: /Users/hareenedla/Hareen/techwithhareen-web (separate repo)
# Components: PostCard, SlideEditorModal (two-tab: content edit + manage slides)
```
