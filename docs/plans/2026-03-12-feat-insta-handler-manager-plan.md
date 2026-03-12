---
title: "feat: Insta Handler Manager — Multi-Agent Instagram Automation"
type: feat
status: active
date: 2026-03-12
---

# feat: Insta Handler Manager — Multi-Agent Instagram Automation

## Overview

Build a cloud-hosted multi-agent system on GCP that fully automates the **@techwithhareen** Instagram page. The system reads every rundownai newsletter from Gmail, creates carousel posts per story, writes captions, analyzes quality, and sends posts to the owner via Telegram for manual approval before publishing.

**Brainstorm:** `docs/brainstorms/2026-03-12-insta-handler-manager-brainstorm.md`

---

## ⚠️ Critical Pre-Build Decision: Canva Integration Path

Research revealed a blocker that must be resolved before Phase 3.

The **Canva MCP tools** (used interactively in Claude Code) are LLM-dispatched and **cannot be called directly from Python code**. Two paths exist:

| Path | How | Requirement | Recommendation |
|---|---|---|---|
| **A — claude-agent-sdk + Canva MCP** | Python spawns a Claude agent session with Canva MCP enabled. Claude drives the MCP tools via natural language. | Canva account (any tier) | ✅ Use this |
| **B — Canva Connect REST API** | Python calls Canva's autofill REST API to fill template fields programmatically | **Canva Enterprise** org | ❌ Requires paid upgrade |

**Decision: Use Path A (claude-agent-sdk + Canva MCP).** This avoids the Enterprise requirement and leverages the existing Canva template (ID: `DAHDs0ivk0M`) directly. The Post Creator Agent runs as a Claude agent session with Canva MCP tools available.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Agent Framework | Google ADK (`google-adk`) |
| LLM | Claude via direct Anthropic API (`ANTHROPIC_API_KEY`) + LiteLLM |
| Post Creator | `claude-agent-sdk` + Canva MCP |
| Telegram Bot | `aiogram` 3.x |
| Gmail API | `google-api-python-client` + `google-auth-oauthlib` |
| Newsletter Parsing | `html2text` + Claude Haiku |
| Image Search | Serper.dev API (Google Custom Search API is deprecated) |
| Telegram FSM State | Cloud Memorystore (Redis) |
| Infrastructure | GCP: Cloud Run, Pub/Sub, Firestore, Secret Manager, Memorystore |
| IaC | Terraform |

---

## Project Structure

```
insta/
├── CLAUDE.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── docs/
│   ├── brainstorms/
│   └── plans/
├── src/
│   ├── main.py                        # Cloud Run entry point (Flask/FastAPI)
│   ├── orchestrator/
│   │   └── handler.py                 # Insta Handler Manager (ADK SequentialAgent)
│   ├── agents/
│   │   ├── content_fetcher/
│   │   │   ├── agent.py               # Content Fetching Agent
│   │   │   └── newsletter_parser.py   # html2text + Claude Haiku extraction
│   │   ├── post_creator/
│   │   │   ├── agent.py               # Post Creator (claude-agent-sdk + Canva MCP)
│   │   │   └── image_fetcher.py       # Serper.dev image search
│   │   ├── caption_writer/
│   │   │   └── agent.py               # Caption Writer Agent
│   │   ├── post_analyzer/
│   │   │   └── agent.py               # Post Analyzer Agent (quality checks)
│   │   └── telegram_bot/
│   │       ├── bot.py                 # aiogram bot + webhook handler
│   │       └── keyboards.py           # Inline approve/reject keyboards
│   ├── publishing/
│   │   └── publisher.py               # Pluggable publishing module (TBD)
│   └── utils/
│       ├── gmail_client.py            # Gmail API wrapper
│       ├── canva_session.py           # claude-agent-sdk + Canva MCP session manager
│       ├── firestore_client.py        # Firestore job failure logger
│       └── secrets.py                 # GCP Secret Manager helpers
├── infra/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── pubsub.tf                  # Gmail Pub/Sub topic + subscription
│   │   ├── cloud_run.tf               # Cloud Run service definitions
│   │   ├── firestore.tf               # Firestore database
│   │   ├── memorystore.tf             # Redis for Telegram FSM
│   │   └── secrets.tf                 # Secret Manager secret definitions
│   └── cloudbuild.yaml                # CI/CD pipeline
└── scripts/
    └── setup_gmail_watch.py           # One-time Gmail watch() setup + renewal
```

---

## Implementation Phases

### Phase 1: GCP Infrastructure Foundation

**Goal:** All GCP services provisioned and credentials wired. Cloud Run responds to a Pub/Sub push.

#### Tasks

- [ ] Create GCP project and enable APIs: Cloud Run, Pub/Sub, Firestore, Secret Manager, Memorystore, Cloud Scheduler, Vertex AI
- [ ] Write `infra/terraform/main.tf` — provider config, project variables
- [ ] Write `infra/terraform/pubsub.tf`:
  - Topic: `gmail-notifications`
  - Grant publish rights to `gmail-api-push@system.gserviceaccount.com`
  - Push subscription → Cloud Run URL
- [ ] Write `infra/terraform/secrets.tf` — define secret names (no values):
  - `gmail-oauth-token`, `canva-client-id`, `canva-client-secret`, `anthropic-api-key`, `telegram-bot-token`, `serper-api-key`
- [ ] Write `infra/terraform/firestore.tf` — Firestore native mode, `failed_jobs` collection
- [ ] Write `infra/terraform/memorystore.tf` — Redis instance for Telegram FSM state
- [ ] Write `infra/terraform/cloud_run.tf` — service definition with secret env vars, min-instances=1 for Telegram bot
- [ ] Write `Dockerfile` — Python 3.12 slim, non-root user, uvicorn entrypoint
- [ ] Write `src/main.py` — FastAPI app with `/pubsub/push`, `/telegram/webhook`, `/renew-watch`, `/healthz` routes
- [ ] Write `scripts/setup_gmail_watch.py` — calls `users().watch()`, stores initial `historyId` in Firestore
- [ ] Write `infra/cloudbuild.yaml` — build → push → deploy pipeline
- [ ] Create `.env.example` with all required secret names documented

**Acceptance Criteria:**
- [ ] `terraform apply` provisions all resources without errors
- [ ] `POST /pubsub/push` with a valid Pub/Sub envelope returns HTTP 200
- [ ] `/healthz` returns `{"status": "ok"}`
- [ ] Gmail watch script runs and stores `historyId` in Firestore

---

### Phase 2: Content Fetching Agent

**Goal:** When rundownai newsletter arrives in Gmail, agent extracts all stories as structured data.

#### Tasks

- [ ] Write `src/utils/gmail_client.py`:
  - `get_gmail_service()` — OAuth2 with service account + domain delegation
  - `decode_pubsub_notification(envelope)` — base64url decode + padding fix
  - `get_history_since(history_id)` — `users().history().list()` call
  - `get_message(message_id)` — fetch full message with `format=full`
  - `extract_html_body(payload)` — recursive MIME part extraction
  - `get_and_store_history_id(new_id)` — Firestore cursor update
- [ ] Write `src/agents/content_fetcher/newsletter_parser.py`:
  - `html_to_markdown(html)` — `html2text` conversion with link preservation
  - `extract_stories_with_llm(markdown, anthropic_client)` — Claude Haiku call returning `list[Story]`
  - `Story` dataclass: `headline`, `summary`, `url`, `key_stats: list[str]`
- [ ] Write `src/agents/content_fetcher/agent.py`:
  - `ContentFetcherAgent` — ADK `LlmAgent` wrapping the Gmail + parser flow
  - Tools: `fetch_latest_newsletter()`, `parse_newsletter(html)`
  - Returns: `list[Story]`
- [ ] Wire into `src/main.py` `/pubsub/push` handler — decode notification, trigger agent, fan out stories to orchestrator
- [ ] Handle the `watch()` 7-day expiry: add `/renew-watch` endpoint + Cloud Scheduler job (`0 6 * * *`)

**Acceptance Criteria:**
- [ ] Sending a real rundownai newsletter to the Gmail account triggers the Pub/Sub push
- [ ] Agent extracts correct `headline`, `summary`, `url`, `key_stats` for each story
- [ ] `historyId` advances correctly in Firestore after each notification
- [ ] Duplicate Pub/Sub deliveries are handled idempotently (same `historyId` = no reprocessing)

---

### Phase 3: Post Creator Agent

**Goal:** For each story, create an Instagram carousel in Canva using the existing template.

#### Tasks

- [ ] Write `src/utils/canva_session.py`:
  - `CanvaSession` class — manages `claude-agent-sdk` `ClaudeSDKClient` session with Canva MCP enabled
  - MCP config: `{"canva": {"command": "npx", "args": ["@canva/cli@latest", "mcp"], "type": "stdio"}}`
  - `create_carousel(story: Story, image_url: str) -> CarouselResult` — sends natural language prompt to Claude agent with Canva MCP tools
  - `CarouselResult` dataclass: `design_id`, `export_urls: list[str]`, `slide_count`
- [ ] Write `src/agents/post_creator/image_fetcher.py`:
  - `search_image(query: str) -> str` — Serper.dev images endpoint, returns best image URL
  - Query construction: `f"{story.headline} {extracted_brand_name}"` (e.g., "Microsoft Copilot")
  - Fallback: return `None` if no image found (agent proceeds without image)
- [ ] Write `src/agents/post_creator/agent.py`:
  - `PostCreatorAgent` — ADK `LlmAgent`
  - Prompt to Canva session: open template `DAHDs0ivk0M`, fill cover hook, duplicate content slide as needed, replace `BrocelleTech` → `@techwithhareen`, add fetched image, export slides as PNG
  - Slide count logic: `len(story.key_stats) <= 3` → 4 slides; else 7 slides
  - Returns: `CarouselResult`

**Canva session prompt template:**
```
Open design DAHDs0ivk0M. Make the following changes:
1. Slide 1 (Cover): Change "Do you know" hook text to "Do you know [HEADLINE]?"
   Replace "BrocelleTech" with "@techwithhareen" on all slides.
   Replace "www.reallygreatsite.com" with "techwithhareen" on all slides.
2. Slide 3 (Content): Replace stats with: [KEY_STATS as bullets].
   If more than 3 stats, duplicate slide 3 for additional stats.
3. Add this image to the content slide: [IMAGE_URL] (if provided).
4. Export all slides as PNG images.
```

**Acceptance Criteria:**
- [ ] Agent successfully opens template `DAHDs0ivk0M` via Canva MCP session
- [ ] Brand name replaced on all slides
- [ ] Content slides contain story-specific stats
- [ ] Fetched image placed on content slide when available
- [ ] PNG exports returned for all slides
- [ ] `image_fetcher.py` returns relevant image for test query "OpenAI GPT-5"

---

### Phase 4: Caption Writer Agent

**Goal:** Generate a complete Instagram caption for each story.

#### Tasks

- [ ] Write `src/agents/caption_writer/agent.py`:
  - `CaptionWriterAgent` — ADK `LlmAgent` (Claude Sonnet)
  - Input: `Story` + `CarouselResult`
  - System prompt: enforce caption format strictly
  - Output: `Caption` dataclass with `hook`, `body`, `cta`, `hashtags: list[str]`, `full_text`
- [ ] Caption format prompt:
  ```
  Write an Instagram caption for @techwithhareen (AI/Tech/Startups feed).
  Format:
  1. Hook line (one punchy sentence, no emoji)
  2. 3-4 sentence summary of the story
  3. CTA: "Save this post 🔖" or "Follow @techwithhareen for daily AI updates"
  4. 15-20 relevant hashtags (AI, tech, startups focused)

  Story: {story.headline}
  Summary: {story.summary}
  ```
- [ ] Hashtag strategy: mix of high-volume (`#AI`, `#Tech`) + niche (`#AIStartups`, `#AITools`) + branded (`#techwithhareen`)
- [ ] Validate output: caption must have hook, body (≥3 sentences), CTA, ≥10 hashtags

**Acceptance Criteria:**
- [ ] Caption for any test story passes all validation checks
- [ ] Hashtags are story-relevant (not generic spam)
- [ ] Full caption under Instagram's 2,200 character limit
- [ ] CTA present on every caption

---

### Phase 5: Post Analyzer Agent

**Goal:** Quality gate — check every post before it reaches the owner's Telegram.

#### Tasks

- [ ] Write `src/agents/post_analyzer/agent.py`:
  - `PostAnalyzerAgent` — ADK `LlmAgent`
  - Input: `CarouselResult` (slide images + slide count) + `Caption`
  - Runs **5 checks** in parallel using ADK `ParallelAgent`:
    1. `DesignCheckAgent` — fonts/colors/brand consistent with template
    2. `HookCheckAgent` — cover slide has strong question hook
    3. `HashtagCheckAgent` — ≥10 hashtags, at least 3 niche ones
    4. `CaptionCheckAgent` — hook + body + CTA all present
    5. `CTACheckAgent` — last slide has CTA text
  - `AnalysisResult` dataclass: `passed: bool`, `issues: list[str]`, `fix_instructions: list[str]`
- [ ] **Auto-fix retry logic:**
  - If `passed=False` → pass `fix_instructions` back to `PostCreatorAgent` + `CaptionWriterAgent`
  - Second analysis run → if still `passed=False` → skip story + log to Firestore + Telegram alert
  - Max 1 retry
- [ ] Write failure logging in `src/utils/firestore_client.py`:
  - `log_failed_story(story, issues, retry_attempted)` → `failed_jobs` collection

**Acceptance Criteria:**
- [ ] All 5 checks run and return structured results
- [ ] A post missing CTA is caught and flagged
- [ ] A post missing hashtags is caught and flagged
- [ ] Auto-fix retry triggers exactly once on first failure
- [ ] Second failure correctly skips the story and logs to Firestore

---

### Phase 6: Telegram Bot

**Goal:** Send all processed posts to the owner for burst approval. Trigger publish on approval.

#### Tasks

- [ ] Write `src/agents/telegram_bot/keyboards.py`:
  - `build_approval_keyboard(story_id: str)` → `InlineKeyboardMarkup` with Approve / Reject buttons
  - Callback data format: `"approve:{story_id}"` / `"reject:{story_id}"`
- [ ] Write `src/agents/telegram_bot/bot.py`:
  - `aiogram` 3.x `Dispatcher` + `Router`
  - `RedisStorage` (Cloud Memorystore) for FSM state
  - `send_post_for_approval(story_id, slide_images, caption)`:
    - Send slide images as `media_group` (album)
    - Send caption text + approval keyboard as follow-up message
  - `handle_approve(query)`: call `trigger_downstream(story_id, approved=True)`, edit keyboard away
  - `handle_reject(query)`: log rejection, edit keyboard away
  - `send_failure_alert(story_id, headline, issues)`: simple text notification for skipped stories
  - Webhook registered at `/telegram/webhook` via `SimpleRequestHandler`
  - Webhook secret token validated from Secret Manager
- [ ] Wire bot startup into `src/main.py` lifespan event: register webhook on startup
- [ ] Store `OWNER_CHAT_ID` in Secret Manager (populated on first `/start` command)

**Acceptance Criteria:**
- [ ] Bot sends test carousel images + caption with Approve/Reject buttons
- [ ] Approve button triggers `trigger_downstream()` and removes keyboard
- [ ] Reject button removes keyboard silently
- [ ] Failure alert for a skipped story arrives as plain text notification
- [ ] FSM state survives Cloud Run scale-to-zero (Redis persistence)

---

### Phase 7: Orchestrator Integration

**Goal:** Wire all agents together. Insta Handler Manager runs the full pipeline end-to-end.

#### Tasks

- [ ] Write `src/orchestrator/handler.py`:
  - `InstaHandlerManager` — top-level ADK `SequentialAgent`
  - Step 1: `ContentFetcherAgent` → `list[Story]`
  - Step 2: ADK `ParallelAgent` — fan out one pipeline per story simultaneously:
    - Each story pipeline: `PostCreatorAgent` → `CaptionWriterAgent` → `PostAnalyzerAgent`
  - Step 3: Collect all `passed` posts → burst-send all to Telegram bot
  - Error handling: catch per-story exceptions, log to Firestore, continue with remaining stories
  - Send Telegram failure alerts for all skipped stories at the end
- [ ] Write `src/publishing/publisher.py`:
  - `publish(story_id, slide_images, caption)` → stub returning `{"status": "pending_manual"}` (TBD)
  - `trigger_downstream(story_id, approved)` → calls `publisher.publish()` when approved
- [ ] Integration test: feed a real rundownai HTML fixture through the full pipeline end-to-end
- [ ] Add request timeout of 270s on Cloud Run invocation (Cloud Run max is 3600s; keep headroom)

**Acceptance Criteria:**
- [ ] Full pipeline runs end-to-end from Pub/Sub notification to Telegram approval message
- [ ] Multiple stories processed in parallel (verify via Cloud Run logs)
- [ ] A story that fails twice is skipped and owner receives alert, others continue
- [ ] Approving a post calls `publisher.publish()` correctly

---

### Phase 8: Deployment & Hardening

**Goal:** Production-ready deployment on GCP with monitoring and scheduled watch renewal.

#### Tasks

- [ ] Finalize `Dockerfile` — multi-stage build, non-root user, Python 3.12-slim
- [ ] Write `infra/cloudbuild.yaml`:
  - Trigger: push to `main` branch
  - Steps: lint → test → docker build → push to Artifact Registry → deploy to Cloud Run
- [ ] `terraform apply` full infra stack
- [ ] Set up Cloud Scheduler job: `POST /renew-watch` daily at 06:00 UTC (Gmail watch expires every 7 days)
- [ ] Set Cloud Run min-instances:
  - Telegram bot service: `min-instances=1` (must respond to webhooks without cold start)
  - Orchestrator service: `min-instances=0` (triggered by Pub/Sub, cold start acceptable)
- [ ] Pin all Secret Manager secret versions in Cloud Run service definition (not `latest`)
- [ ] Configure Cloud Run service account with least-privilege IAM
- [ ] Add `GET /healthz` → Cloud Run liveness probe
- [ ] Run `scripts/setup_gmail_watch.py` against production Gmail account
- [ ] Smoke test: send a test email from rundownai address, verify full pipeline fires

**Acceptance Criteria:**
- [ ] `cloudbuild.yaml` triggers and deploys successfully on `git push`
- [ ] Gmail watch is active and `historyId` is stored in Firestore
- [ ] Cloud Scheduler job renews watch daily without manual intervention
- [ ] Telegram bot responds to approval within 5 seconds of button tap
- [ ] Cloud Run logs show clean pipeline execution for a real newsletter

---

## Acceptance Criteria (Full System)

### Functional
- [ ] rundownai newsletter arrives → all stories extracted automatically
- [ ] Each story → carousel created in Canva with brand, story content, relevant image
- [ ] Each post → Instagram caption with hook + summary + CTA + hashtags
- [ ] Each post → quality analyzed, auto-fixed once if needed
- [ ] All passing posts → burst-sent to Telegram for approval
- [ ] Owner approves → publishing stub called
- [ ] Failed stories → skipped + Telegram alert sent
- [ ] Gmail watch renews automatically every day

### Non-Functional
- [ ] Full pipeline for a 5-story newsletter completes in under 5 minutes
- [ ] No API keys in code — all via Secret Manager
- [ ] No posts go live without owner approval
- [ ] System recovers from Pub/Sub redelivery without duplicate posts

---

## Dependencies & Risks

| Risk | Mitigation |
|---|---|
| Canva MCP session instability in headless Cloud Run | Test claude-agent-sdk + Canva MCP in Cloud Run early (Phase 3). Fallback: use Canva Connect REST API if Enterprise tier is available. |
| Gmail watch() not triggering reliably | Store `historyId` cursor; Cloud Scheduler fallback polling endpoint |
| Serper.dev image URLs returning broken links | Validate image URL with HEAD request before sending to Canva |
| Telegram bot FSM state lost on Redis restart | Use Firestore-backed FSM storage as fallback |
| Cloud Run cold start delays Telegram webhook response | Set `min-instances=1` for Telegram service |
| rundownai newsletter HTML structure changes | Use html2text + Claude Haiku extraction (resilient to DOM changes) |

---

## Resolved Decisions

| Decision | Choice |
|---|---|
| Canva path | Path A — `claude-agent-sdk` + Canva MCP (no Enterprise needed) |
| LLM billing | Direct Anthropic API key (`ANTHROPIC_API_KEY`) via LiteLLM — no Vertex AI |
| Instagram publishing | Manual export for now — `publisher.py` is a stub that exports Canva slides as PNG for manual posting |

## Open Questions

None — all decisions resolved. Agent decides slide count freely based on story depth.

---

## Key File References

- Architecture spec: `CLAUDE.md`
- Brainstorm: `docs/brainstorms/2026-03-12-insta-handler-manager-brainstorm.md`
- Canva template: ID `DAHDs0ivk0M` (4 pages: Cover / Teaser / Content / CTA)

## Dependencies (requirements.txt sketch)

```
google-adk
claude-agent-sdk==0.1.48
anthropic
aiogram==3.*
google-api-python-client
google-auth-oauthlib==1.3.0
google-auth-httplib2
google-cloud-firestore
html2text
beautifulsoup4
lxml
httpx
fastapi
uvicorn
python-dotenv
```
