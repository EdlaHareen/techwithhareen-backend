# techwithhareen — Insta Handler Manager

## Project Overview

Automated multi-agent system that runs the Instagram page **@techwithhareen** — an AI-powered feed for Tech, AI, and Startups.

The system reads the daily **rundownai** newsletter from Gmail, creates carousel posts in Canva, writes captions, analyzes post quality, and sends them to the owner via Telegram for approval before publishing.

## Agent Architecture

### Insta Handler Manager (Orchestrator)
- Coordinates all agents
- Triggered by Gmail Pub/Sub event when rundownai newsletter arrives
- Manages per-story pipeline execution (parallel)
- Routes failures to Telegram alerts

### Content Fetching Agent
- Parses rundownai newsletter HTML from Gmail
- Extracts all stories (no deduplication — trust the source)
- Passes each story downstream as a job

### Post Creator Subagent
- Uses **Canva MCP** to create carousel posts
- Canva template ID: `DAHDs0ivk0M`
- Template structure:
  - Slide 1 — Cover: "Do you know... [hook]?" + brand
  - Slide 2 — Teaser: "Let me tell you / check next slide" (evergreen)
  - Slide 3 — Content: stats/key points (duplicate as needed)
  - Slide 4 — CTA: "Follow for more!" (evergreen)
- Replace `BrocelleTech` → `@techwithhareen` and `www.reallygreatsite.com` throughout
- **Image Fetcher** sub-step: searches Google Images for story-relevant image → uploads to Canva → places on content slide
- Flexible slide count: 3-4 slides (short story) / 6-7 slides (deep story)

### Caption Writer Agent
- Dedicated agent for Instagram captions
- Output format:
  ```
  [Hook line]
  [3-4 sentence summary of the story]
  [CTA — e.g., "Save this post 🔖"]
  [AI-generated hashtags]
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
- Sends all post previews + captions in a burst after processing
- Owner replies approve/reject per post
- On approve → publish immediately (Publishing Module)
- On failure alert → notifies owner with story title + reason

### Publishing Module (TBD)
- Pluggable — Instagram Graph API or manual export for now
- Triggered immediately on Telegram approval

## Pipeline Flow

```
Gmail Pub/Sub (rundownai arrives)
            ↓
[Content Fetching Agent]
 - Parse HTML, extract all stories
            ↓ (per story, parallel)
[Post Creator Subagent]  ←→  Canva MCP
 - Google Images fetch → relevant image
 - Build carousel (Cover → Teaser → Content × N → CTA)
            ↓
[Caption Writer Agent]
 - Hook + summary + CTA + hashtags
            ↓
[Post Analyzer Agent]
 - Quality check → 1 auto-retry → skip + alert if still failing
            ↓
[Telegram Bot]
 - Burst send all posts for approval
 - Approve → publish immediately
            ↓
[Publishing Module — TBD]
```

## Infrastructure (GCP)

| Service | Purpose |
|---|---|
| **Cloud Run** | Host and run all agents |
| **Pub/Sub** | Gmail push notification trigger |
| **Secret Manager** | Store API keys (Gmail, Canva, Telegram, Serper, Anthropic) |
| **Firestore** | Minimal job logging (failures only) |
| **Memorystore (Redis)** | Telegram bot FSM state persistence |

## Resolved Architecture Decisions

| Decision | Choice |
|---|---|
| Canva integration | `claude-agent-sdk` + Canva MCP (no Enterprise account) |
| LLM API | Direct Anthropic API key via LiteLLM — no Vertex AI |
| Image search | Serper.dev (Google Custom Search API is deprecated) |
| Instagram publishing | Manual export stub — Canva slides exported as PNG, owner posts manually |
| Telegram bot library | aiogram 3.x |
| Agent framework | Google ADK with `ParallelAgent` for per-story parallel processing |

## Key Constraints

- **Always manual approval** before any post goes live (Telegram)
- **Burst mode** — all posts sent to Telegram at once, no drip/digest
- **Publish immediately** on approval, no scheduling
- **Skip + alert** on failure (no complex retry loops)
- **No deduplication** — trust rundownai not to repeat stories

## Brainstorm Doc

Full brainstorm at: `docs/brainstorms/2026-03-12-insta-handler-manager-brainstorm.md`
