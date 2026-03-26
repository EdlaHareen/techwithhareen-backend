# techwithhareen — Instagram Agent System

## What This Is

Automated multi-agent system that runs the Instagram page @techwithhareen (AI, Tech, Startups). The system takes content from two sources — the rundownai newsletter (v1) and a web UI topic research pipeline (v2) — and produces carousel posts with Hareen's personal voice captions, approved via a web UI before manual posting.

## Core Value

Every approved post sounds like Hareen — opinionated, direct, signal-not-noise — with zero extra effort from her beyond the approval click.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Gmail newsletter (rundownai) → carousel pipeline — v1
- ✓ Pillow PNG carousel renderer (UncoverAI design: #1A1A2E bg, #8075FF accent, Anton+Inter) — v1
- ✓ GCS upload + public slide URLs — v1
- ✓ Telegram bot approval (approve/reject per post) — v1
- ✓ Web UI topic research → carousel pipeline (Exa + Tavily + Serper) — v2
- ✓ Firestore job + post queue — v2
- ✓ React web UI approval queue (Vercel) — v2
- ✓ Personal-voice captions (Hareen's tone, 4 story types: tool_feature/funding_acquisition/research_finding/general_news) — v3
- ✓ Slide editor in web UI (edit/reorder/delete slides) — v3
- ✓ Read More slide shows "LINK IN DESCRIPTION" (no URL on slide) — v3

### Active

<!-- Current scope: v4 — Algorithm Compliance + Content Engine -->

- [ ] Hashtags 3–5 per post (Instagram best practice, currently using 15–20)
- [ ] Background colour #1A1A2E enforced (was #000000 — OLED readability issue)
- [ ] Two-CTA strategy: mid-carousel bookmark slide + DM-share final CTA
- [ ] Caption first 125 chars enforced as standalone hook
- [ ] Slide 2 works as standalone hook (remove "SWIPE TO FIND OUT WHY")
- [ ] Content type classifier (3 types: news_and_announcements / tool_and_product / educational)
- [ ] Reels Script Agent — generates ready-to-record 15–60s Reel scripts (on-demand, per post)
- [ ] "This Week in AI" Monday roundup series template
- [ ] Stories teaser card (1080×1920, hook stat, on-demand per post)

### Out of Scope

- Instagram Graph API publishing — manual export remains through v4+
- TikTok / YouTube Shorts — Instagram-only scope
- Mixed-media carousels (image + video clips) — deferred to v5
- Scheduling / posting calendar — not needed, Hareen posts manually
- Analytics ingestion — deferred
- Broadcast Channels / Close Friends — premature below 10K followers
- "Worth It or Hype?" and "Hot Take" series — defer to v5, depends on Reels Script adoption data
- Stories insight card + poll/engagement card — defer until 5K followers
- opinion_hot_take classifier type — needs manual entry, not aggregator routing

## Context

- Backend: FastAPI on Cloud Run (`https://insta-handler-371034138276.us-central1.run.app`)
- Frontend: React 19 + Vite + Tailwind v4 on Vercel (`https://techwithhareen-web.vercel.app`)
- Frontend repo: `/Users/hareenedla/Hareen/techwithhareen-web` (github.com/EdlaHareen/techwithhareen-web)
- Backend repo: `/Users/hareenedla/Hareen/insta` (github.com/EdlaHareen/techwithhareen-backend)
- GCS bucket: `techwithhareen-carousel-assets` (public read)
- GCP project: `techwithhareen`, region: `us-central1`
- Firestore native mode, free tier
- Redis (Memorystore) for Telegram bot FSM: `10.74.150.107`
- LLM: Anthropic API direct (AsyncAnthropic client)
- Image search: Serper.dev Google Images
- Research APIs: Exa.ai + Tavily + Serper

## Constraints

- **Approval**: All posts require Hareen's approval before publishing — no autonomous posting ever
- **Solo operator**: All workflows must be completable by one person
- **Budget**: GCP free tier + existing API keys; no new paid infra without sign-off
- **Publishing**: Manual export — Hareen posts PNGs to Instagram manually
- **Reels**: System writes scripts; Hareen records. No video generation.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pillow PNG renderer (no Canva) | Fully local, no external dependencies, parallelised GCS upload | ✓ Good |
| AsyncAnthropic (not sync) | Avoids blocking the FastAPI event loop under concurrent requests | ✓ Good |
| Firestore client-side status filtering | No composite index needed, well within free tier query limits | ✓ Good |
| Hashtag count: 3–5 (v4) | Instagram best practice; 15–20 delivered negligible additional reach | — Pending |
| Content classifier: 3 types (not 5) | 5-type system has misclassification edge cases; 3 types handle 85%+ of actual content | — Pending |
| Reels Script on-demand (not auto) | Auto-generation for every post creates noise; on-demand ties generation to intent | — Pending |
| Stories: teaser card only for v4 | Poll cards need 5K+ community to generate signal; defer insight+poll to v5 | — Pending |

---
*Last updated: 2026-03-25 after v3 milestone complete, initialising v4*
