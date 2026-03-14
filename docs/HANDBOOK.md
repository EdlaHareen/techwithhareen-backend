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
   - [Serper.dev](#serperdev--the-image-searcher)
   - [Telegram + aiogram](#telegram--aiogram--the-notification-system)
   - [Redis / Memorystore](#redis--memorystore--the-sticky-note-board)
   - [Google Secret Manager](#google-secret-manager--the-safe)
   - [Terraform](#terraform--the-blueprint)
   - [Cloud Build](#cloud-build--the-robot-deployer)
   - [Cloud Scheduler](#cloud-scheduler--the-alarm-clock)
   - [Firestore](#firestore--the-failure-logbook)
   - [Google ADK](#google-adk--the-task-manager)
4. [The Pipeline — Step by Step](#4-the-pipeline--step-by-step)
5. [Why Not Use Simpler Tools?](#5-why-not-use-simpler-tools)
6. [Glossary — Words You Might Not Know](#6-glossary)

---

## 1. What Does This System Actually Do?

Imagine you run an Instagram page about Tech, AI, and Startups called **@techwithhareen**.

Every morning, a newsletter called **rundownai** lands in your Gmail inbox. It's packed with 5–10 stories about what happened in the tech world overnight — things like "OpenAI launched a new AI" or "A startup just raised $500 million."

Normally, if you wanted to post about each story, you'd have to:
1. Read the newsletter
2. Pick the best stories
3. Design slide-by-slide carousel images in Canva
4. Write a catchy Instagram caption
5. Check if everything looks good
6. Post it

That takes **hours every single morning**.

This system does all of that **automatically**, while you sleep. It:
- Detects when the newsletter arrives in your Gmail
- Reads every story
- Creates beautiful carousel post images from scratch
- Writes the Instagram caption
- Double-checks the quality
- Sends everything to your Telegram phone app for your approval
- Waits for you to say "yes" or "no"
- Logs everything that goes wrong so nothing gets lost

**You only have to do one thing: tap Approve on your phone.**

---

## 2. The Big Picture — How It All Connects

Think of the whole system like a factory assembly line. Each worker (called an **agent**) does one specific job and passes the work to the next person.

```
GMAIL INBOX
    │
    │  ← Email arrives from rundownai
    ▼
[WATCHER]  ← Google notices the email and sends a signal
    │
    ▼
[READER AGENT]  ← Opens the email, reads all the stories
    │
    │  (For each story, separately and simultaneously)
    ├──────────────────────────────────────────┐
    ▼                                          ▼
[IMAGE SEARCHER]  ← Finds a           [CAPTION WRITER] ← Writes the
  relevant photo                         Instagram text
    │                                          │
    ▼                                          │
[SLIDE DESIGNER]  ← Draws 4 slide images      │
    │                                          │
    └──────────────┬───────────────────────────┘
                   ▼
          [QUALITY CHECKER]  ← Reviews everything
                   │
          Pass? ───┼─── Fail? ──► Skip + notify you
                   │
                   ▼
         [TELEGRAM SENDER]  ← Sends to your phone
                   │
         Approve ──┼── Reject
                   │
                   ▼
         [PUBLISHER]  ← (Manual for now) Saves slides
```

Each box in this diagram is a piece of code we wrote. Together they form a **multi-agent system** — meaning multiple specialised workers, each expert in their one job.

---

## 3. Every Tool Explained

---

### Python — The Language Everything Is Written In

**What is it?**
Python is a programming language. Think of it like this: if the computer is a person who only speaks Japanese, Python is a translator that lets you give instructions in almost-plain English.

**Why Python?**
- It reads almost like English sentences. `if email.is_from("rundownai")` literally means "if the email is from rundownai."
- The largest collection of ready-made tools (called "libraries") for AI, images, APIs — all available in Python.
- Almost every AI company (Anthropic, Google, OpenAI) publishes their tools in Python first.

**Why not JavaScript, Java, or others?**
- JavaScript is mainly for websites. It *can* do this, but it's messier for AI/data work.
- Java is very powerful but extremely verbose — you write 5x more code to do the same thing.
- Python is the industry standard for AI and automation. That's just where the ecosystem lives.

**How is it used here?**
Every single file ending in `.py` in this project is Python. The entire system — reading emails, drawing images, talking to AI, sending Telegram messages — is all Python.

---

### FastAPI — The Web Server

**What is it?**
A web server is a program that sits and waits for someone to knock on its door (called making a "request") and then responds.

FastAPI is a Python tool for building web servers. It's what makes our system "reachable" from the internet — so Google can send us a signal when an email arrives, and so Telegram can send us your approval tap.

**Why FastAPI?**
- It's the fastest Python web server available (hence "Fast" in the name).
- It automatically checks that incoming data is in the right format, so we don't have to write those checks ourselves.
- It produces instant documentation of all our "doors" (called endpoints) at `/docs`.

**Why not Flask or Django?**
- **Flask** is fine but older and slower. FastAPI does in 3 lines what Flask does in 10.
- **Django** is a massive framework built for full websites with databases, user accounts, etc. We don't need any of that — we just need a few simple doors. Django would be like buying a mansion when you need a doorbell.

**How is it used here?**
We have 4 "doors" (endpoints):

| Door | Who knocks | What happens |
|------|-----------|--------------|
| `POST /pubsub/push` | Google, when new email arrives | Triggers the whole pipeline |
| `POST /telegram/webhook` | Telegram, when you tap approve/reject | Records your decision |
| `GET /healthz` | Google, every 30 seconds | Just checks "are you alive?" |
| `POST /test/story` | You, during testing | Runs a fake story through the whole pipeline |

---

### Docker — The Shipping Container

**What is it?**
Imagine you build a Lego creation at home and want to send it to a friend. If you just ship the pieces, they might not have the same pieces or the instructions. If you ship the whole box — pieces, instructions, even the desk it was built on — your friend can recreate it exactly.

Docker does this for software. It packages **everything** — the code, the Python version, all the libraries, even the fonts for our slides — into one box called a **container**. That container runs identically anywhere.

**Why Docker?**
- "Works on my machine" is the #1 cause of software problems. Docker eliminates it.
- Google Cloud Run (where we host) requires Docker containers — it's how it knows what to run.
- If the server crashes, a new identical container starts automatically in seconds.

**Why not just run Python directly?**
You could, but then you'd have to manually install Python 3.12, every library, the fonts, the right version of each dependency — on every machine. One mismatch and everything breaks. Docker makes it a one-step process.

**How is it used here?**
The `Dockerfile` at the root of the project is a recipe:
1. Start with a clean Python 3.12 computer
2. Install system tools (image processing libraries)
3. Install all Python packages
4. Copy our code + fonts
5. Set the startup command: "run the web server on port 8080"

When we deploy, this recipe gets "baked" into a container image and sent to Google's servers.

---

### Google Cloud Run — The Computer in the Sky

**What is it?**
Cloud Run is Google's service for running our Docker container on their computers. Instead of buying and managing our own server, we rent computing power from Google and they handle everything — keeping it running, scaling it up if traffic spikes, restarting it if it crashes.

**Why Cloud Run?**
- **Serverless**: We don't pay for a server sitting idle. We only pay when our code actually runs. For a once-a-day newsletter pipeline, this is dramatically cheaper.
- **Auto-scaling**: If somehow 100 newsletters came in at once, Cloud Run would automatically spin up 100 copies of our container.
- **Managed**: Google handles security patches, restarts, and hardware failures. We never SSH into a server.
- **Integration**: Works seamlessly with every other Google service we use (Pub/Sub, Secret Manager, Redis, etc.).

**Why not AWS Lambda, Heroku, or a VPS?**
- **AWS Lambda** is similar but has a 15-minute time limit and 10MB file size limit. Our image generation can take longer and our container with fonts is large.
- **Heroku** is simple but expensive for always-on services and doesn't integrate with Google's ecosystem.
- **VPS (Virtual Private Server)** like DigitalOcean: you manage everything yourself. You're responsible for updates, crashes, security. We're a one-person operation — we don't want that burden.

**How is it used here?**
Our service runs 24/7 (`min_instance_count = 1` so it never goes to sleep). When Google sends a Pub/Sub signal or Telegram sends your approval, the Cloud Run service receives it instantly because it's always on.

---

### Gmail API + Pub/Sub — The Email Listener

**What is it?**
Two separate things that work together:

**Gmail API**: Google's official way to read and interact with Gmail from code. Like having a robot assistant who can open your Gmail, read emails, and hand them to you.

**Pub/Sub** (short for Publish/Subscribe): A messaging system. Think of it like a notification bell. Gmail "rings the bell" (publishes a message) whenever a new email from `news@daily.therundown.ai` arrives. Our server is "listening to the bell" (subscribed) and wakes up immediately.

**Why this combination?**
Without Pub/Sub, we'd have to constantly ask Gmail "any new emails? any new emails? any new emails?" every few seconds — this is called polling and it wastes resources. With Pub/Sub, Gmail tells US the moment something arrives. It's the difference between checking your mailbox every 5 minutes vs. having the mailman ring your doorbell.

**Why Gmail specifically?**
Because rundownai is delivered to Gmail. We go where the data is.

**Why not just forward emails to a webhook directly?**
Gmail doesn't support that natively. The Gmail API + Pub/Sub is Google's official way to build real-time email triggers.

**How is it used here?**
1. We ran a setup script (`scripts/setup_gmail_watch.py`) once, which told Gmail: "whenever you get a new email matching rundownai's address, send a signal to our Pub/Sub topic"
2. That Pub/Sub topic is connected to our Cloud Run service's `/pubsub/push` door
3. When the newsletter arrives → Gmail signals Pub/Sub → Pub/Sub calls our server → Pipeline starts

The Gmail API credentials (the "keys" to access the inbox) are stored securely and renewed automatically.

---

### Anthropic Claude API — The AI Brain

**What is it?**
Claude is Anthropic's AI — the same family of AI you're talking to right now. The "API" is a way to use Claude from code, like sending it a message and getting a reply, but programmatically.

**Where is Claude used in our system?**

We use it in **three places**:

| Agent | What Claude does |
|-------|-----------------|
| **Newsletter Parser** | Reads the HTML email and extracts each story: headline, summary, stats, the most shocking number |
| **Caption Writer** | Writes the Instagram caption — hook line, summary, CTA, hashtags |
| **Post Analyzer** | Checks the final post quality: is the design consistent? Is the hook strong? Are hashtags relevant? |

**Why Claude specifically?**
- Claude is particularly good at structured data extraction — telling it "read this messy HTML and give me a JSON list of stories" and getting exactly that back, reliably.
- Claude is also strong at writing in a specific style (Instagram captions need energy, hooks, hashtags).
- Anthropic provides a clean Python library (`anthropic`) that's a joy to use.

**Why not GPT-4, Gemini, or a local model?**
- **GPT-4**: Also works well, but we're already deeply in the Anthropic/Claude ecosystem (you're using Claude Code right now). Consistency matters.
- **Gemini**: Google's AI, technically accessible here too, but Claude consistently outperforms for creative writing and structured extraction in our testing.
- **Local models (running AI on our own server)**: Would require expensive GPU hardware or very slow inference. Cloud APIs give us the best models instantly for pennies per request.

**How is it used here?**
We send Claude a prompt like:
> "Here is the HTML of a newsletter. Extract every story as a JSON array. For each story include: headline, summary, key stats, and the single most shocking number."

Claude replies with clean, structured data that we can immediately use.

---

### Pillow — The Graphic Designer

**What is it?**
Pillow is a Python library for creating and editing images. Think of it as Photoshop, but controlled by code instead of a human clicking.

**What does it create?**
Four slides per story at 1080×1350 pixels (Instagram's portrait format):

| Slide | What it shows |
|-------|--------------|
| **Cover (Slide 1)** | Story image at top, "DO YOU KNOW" pill badge, bold headline in huge text |
| **Hook Stat (Slide 2)** | The most shocking number from the story, huge, in bright purple. E.g. "10x" with "CHEAPER THAN GPT-4 PER TOKEN" below it |
| **Content (Slide 3)** | Numbered bullet points with the key stats/facts |
| **CTA (Slide 4)** | "FOLLOW FOR MORE @techwithhareen" call-to-action |

**Design style used:** "UncoverAI" style:
- Pure black background
- Neon purple accent color (#8075FF)
- Anton font (heavy condensed) for headlines
- Inter font for body text
- Word-level color highlighting (some words accent, some white)

**Why Pillow instead of Canva?**
Originally we planned to use Canva (the design tool). But Canva's API requires an Enterprise account ($$$), and automating it via their MCP tool was fragile and slow. Pillow lets us create pixel-perfect slides in under 2 seconds, fully programmatically, for free.

**Why not other image libraries?**
- **OpenCV**: Primarily for computer vision (detecting faces, etc.), not ideal for graphic design.
- **Cairo/Wand**: More complex setup, Pillow does everything we need simply.
- **HTML/CSS to image converters**: Slower, requires a headless browser, adds complexity.

**How is it used here?**
The file `src/utils/carousel_renderer.py` is our designer. It:
1. Creates a black 1080×1350 pixel canvas
2. Downloads the story image from the web
3. Places the image in the top half with a gradient fade to black
4. Loads the Anton/Inter fonts from `assets/fonts/`
5. Draws text with word-level color control
6. Saves 4 PNG files to `/tmp/carousel_<id>/slide1.png` etc.

---

### Serper.dev — The Image Searcher

**What is it?**
Serper is a service that lets you search Google Images from code. You send it a search query, it sends back image URLs.

**Why do we need this?**
Each carousel's Cover slide looks much better with a real photo related to the story (e.g., a story about OpenAI → a photo of Sam Altman or the ChatGPT logo). Without this, the cover would just be a black slide with text — less engaging.

**Why Serper specifically?**
- Google's own official image search API was **deprecated** (shut down) in 2024. It no longer exists.
- Serper reverse-engineers Google Image search results and provides them as an API.
- It's the most reliable Google Images API available, used by thousands of developers.
- It's fast (under 1 second) and affordable ($50/month for our volume).

**Why not Bing Image Search, Unsplash, or Pexels?**
- **Bing Image Search**: Works, but results are lower quality for tech news topics.
- **Unsplash/Pexels**: Stock photo libraries. Great for generic images but they don't have news photos (e.g., no photo of a specific startup's funding round).
- **Scraping Google directly**: Against Google's terms of service and gets blocked quickly.

**How is it used here?**
In `src/agents/post_creator/image_fetcher.py`:
1. Claude first generates the best search query for the story (e.g., "OpenAI GPT-5 artificial intelligence")
2. We send that query to Serper
3. Serper returns 10 candidate image URLs
4. We check each URL is actually reachable (some are broken)
5. We return the first valid one
6. Pillow downloads it and composites it onto the slide

---

### Telegram + aiogram — The Notification System

**What is it?**
Telegram is a messaging app (like WhatsApp but faster and with better developer support). aiogram is a Python library for building Telegram bots.

**Why Telegram for approvals?**
This is the human-in-the-loop step — before anything goes live on Instagram, you (the owner) must approve it. Telegram is perfect because:
- **Instant**: Push notification to your phone the moment slides are ready
- **Visual**: Telegram supports sending image albums, so you see all 4 slides right there in the chat
- **Inline buttons**: Telegram supports "Approve ✅" / "Reject ❌" buttons right in the message — one tap to respond
- **Reliable**: Telegram rarely goes down. WhatsApp Business API requires a business account, is expensive, and limits what you can send.

**Why not email, WhatsApp, or a web dashboard?**
- **Email**: No inline buttons, clunky for approvals, easy to miss
- **WhatsApp**: Requires Meta business account, limited bot capabilities, not developer-friendly
- **Web dashboard**: We'd have to build a whole website with login, sessions, database — massive extra work for something Telegram does out-of-the-box in 50 lines of code

**Why aiogram specifically?**
- It's the most popular async Telegram library for Python (40k+ GitHub stars)
- It handles complex bot state (remembering which story each approval button refers to) elegantly
- It integrates with Redis for storing that state

**How is it used here?**
The Telegram bot (`src/agents/telegram_bot/bot.py`):
1. After all stories are processed, sends a burst of messages to your Telegram
2. Each message contains: the 4 slide images as an album + the caption text + two buttons: ✅ Approve / ❌ Reject
3. When you tap ✅, Telegram calls our `/telegram/webhook` endpoint
4. We look up which story that button belonged to (using Redis)
5. We call the publisher to log it as approved

---

### Redis / Memorystore — The Sticky Note Board

**What is it?**
Redis is an ultra-fast in-memory database. "In-memory" means it stores data in RAM (the computer's fast short-term memory) rather than on disk. Think of it as a giant sticky note board that any part of our system can read and write to instantly.

**Why do we need it?**
The Telegram bot has a problem: when you tap "Approve" on a message, Telegram sends our server a tap event — but how does the server know *which story* you approved? The story ID needs to be stored somewhere between:
- When we sent the message
- When you tapped the button

This is called **state** — remembering context between two separate events. Redis stores this state.

**Why Redis specifically?**
- It's extremely fast (microseconds per read/write)
- It's the standard for storing bot/session state — aiogram has built-in Redis support
- Google Memorystore is the managed Redis service on GCP, so we don't maintain it ourselves

**Why not just store it in the code's memory?**
When Cloud Run scales from 1 instance to multiple (if many requests come in), each instance has its own memory. If the request to send messages went to instance A, but your tap came back to instance B, instance B wouldn't have the story ID in its memory. Redis is shared across all instances.

**Why not a full database like PostgreSQL?**
For temporary state like "which button maps to which story," Redis is perfect — it's orders of magnitude faster and simpler. We only use it as a scratchpad, not for permanent records.

**How is it used here?**
When we send a Telegram message with an "Approve" button, we store a mapping in Redis:
```
key:   "approve_button_callback_id_abc123"
value: "story_id_256e0c8f"
```
When you tap Approve, the callback ID comes back, we look it up in Redis, get the story ID, and know exactly which story to publish.

---

### Google Secret Manager — The Safe

**What is it?**
A secure vault in Google Cloud where we store sensitive information — API keys, passwords, tokens. Only our Cloud Run service (with the right permissions) can access what's inside.

**What secrets does it hold?**
| Secret | What it is |
|--------|-----------|
| `anthropic-api-key` | Key to use Claude AI |
| `telegram-bot-token` | Key to send Telegram messages |
| `telegram-owner-chat-id` | Your personal Telegram ID |
| `serper-api-key` | Key to search Google Images |
| `gmail-oauth-token` | Permission slip to read your Gmail |
| `gmail-oauth-credentials` | The app's identity for Gmail |

**Why Secret Manager instead of just putting them in the code?**
Putting API keys in code is one of the most common and costly mistakes in software. Keys in code end up in Git history, shared with teammates, accidentally uploaded to GitHub — and then get stolen by bots that constantly scan GitHub for exposed credentials. Companies have paid millions in cloud bills after a key was exposed.

Secret Manager means:
- Keys never appear in code
- Keys never appear in logs
- Only specific services with specific permissions can read them
- Every access is logged — you can see who read what and when

**Why not `.env` files or environment variables directly?**
`.env` files are fine for local development (and we use them locally) but they can't be used safely in Cloud Run — you'd have to paste secrets into the Cloud Run configuration where they could be seen by anyone with console access. Secret Manager injects them securely at runtime.

---

### Terraform — The Blueprint

**What is it?**
Terraform is a tool where you describe your cloud infrastructure in text files, and it creates/updates everything automatically.

Instead of clicking through 47 screens in the Google Cloud Console to set up Cloud Run, Redis, Pub/Sub, service accounts, permissions — you write it once in a `.tf` file and Terraform does all the clicking for you.

**Why Terraform?**
- **Reproducible**: If you had to rebuild from scratch (disaster recovery), you just run `terraform apply` and everything is recreated identically.
- **Version controlled**: Infrastructure changes are tracked in Git just like code changes.
- **Self-documenting**: The `.tf` files are the documentation of exactly what exists in your cloud account.

**Why not just click through the Google Cloud Console?**
Clicking through the console is:
- Not repeatable (you can't "undo" a mistake or rebuild easily)
- Not documented (future-you won't remember what you clicked)
- Error-prone (miss one checkbox and things break mysteriously)

**Why not Pulumi or AWS CloudFormation?**
- **CloudFormation**: Only works with AWS. We're on Google Cloud.
- **Pulumi**: Similar to Terraform, slightly newer. Terraform has a larger community and more Google Cloud examples. Either would work, but Terraform is the industry standard.

**How is it used here?**
`infra/terraform/` contains files describing:
- The Cloud Run service (what image to run, how much memory, which secrets to inject)
- The Redis instance
- The Pub/Sub topic
- Service accounts and their permissions
- Cloud Scheduler job for Gmail watch renewal

Run `terraform apply` and all of this is created/updated in Google Cloud automatically.

---

### Cloud Build — The Robot Deployer

**What is it?**
Cloud Build is Google's CI/CD service. CI/CD stands for Continuous Integration / Continuous Deployment — fancy words for "automatically build and deploy when code changes."

When we push code, Cloud Build:
1. Takes our code and Dockerfile
2. Builds the Docker container image
3. Pushes the image to Google's container registry (like a warehouse for Docker images)
4. Deploys the new image to Cloud Run

**Why Cloud Build?**
- It runs on Google's servers, not your laptop — so your computer doesn't need to be on
- It's integrated with the rest of our Google Cloud setup
- It keeps a history of every build (easy to see what changed and when)

**Why not GitHub Actions, CircleCI, or building locally?**
- **GitHub Actions**: Works great and is a common alternative. We chose Cloud Build because everything else is already in Google Cloud — keeping it in one ecosystem reduces complexity.
- **CircleCI**: Another option, but it's a third-party service. More moving parts.
- **Building locally**: You have to remember to do it. Automation is more reliable than humans.

**How is it used here?**
`infra/cloudbuild.yaml` defines three steps:
1. **Build** the Docker image
2. **Push** it to Artifact Registry (Google's image warehouse)
3. **Deploy** to Cloud Run with the new image

The `deploy.sh` script calls Cloud Build as part of the full deployment process.

---

### Cloud Scheduler — The Alarm Clock

**What is it?**
Cloud Scheduler lets you run tasks on a schedule — like a cron job or an alarm clock for your server.

**Why do we need it?**
Gmail's "watch" feature (the thing that notifies us when new emails arrive) expires every 7 days. If we don't renew it, emails stop triggering our pipeline.

Cloud Scheduler calls our `/renew-watch` endpoint automatically every day at 6 AM UTC, renewing the Gmail watch before it expires.

**Why not handle this inside the application?**
We could write code to renew it internally, but Cloud Scheduler is:
- Zero code
- Reliable (Google manages it)
- Observable (you can see in the console if it ran)
- Decoupled (the scheduler doesn't know or care about our app internals)

---

### Firestore — The Failure Logbook

**What is it?**
Firestore is Google's NoSQL cloud database. It stores data as documents (like JSON files) organized in collections.

**What do we use it for?**
In this system, we use it minimally — only for logging **failures**. When a story fails quality checks (bad design, weak hook, no hashtags) and can't be fixed, we record:
- The story headline
- The reason it failed
- When it happened

**Why Firestore for this?**
- It's already available in our Google Cloud project
- Storing a few failure records doesn't need a complex relational database
- Firestore handles the storage, replication, and backups automatically

**Why not a full relational database like PostgreSQL?**
For simple key-value logging of failures, a full relational database is massive overkill. Firestore is serverless (no server to manage) and scales automatically.

**Important:** We deliberately keep this minimal. We only log failures — not every story, not every run. This keeps things simple and prevents data bloat.

---

### Google ADK — The Task Manager

**What is it?**
Google ADK (Agent Development Kit) is a framework from Google for building multi-agent systems — systems where multiple AI "workers" coordinate to complete a task.

**Why do we have multiple agents instead of one?**
Because each agent specialises in exactly one job:

| Agent | One Job |
|-------|---------|
| Content Fetcher | Read emails, extract stories |
| Post Creator | Create the carousel images |
| Caption Writer | Write Instagram captions |
| Post Analyzer | Check quality |
| Telegram Bot | Handle approvals |

This is like a real company: you have a copywriter, a designer, a quality reviewer — not one person doing everything. Each agent can be:
- Tested independently
- Replaced without touching others
- Run in parallel for different stories

**Why Google ADK specifically?**
- It provides `ParallelAgent` which lets us process 5 stories simultaneously (instead of one at a time) — so the whole pipeline takes the same time as processing one story.
- It integrates with Google Cloud (logging, tracing).
- It's well-maintained by Google.

**Why not LangChain, LlamaIndex, or AutoGen?**
- **LangChain**: Very popular but has a reputation for being overly complex with many abstraction layers. Simple operations get buried under chains and callbacks.
- **LlamaIndex**: Primarily focused on document search (RAG). Not ideal for our use case.
- **AutoGen**: Microsoft's framework. Less Google Cloud integration.
- **Bare Anthropic API**: We actually do use the Anthropic API directly for the Claude calls — Google ADK is only for orchestrating the agents, not for the AI itself.

---

## 4. The Pipeline — Step by Step

Let's trace exactly what happens from the moment the newsletter arrives:

### Step 1: Email Detected (< 1 second)
```
rundownai sends email to your Gmail
→ Gmail detects new email
→ Gmail sends a tiny notification to Google Pub/Sub
→ Pub/Sub calls our Cloud Run service at POST /pubsub/push
→ Our server wakes up
```

### Step 2: Email Reading (2–3 seconds)
```
Our server asks Gmail API: "Give me the email body"
→ Gmail returns raw HTML (messy email code)
→ We send the HTML to Claude with instructions:
   "Extract every news story. Give me: headline, summary, stats,
    most shocking number. Return as JSON."
→ Claude returns a clean list of 7–10 stories
```

### Step 3: Parallel Processing (all stories at once)
For each story simultaneously:

```
┌─────────────────────────────────────────────────────┐
│ Story: "OpenAI launches GPT-5"                      │
│                                                     │
│ Thread A: Image Search                              │
│   → Claude generates search query                  │
│   → Serper searches Google Images                  │
│   → Returns first valid image URL                  │
│                                                     │
│ Thread B: Caption Writing (happens simultaneously) │
│   → Claude writes hook, summary, CTA, hashtags     │
│   → Validates format                               │
└─────────────────────────────────────────────────────┘
```

### Step 4: Carousel Creation (1–2 seconds)
```
Pillow creates 4 images:
  Slide 1: Downloads story image → place on black canvas →
           add vignette → draw "DO YOU KNOW" badge →
           draw headline in huge Anton font
  Slide 2: Draw the hook stat (e.g. "10x") huge in purple
  Slide 3: Draw numbered bullet points (the key stats)
  Slide 4: Draw "FOLLOW @techwithhareen"
→ Saves as slide1.png, slide2.png, slide3.png, slide4.png
```

### Step 5: Quality Check (3–5 seconds)
```
Claude reviews the post:
  ✅ Does the cover slide have a clear hook?
  ✅ Are brand colors consistent?
  ✅ Is the @techwithhareen handle present throughout?
  ✅ Are hashtags present and relevant?
  ✅ Is the caption well-formatted?
  ✅ Is there a CTA on the last slide?

If any fail → 1 automatic retry
If still failing → Skip this story, send you an alert
```

### Step 6: Telegram Delivery (1 second)
```
For each story that passed:
  → Send 4 slide images as an album to your Telegram
  → Send caption text
  → Add two buttons: [✅ Approve] [❌ Reject]
  → Store story ID in Redis linked to the button

All stories sent in a burst to your phone.
```

### Step 7: Your Approval (whenever you check your phone)
```
You see the slides + caption in Telegram
You tap ✅ Approve
  → Telegram calls POST /telegram/webhook on our server
  → We look up the story ID from Redis
  → Publisher logs: "Story approved, slides saved at /tmp/..."
  → You manually download slides and post to Instagram
```

**Total time from email arriving to Telegram notification: ~30–60 seconds.**

---

## 5. Why Not Use Simpler Tools?

A reasonable question: couldn't you just use Zapier, Make.com, or another no-code tool?

| Tool | Why We Didn't Use It |
|------|---------------------|
| **Zapier** | No way to generate custom images or run AI that creates visual content. Good for simple data routing, not creative pipelines. |
| **Make.com** | Same limitations. Great for "when email arrives, add row to spreadsheet" — not "when email arrives, design 4 custom slides" |
| **Buffer/Later** | Scheduling tools, not pipeline builders. Can't generate content. |
| **Canva automation** | Canva's API is Enterprise-only ($$$) and not programmable enough for our custom design |
| **n8n** | Similar to Make/Zapier, open-source. Could handle parts of this but image generation and AI orchestration would still require custom code |

The core of what we're doing — **AI-powered content creation + custom image generation** — simply requires real code. No-code tools aren't there yet for this level of customisation.

---

## 6. Glossary

| Term | Plain English Meaning |
|------|-----------------------|
| **API** | A way for two pieces of software to talk to each other. Like a waiter taking your order to the kitchen. |
| **Agent** | A piece of code that does one specific job, possibly using AI |
| **Endpoint** | A "door" on a web server that receives requests. E.g., `/healthz` is a door that checks if the server is alive. |
| **Container** | A self-contained package of code + everything it needs to run, like a shipping container for software |
| **Cloud** | Someone else's computer that you rent. Google Cloud = Google's computers |
| **Serverless** | Cloud computing where you don't manage a server yourself — you just give Google your code and they run it |
| **SDK** | Software Development Kit. A toolbox of pre-written code from a company to help you use their service |
| **JSON** | A simple way to write structured data. Like: `{"name": "OpenAI", "raised": "$6B"}` |
| **Webhook** | A URL that another service calls when something happens. Telegram calls our webhook URL when you tap a button. |
| **VPC** | Virtual Private Cloud. A private network inside Google Cloud. Our Redis lives here, protected from the internet. |
| **Pub/Sub** | A messaging system where one service "publishes" a message and another "subscribes" to receive it |
| **Terraform** | A tool that creates cloud infrastructure from text files, like an instruction manual for your cloud setup |
| **CI/CD** | Automated build and deployment. When you push code, it automatically builds and deploys without manual steps. |
| **Redis** | A super-fast in-memory database used for temporary data like session state |
| **Cron/Scheduler** | A way to run code on a schedule, like "every day at 6am" |
| **Liveness probe** | Google Cloud Run pings `/healthz` every 30 seconds to verify the service is still alive |
| **Secret** | A sensitive value (password, API key) that must be stored securely and never put in code |
| **Instance** | One running copy of our Cloud Run container |
| **Revision** | A version of our Cloud Run service. Every deploy creates a new revision (like version 1, version 2, etc.) |
| **Pipeline** | A series of steps that process data in order, like an assembly line |
| **Carousel** | An Instagram post with multiple images you can swipe through |
| **CTA** | Call To Action. The bit that says "Follow for more!" |
| **Hook** | The first line of an Instagram caption, designed to grab attention |

---

*Built for @techwithhareen — AI, Tech & Startups*
*Last updated: March 2026*
