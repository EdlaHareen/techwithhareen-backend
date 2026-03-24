# @techwithhareen Instagram Automation — The Complete Handbook

> Written for anyone who wants to understand this system from scratch.
> No coding experience needed. If you're 16 and curious, this is for you.

---

## Table of Contents

1. [What Does This System Actually Do?](#1-what-does-this-system-actually-do)
2. [The Big Picture — How It All Connects](#2-the-big-picture--how-it-all-connects)
3. [Every Tool Explained — What, Why, Why Not Others, How](#3-every-tool-explained)
   - [Python](#python--the-language-everything-is-written-in)
   - [FastAPI](#fastapi--the-web-server)
   - [Docker](#docker--the-shipping-container)
   - [Google Cloud Run](#google-cloud-run--the-computer-in-the-sky)
   - [Gmail API + Pub/Sub](#gmail-api--pubsub--the-email-listener)
   - [Anthropic Claude API](#anthropic-claude-api--the-ai-brain)
   - [Pillow](#pillow--the-graphic-designer)
   - [Google Cloud Storage](#google-cloud-storage--the-slide-warehouse)
   - [Serper.dev](#serperdev--the-image-searcher)
   - [Exa.ai + Tavily](#exaai--tavily--the-research-agents)
   - [Telegram + aiogram](#telegram--aiogram--the-notification-system)
   - [Redis / Memorystore](#redis--memorystore--the-sticky-note-board)
   - [Google Secret Manager](#google-secret-manager--the-safe)
   - [Firestore](#firestore--the-database)
   - [React + Vercel](#react--vercel--the-web-ui)
   - [Cloud Build](#cloud-build--the-robot-deployer)
   - [Cloud Scheduler](#cloud-scheduler--the-alarm-clock)
4. [The Two Pipelines — Step by Step](#4-the-two-pipelines--step-by-step)
5. [Why Not Use Simpler Tools?](#5-why-not-use-simpler-tools)
6. [Glossary — Words You Might Not Know](#6-glossary)

---

## 1. What Does This System Actually Do?

Imagine you run an Instagram page about Tech, AI, and Startups called **@techwithhareen**.

This system has **two ways** to create Instagram carousel posts:

### Way 1 — The Newsletter (v1, automatic)
Every morning, a newsletter called **rundownai** lands in your Gmail inbox. It's packed with 5–10 stories about what happened in the tech world overnight.

Normally you'd have to read it, design slides, write captions, and post — **hours every single morning**.

This system does all of that **automatically**, while you sleep:
- Detects when the newsletter arrives in Gmail
- Reads every story
- Creates beautiful carousel slides from scratch
- Writes the Instagram caption
- Double-checks quality
- Sends everything to your Telegram for approval
- Waits for you to tap Approve

### Way 2 — The Web UI (v2, on-demand)
Don't want to wait for the newsletter? Type any topic into a web app — "Claude Cowork", "AI chip shortage", anything — and the system:
- Searches the web via 3 different research tools simultaneously
- Picks the best angles
- Runs them through the same carousel + caption pipeline
- Shows you the posts in a browser-based approval queue

**Either way, you only have to do one thing: approve or reject.**

---

## 2. The Big Picture — How It All Connects

### v1 — Newsletter Pipeline
```
Gmail INBOX (rundownai arrives)
        │
        ▼
[Gmail Pub/Sub Watcher]  ← Google signals us instantly
        │
        ▼
[Content Fetcher Agent]  ← Claude reads the newsletter HTML
        │  extracts all stories as structured data
        │
        │ (per story, in parallel)
        ▼
[Post Creator Agent]  ← Serper finds image, Pillow draws 4-7 slides
        │
        ▼
[Caption Writer Agent]  ← Claude writes hook + summary + CTA + hashtags
        │
        ▼
[Post Analyzer Agent]  ← Claude checks quality (5 checks, 1 auto-retry)
        │
  Pass ─┤─ Fail → Skip + Telegram alert
        │
        ▼
[Telegram Bot]  ← Burst-sends all posts to your phone
        │
  Approve ─┤─ Reject
        │
        ▼
[Publisher]  ← (Manual export for now)
```

### v2 — Web UI Pipeline
```
Web UI: you type a topic
        │
        ▼
POST /api/v2/research
        │
        ▼
[Research Orchestrator]
 ┌──────────────────────────────┐
 │  [Exa]  [Tavily]  [Serper]  │  ← all 3 run in parallel
 └──────────────────────────────┘
   aggregate → deduplicate → Claude synthesises → Story objects
        │
        ▼
[Content Validator]  ← relevance + freshness + dedup checks
        │
        │ (per story, in parallel)
        ▼
[Same v1 pipeline: Post Creator → Caption → Analyzer]
        │
        ▼
Firestore /posts collection
        │
        ▼
Web UI approval queue  ← you approve/reject/edit caption in browser
        │
        ▼
[Publisher]  ← (Manual export for now)
```

---

## 3. Every Tool Explained

---

### Python — The Language Everything Is Written In

**What is it?**
Python is a programming language. Think of it like this: if the computer is a person who only speaks Japanese, Python is a translator that lets you give instructions in almost-plain English.

**Why Python?**
- It reads almost like English sentences. `if email.is_from("rundownai")` literally means "if the email is from rundownai."
- The largest collection of ready-made tools for AI, images, and APIs — all available in Python.
- Almost every AI company (Anthropic, Google, OpenAI) publishes their tools in Python first.

**Why not JavaScript, Java, or others?**
- JavaScript is mainly for websites. It *can* do this, but it's messier for AI/data work.
- Java is very verbose — you write 5x more code to do the same thing.
- Python is the industry standard for AI and automation.

---

### FastAPI — The Web Server

**What is it?**
A web server is a program that waits for requests and responds. FastAPI is a Python tool for building web servers — it's what makes our system reachable from the internet.

**Why FastAPI?**
- Fastest Python web server available
- Automatically validates incoming data formats
- Produces instant docs at `/docs`

**How is it used here?**
We have these "doors" (endpoints):

| Door | Who knocks | What happens |
|------|-----------|--------------|
| `POST /pubsub/push` | Google, when newsletter arrives | Triggers v1 pipeline |
| `POST /telegram/webhook` | Telegram, when you tap approve/reject | Records decision |
| `GET /healthz` | Google, every 30 seconds | Checks if alive |
| `POST /test/story` | You, during testing | Runs a fake story |
| `POST /api/v2/research` | Web UI, when you submit a topic | Starts v2 pipeline |
| `GET /api/v2/jobs/{id}` | Web UI polling | Returns job status |
| `GET /api/v2/posts` | Web UI | Lists all posts |
| `POST /api/v2/posts/{id}/approve` | Web UI | Approves a post |
| `POST /api/v2/posts/{id}/reject` | Web UI | Rejects a post |
| `PATCH /api/v2/posts/{id}/caption` | Web UI | Edits caption |

---

### Docker — The Shipping Container

**What is it?**
Docker packages everything — code, Python version, all libraries, fonts — into one box called a **container**. That container runs identically anywhere.

**Why Docker?**
- "Works on my machine" is the #1 cause of software problems. Docker eliminates it.
- Google Cloud Run requires Docker containers.
- If the server crashes, a new identical container starts automatically in seconds.

**How is it used here?**
The `Dockerfile` at the root is a recipe:
1. Start with a clean Python 3.12 computer
2. Install system tools (image processing libraries for Pillow)
3. Install all Python packages from `requirements.txt`
4. Copy our code + font files (`assets/fonts/`)
5. Set the startup command: run the web server on port 8080

---

### Google Cloud Run — The Computer in the Sky

**What is it?**
Cloud Run runs our Docker container on Google's servers. We don't manage hardware — Google handles uptime, scaling, restarts, and security patches.

**Why Cloud Run?**
- **Serverless**: Only pay when code actually runs
- **Auto-scaling**: Handles traffic spikes automatically
- **Managed**: No server administration
- **Integration**: Works seamlessly with Pub/Sub, Secret Manager, Firestore, etc.

**Service URL:** `https://insta-handler-371034138276.us-central1.run.app`

---

### Gmail API + Pub/Sub — The Email Listener

**What is it?**
**Gmail API**: Google's official way to read Gmail from code.

**Pub/Sub**: A messaging system. Gmail "rings the bell" whenever a newsletter arrives. Our server is listening and wakes up immediately — no polling needed.

**How is it used here?**
1. A setup script told Gmail: "when you get email from rundownai, signal our Pub/Sub topic"
2. Pub/Sub calls our Cloud Run service at `/pubsub/push`
3. Pipeline starts instantly

---

### Anthropic Claude API — The AI Brain

**What is it?**
Claude is Anthropic's AI. The API lets us use it from code — send a prompt, get a reply.

**Where is Claude used?**

| Agent | What Claude does |
|-------|-----------------|
| **Newsletter Parser** | Extracts stories from messy HTML into structured JSON |
| **Research Orchestrator** | Synthesises raw search results into Story objects |
| **Content Validator** | Checks relevance, deduplication across stories |
| **Caption Writer** | Writes hook, summary, CTA, hashtags |
| **Post Analyzer** | Checks design quality, hook strength, hashtag relevance |

**Which model?**
- `claude-haiku-4-5` for fast extraction tasks (parsing, validation)
- `claude-sonnet-4-6` for higher-quality writing tasks (captions, analysis)

---

### Pillow — The Graphic Designer

**What is it?**
Pillow is a Python library for creating images from code. Think of it as Photoshop controlled by code.

**What does it create?**
6–10+ slides per story at 1080×1350px (Instagram portrait 4:5):

| Slide | What it shows |
|-------|--------------|
| **Cover (Slide 1)** | Story image top half, "DO YOU KNOW" badge, bold headline with word-level accent highlights |
| **Hook Stat (Slide 2)** | The most shocking number huge in neon purple — e.g. "70%" with "OF DEVELOPERS USE AI DAILY" |
| **Content (Slide 3+)** | Numbered bullets: each has a punchy ALL CAPS headline + one explanation sentence below. Claude generates 8–12 stats per story; the renderer groups them 4 per slide automatically — so more content = more slides, no hard cap |
| **CTA (Last slide)** | "FOLLOW FOR MORE @techwithhareen" |

**Design system: "UncoverAI"**
- Pure black background (#000000)
- Neon periwinkle accent (#8075FF)
- Anton font (heavy condensed) for headlines
- Inter font for body text
- Word-level color highlighting on cover

**Why Pillow instead of Canva?**
Canva's API requires Enterprise ($$$) and automating it was fragile. Pillow creates pixel-perfect slides in under 2 seconds, programmatically, for free.

---

### Google Cloud Storage — The Slide Warehouse

**What is it?**
GCS is Google's file storage — like Google Drive for developers. We use it to store the carousel PNG files.

**Bucket:** `techwithhareen-carousel-assets`

**Why do we need this?**
After Pillow generates slides, they exist as files on the server at `/tmp/...`. These paths aren't accessible from the internet — the web UI can't display a `file://` URL from a remote server. We upload each PNG to GCS which gives it a public `https://` URL that any browser can load.

**Access:**
- Public read — anyone can view the images (needed for web UI previews and Telegram)
- Service account write — only our Cloud Run service can upload

**URL format:** `https://storage.googleapis.com/techwithhareen-carousel-assets/{design_id}/slide1.png`

---

### Serper.dev — The Image Searcher

**What is it?**
Serper searches Google Images from code. You send a query, it returns image URLs.

**Why do we need this?**
Each carousel's Cover slide is much more engaging with a real photo related to the story. Without it, the cover is just black text.

**Why Serper?**
- Google's official image API was deprecated in 2024 — it no longer exists
- Serper provides Google Image results as an API, reliably
- Also used in v2 as one of the 3 research sources (Google News)

---

### Exa.ai + Tavily — The Research Agents

**What are they?**
Two AI-powered web research APIs, used exclusively in the v2 pipeline:

**Exa.ai** — semantic/neural search. Instead of keyword matching, Exa understands *meaning*. Ask for "impact of AI on software jobs" and it finds relevant articles, Reddit threads, and thought pieces by concept, not just keywords.

**Tavily** — deep content extraction. Fetches the full body text of articles, not just snippets. Great for getting enough context for Claude to synthesise quality stories.

**Together with Serper (Google News), all three run in parallel** — the Research Orchestrator fires them all at once and aggregates results in ~10–20 seconds.

**Why three sources instead of one?**
- Exa finds conceptual/semantic content Serper misses
- Tavily gets full article text that Exa and Serper only have snippets for
- Serper finds breaking news that Exa hasn't indexed yet
- Together they give Claude much richer material to work with

---

### Telegram + aiogram — The Notification System

**What is it?**
Telegram is a messaging app with excellent developer support. aiogram is a Python library for building Telegram bots.

**Why Telegram for approvals?**
- **Instant**: Push notification to your phone when slides are ready
- **Visual**: Supports image albums — you see all slides right in chat
- **Inline buttons**: One-tap "Approve ✅" / "Reject ❌" buttons
- **Reliable and free**

**How is it used here?**
1. After pipeline completes, sends all passing posts to your Telegram in a burst
2. Each message: slide album + caption + Approve/Reject buttons
3. Your tap → Telegram calls `/telegram/webhook` → we look up story ID from Redis → publisher handles it

In **v2**, Telegram is opt-in per post (the Web UI is the primary approval channel).

---

### Redis / Memorystore — The Sticky Note Board

**What is it?**
Redis is an ultra-fast in-memory database. Think of it as a giant sticky note board any part of the system can read/write to instantly.

**Why do we need it?**
When you tap "Approve" in Telegram, how does the server know *which story* you approved? The story ID must be stored between:
- When we sent the Telegram message
- When you tapped the button (could be hours later)

Redis stores this mapping: `{button_callback_id → story_id}`

**Why not store it in the app's memory?**
If Cloud Run runs multiple instances, each has its own memory. Redis is shared across all instances.

---

### Google Secret Manager — The Safe

**What is it?**
A secure vault where we store API keys and tokens. Only our Cloud Run service can access what's inside.

**What secrets does it hold?**

| Secret | What it is |
|--------|-----------|
| `anthropic-api-key` | Key to use Claude AI |
| `telegram-bot-token` | Key to send Telegram messages |
| `telegram-owner-chat-id` | Your personal Telegram ID |
| `serper-api-key` | Key to search Google Images + News |
| `exa-api-key` | Key for Exa semantic search (v2) |
| `tavily-api-key` | Key for Tavily content extraction (v2) |
| `cors-origins` | Allowed frontend URL (Vercel) |
| `gmail-oauth-token` | Permission to read your Gmail |
| `gmail-oauth-credentials` | App identity for Gmail |

**Why Secret Manager?**
Putting API keys in code is one of the most common and costly mistakes in software. Keys in code end up in Git history and get stolen by bots that scan GitHub. Secret Manager means keys never appear in code or logs.

---

### Firestore — The Database

**What is it?**
Firestore is Google's NoSQL cloud database. Stores data as documents (like JSON files) in collections.

**What do we use it for?**

In **v1**: logs failures only — stories that couldn't be fixed after 1 retry.

In **v2**: much more:

| Collection | What it stores |
|------------|---------------|
| `/jobs` | Research jobs (topic, status: researching→creating→analyzing→ready, story IDs) |
| `/posts` | Every processed post (slides URLs, caption, status: pending/approved/rejected) |
| `/failed_jobs` | Stories that failed quality checks |
| `/gmail_state` | Gmail historyId cursor (so we don't reprocess old emails) |

The Web UI reads from `/jobs` and `/posts` to show the approval queue and history.

---

### React + Vercel — The Web UI

**What is it?**
**React** is a JavaScript library for building web interfaces. **Vercel** is a hosting platform that deploys React apps instantly from GitHub.

**Frontend URL:** `https://techwithhareen-web.vercel.app`

**Why a web UI (v2)?**
The newsletter pipeline (v1) only runs when rundownai arrives. The Web UI lets you create posts on-demand — any topic, any time — without waiting for a newsletter.

**What the Web UI does:**

| Page | Purpose |
|------|---------|
| **Dashboard** | Shows all pending posts waiting for approval |
| **New Post** | Type a topic → watch pipeline status in real-time → review posts |
| **History** | All approved and rejected posts with dates |

Each post card shows:
- Slide preview with left/right navigation
- Caption (editable inline)
- Approve / Reject buttons
- "Also send to Telegram" toggle (opt-in)

**Why Vercel?**
- Zero configuration — connects to GitHub, auto-deploys on every push
- Free tier is more than sufficient
- Global CDN — fast worldwide

**Why a separate frontend repo?**
Keeps frontend and backend deployments independent. A bug fix in the backend doesn't require redeploying the frontend, and vice versa.

**Two repos, two jobs:**

| Repo | What's in it | Deployed to |
|------|-------------|-------------|
| `github.com/EdlaHareen/techwithhareen-backend` | All AI agents, Pillow renderer, Telegram bot, Firestore/GCS/Gmail integrations, FastAPI server | Google Cloud Run |
| `github.com/EdlaHareen/techwithhareen-web` | React UI — Dashboard, New Post, History, PostCard, API client | Vercel |

They talk to each other over HTTP — the frontend calls the backend's `/api/v2/...` endpoints. The backend does all the intelligence; the frontend is purely the approval interface.

**Important config files in the frontend repo:**
- `vercel.json` — rewrites all paths to `index.html` so hard-refreshing on `/history` or `/new` doesn't return 404
- `.npmrc` — sets `legacy-peer-deps=true` to resolve peer dependency conflict between `@tailwindcss/vite` and Vite 8

---

### Cloud Build — The Robot Deployer

**What is it?**
Cloud Build is Google's CI/CD service. When we run the deploy command, it:
1. Takes our code and Dockerfile
2. Builds the Docker container on Google's servers (not your laptop)
3. Pushes it to Artifact Registry (Google's image warehouse)
4. Deploys the new image to Cloud Run

**Deploy command:**
```bash
~/google-cloud-sdk/bin/gcloud builds submit \
  --config=infra/cloudbuild.yaml \
  --project=techwithhareen \
  --substitutions=COMMIT_SHA=$(git rev-parse HEAD)
```

**Config:** `infra/cloudbuild.yaml`

---

### Cloud Scheduler — The Alarm Clock

**What is it?**
Cloud Scheduler runs tasks on a schedule — like a cron job.

**Why do we need it?**
Gmail's "watch" feature (what notifies us when emails arrive) expires every 7 days. Cloud Scheduler calls our `/renew-watch` endpoint daily at 6 AM UTC, renewing it before it expires.

---

## 4. The Two Pipelines — Step by Step

### v1 — Newsletter Pipeline

**Step 1: Email detected (< 1 second)**
```
rundownai sends email → Gmail detects it → Pub/Sub signals Cloud Run
→ POST /pubsub/push → pipeline starts
```

**Step 2: Email reading (2–3 seconds)**
```
Gmail API returns raw HTML → Claude extracts 7–10 stories as JSON
Each story: headline, summary, key stats, hook number, image query
```

**Step 3: Per-story processing (parallel)**
```
For each story simultaneously:
  → Serper searches for a relevant image
  → Claude writes the Instagram caption (hook + summary + CTA + hashtags)
```

**Step 4: Carousel creation (1–2 seconds)**
```
Pillow draws 6–10+ PNG slides:
  Slide 1: Story image + "DO YOU KNOW" + bold headline
  Slide 2: Hook stat (e.g. "70%") huge in purple + "SWIPE TO FIND OUT WHY"
  Slide 3+: Numbered stats, each with headline + explanation sentence
  Last: "FOLLOW FOR MORE @techwithhareen"
→ Each slide uploaded to GCS → public https:// URL
```

**Step 5: Quality check (3–5 seconds)**
```
Claude checks:
  ✅ Cover hook clear and strong?
  ✅ Brand handle present throughout?
  ✅ Hashtags present and relevant?
  ✅ Caption well-formatted?
  ✅ CTA on last slide?

Fail → 1 automatic retry → still failing → skip + Telegram alert
```

**Step 6: Telegram delivery**
```
For each passing story:
  → Send slide album + caption + [✅ Approve] [❌ Reject] to your Telegram
  → Story ID stored in Redis linked to the buttons
```

**Step 7: Approval**
```
You tap ✅ → Publisher logs approval → you manually post to Instagram
```

**Total time: ~30–60 seconds from email to Telegram notification.**

---

### v2 — Web UI Pipeline

**Step 1: You type a topic**
```
Web UI → POST /api/v2/research {"topic": "Claude Cowork"}
→ Returns job_id immediately (background task starts)
```

**Step 2: Research (parallel, ~10–20 seconds)**
```
[Exa]    → semantic/neural search → 5 articles by concept
[Tavily] → deep content extraction → 5 articles with full body text
[Serper] → Google News → 5 current news articles
→ Aggregate → deduplicate by URL → Claude synthesises → 1–5 Story objects
```

**Step 3: Validation**
```
Content Validator checks each story:
  → Relevant to the topic? (LLM check)
  → Less than 30 days old? (date check)
  → Duplicate angle of another story? (LLM dedup)
→ Passing stories continue; dropped stories logged
```

**Step 4: Same carousel + caption + analysis pipeline as v1**

**Step 5: Posts appear in Web UI**
```
Web UI polls GET /api/v2/jobs/{job_id} every 3 seconds
Status: researching → creating → analyzing → ready
→ Posts appear in Dashboard with slide previews from GCS
```

**Step 6: Browser approval**
```
You see slide carousel preview + caption in browser
Edit caption inline if needed
Click Approve → publisher handles it
Optional: "Also send to Telegram" toggle
```

---

## 5. Why Not Use Simpler Tools?

| Tool | Why We Didn't Use It |
|------|---------------------|
| **Zapier** | Can't generate custom images or run creative AI pipelines |
| **Make.com** | Same limitations — great for data routing, not slide design |
| **Buffer/Later** | Scheduling only, can't generate content |
| **Canva API** | Enterprise-only ($$$), too slow and fragile for automation |
| **n8n** | Good for routing, but image generation still requires custom code |

The core of what we're doing — **AI-powered content creation + custom image generation + multi-source research** — requires real code. No-code tools aren't there yet.

---

## 6. Glossary

| Term | Plain English Meaning |
|------|-----------------------|
| **API** | A way for two pieces of software to talk to each other. Like a waiter taking your order to the kitchen. |
| **Agent** | A piece of code that does one specific job, possibly using AI |
| **Endpoint** | A "door" on a web server that receives requests |
| **Container** | A self-contained package of code + everything it needs to run |
| **Cloud** | Someone else's computer that you rent |
| **Serverless** | Cloud where you don't manage a server — just give Google your code |
| **SDK** | Software Development Kit — a toolbox of pre-written code |
| **JSON** | Structured data format: `{"name": "OpenAI", "raised": "$6B"}` |
| **Webhook** | A URL that another service calls when something happens |
| **Pub/Sub** | Messaging system: one service publishes, another subscribes to receive |
| **GCS** | Google Cloud Storage — file storage with public URLs |
| **CI/CD** | Automated build and deploy when code changes |
| **Redis** | Ultra-fast in-memory database for temporary state |
| **Firestore** | Google's NoSQL document database |
| **Cron/Scheduler** | Run code on a schedule ("every day at 6am") |
| **Carousel** | Instagram post with multiple swipeable images |
| **Pipeline** | Series of steps that process data in order, like an assembly line |
| **CTA** | Call To Action — "Follow for more!" |
| **Hook** | The first line of a caption designed to grab attention |
| **Neural search** | Search by meaning/concept rather than exact keywords |
| **Semantic search** | Same as neural search — finds related content even without matching words |
| **Vignette** | Gradient that fades the edges of an image to black |
| **Revision** | A version of our Cloud Run service — every deploy creates a new one |
| **Secret** | A sensitive value (API key, password) stored securely, never in code |

---

*Built for @techwithhareen — AI, Tech & Startups*
*Last updated: March 2026*
