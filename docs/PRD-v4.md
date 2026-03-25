# Product Requirements Document — @techwithhareen v4
**Version:** 4.0
**Date:** 2026-03-25
**Owner:** Hareen Edla
**Status:** Draft
**Depends on:** BRD-v4.md

---

## 1. Overview

v4 transforms @techwithhareen from a single-format (carousel) news aggregator into a multi-format content engine. It ships in two phases:

- **Phase 1 — Algorithm Compliance** (quick wins, no new agents): Fix the 6 issues actively penalising reach today
- **Phase 2 — Content Engine Expansion** (new agents + templates): Reels scripts, content classification, recurring series, Stories

All features build on the existing FastAPI backend, React web UI, Pillow renderer, and GCS infrastructure.

---

## 2. Phase 1 — Algorithm Compliance Fixes

These are not optional. Every day these are unshipped, reach is being suppressed.

---

### F1.1 — Hashtag Count: 3–5 (was 15–20)

**Problem:** Instagram capped effective hashtags at 3–5 in December 2025. Using 15–20 is now actively penalised.

**Requirements:**
- `CaptionWriterAgent` must generate exactly 3–5 hashtags per post
- Selection rule: 1 branded tag (`#techwithhareen`) + 1–2 story-specific niche tags + 1 broad category tag
- Remove all filler/volume tags (`#Innovation`, `#Technology`, etc.)
- Validate in `Caption.is_valid()`: fail if hashtag count < 2 or > 5

**Acceptance criteria:**
- [ ] Every generated caption has 3–5 hashtags
- [ ] `is_valid()` rejects captions with > 5 hashtags
- [ ] Hashtags are story-specific (not generic filler)

---

### F1.2 — Background Colour: #1A1A2E (was #000000)

**Problem:** Pure black (#000000) causes halation — text becomes harder to read and the design looks cheaper. All top AI/tech creators use very dark navy or grey.

**Requirements:**
- Change `BLACK = (0, 0, 0)` to `DARK_BG = (26, 26, 46)` (`#1A1A2E`) in `carousel_renderer.py`
- All slide backgrounds use `DARK_BG`
- Accent (`#8075FF`) and white text remain unchanged
- `_black_canvas()` renamed to `_bg_canvas()` to reflect the change

**Acceptance criteria:**
- [ ] All rendered slides use `#1A1A2E` background
- [ ] No visual degradation on text readability
- [ ] Accent and white colours unchanged

---

### F1.3 — Two-CTA Strategy: Mid-carousel soft + DM-share final

**Problem:** Current system has one CTA (end slide: "FOLLOW FOR MORE"). Missing: (1) mid-carousel soft CTA, (2) DM-share as the primary final CTA.

**Requirements:**

**Mid-carousel CTA slide (new slide type):**
- Inserted at position 5–6 in carousels with 8+ slides
- Black bg, accent text: `BOOKMARK` / white: `THIS`
- Sub-label in gray: "you'll want to come back to this"
- No brand watermark on this slide (keeps it clean)

**Final CTA slide — updated copy:**
- Replace "FOLLOW FOR MORE" with two lines:
  - Line 1 (white): `SEND THIS`
  - Line 2 (accent): `TO SOMEONE`
  - Sub-line (gray, Inter): "who needs to know this"
- Keep `@techwithhareen` at bottom in accent

**CaptionWriterAgent CTA options — updated:**
- Remove: `"Follow @techwithhareen for daily AI updates ⚡"`
- Add: `"Send this to someone who needs to see it 👇"`
- Keep: `"Save this post 🔖"` as secondary option
- New selection logic: DM-share CTA for tool/feature + funding stories; Save CTA for research/educational

**Acceptance criteria:**
- [ ] Carousels with 8+ slides include mid-carousel bookmark slide
- [ ] Final slide says "SEND THIS TO SOMEONE" not "FOLLOW FOR MORE"
- [ ] Caption CTA uses DM-share as primary for non-evergreen stories

---

### F1.4 — Caption First 125 Characters Enforced

**Problem:** Instagram truncates captions at 125 chars before "...more". The hook must be complete within this limit.

**Requirements:**
- `CaptionWriterAgent` prompt explicitly instructs: "The hook line must be a complete, punchy sentence under 120 characters — it will be the only thing visible before '...more'"
- Add validation: `Caption.is_valid()` warns if `hook` > 120 chars
- Hook must not end mid-sentence at truncation point

**Acceptance criteria:**
- [ ] Hook field in generated captions is ≤ 120 chars
- [ ] Hook is a grammatically complete sentence
- [ ] Validation logs a warning (not failure) if hook exceeds limit

---

### F1.5 — Slide 2 (Hook Stat) Works as Standalone Hook

**Problem:** Instagram re-shows carousels starting from slide 2 to users who saw the carousel but didn't swipe. Current slide 2 says "SWIPE TO FIND OUT WHY" — useless to someone who never saw slide 1.

**Requirements:**
- Remove "SWIPE TO FIND OUT WHY" sub-label from `_slide_hook_stat()`
- Replace with a one-line implication text: the `hook_stat_label` should now be written as a complete provocative statement, not just a context label
- Update `CaptionWriterAgent` / story LLM prompts to generate `hook_stat_label` as a self-contained shocking fact (e.g., "NVIDIA NOW CONTROLS 90% OF AI CHIP REVENUE" not just "OF CHIP REVENUE")
- Slide 2 must make sense to someone who has never seen slide 1

**Acceptance criteria:**
- [ ] "SWIPE TO FIND OUT WHY" removed from all carousels
- [ ] `hook_stat_label` reads as a complete statement
- [ ] Slide 2 passes a standalone comprehension check (can be understood without slide 1)

---

## 3. Phase 2 — Content Engine Expansion

---

### F2.1 — Content Type Classifier

**Problem:** Every story currently gets the same carousel template regardless of whether it's breaking news, a tool review, a research finding, or an opinion. Different types need different templates, different tone, different structure.

**Requirements:**

**New field on `Story`:**
```python
content_type: Literal["breaking_news", "tool_review", "research_finding", "opinion_hot_take", "evergreen_explainer"] = "breaking_news"
```

**Classification logic:**
- Added to `ResearchOrchestrator` synthesis pass (v2) and `ContentFetcherAgent` (v1)
- LLM classifies each story into one of 5 types based on headline + summary
- Classification informs: carousel template, caption tone, CTA choice, series routing

**Template mapping:**

| Content Type | Carousel Template | Caption Voice | CTA |
|-------------|-------------------|---------------|-----|
| `breaking_news` | Standard UncoverAI | Contrarian analyst | DM-share |
| `tool_review` | "WORTH IT / HYPE?" verdict layout | Translator (practical) | Save |
| `research_finding` | Data-forward, stat-heavy | Accessible + actionable | Save |
| `opinion_hot_take` | Bold statement slides | Direct, opinionated | DM-share |
| `evergreen_explainer` | Step-by-step numbered layout | Teacher mode | Save |

**Acceptance criteria:**
- [ ] Every story has a `content_type` field populated before carousel creation
- [ ] Carousel renderer uses correct template per content type
- [ ] Caption agent uses correct voice mode per content type (extends existing 4-mode system)
- [ ] Web UI shows content type badge on each post card

---

### F2.2 — Reels Script Agent

**Problem:** Zero Reels = zero discovery. Reels get 2.25× more reach than any other format. The system needs to produce ready-to-record Reel scripts for Hareen.

**What this does NOT do:** Record, generate video, or post automatically. It writes the script + on-screen text breakdown. Hareen records it.

**New agent:** `src/agents/reels_script/agent.py` — `ReelsScriptAgent`

**Input:** `Story` + `content_type`

**Output:** `ReelsScript` dataclass:
```python
@dataclass
class ReelsScript:
    story_id: str
    target_length_seconds: int       # 15 | 30 | 45 | 60
    hook_line: str                   # spoken + on-screen, < 10 words, opens cold
    segments: list[ReelsSegment]     # each segment: spoken text + on-screen text + duration
    cta: str                         # final spoken CTA
    on_screen_cta: str               # final on-screen text
    hashtags: list[str]              # 3-5 tags
    caption: str                     # full Instagram caption for the Reel
    content_type: str
```

**Script formula by content type:**

`breaking_news` (30s):
1. Hook stat on screen (3s): "[shocking number]"
2. What happened (7s): one sentence spoken + text overlay
3. Why it matters (10s): Hareen's take, conversational
4. What to do (7s): one concrete action
5. CTA (3s): "Send this to someone who needs to see it"

`tool_review` (30s):
1. Problem hook (5s): "You're wasting [X] doing [Y]"
2. Tool reveal (5s): "[Tool] fixes this in [X] seconds"
3. Demo description (15s): describe the key feature (Hareen demos on screen)
4. Verdict (3s): "Worth it / Hype — here's why"
5. CTA (2s): "Save this for later"

`opinion_hot_take` (15s):
1. Contrarian opener (3s): "Everyone thinks [X]. They're wrong."
2. The real take (9s): Hareen's actual view
3. Open loop (3s): question that drives comments

`research_finding` (45s):
1. Hook (5s): the most counterintuitive finding
2. What the research says (15s): plain English
3. What it means for you (15s): concrete implication
4. Takeaway (7s): one thing to do differently
5. CTA (3s)

`evergreen_explainer` (60s):
1. Hook question (5s): "Do you actually understand [concept]?"
2. Explanation in 3 steps (40s): one concept per step, fast-paced
3. Why it matters now (10s)
4. CTA (5s): save + follow

**New API endpoint:**
`POST /api/v2/posts/{post_id}/reel-script` — generates and saves a Reel script for an existing post

**Firestore:** Store `reel_script` as a sub-field on the post document

**Web UI:** "Generate Reel Script" button on each PostCard → shows script in a modal with copy-to-clipboard per segment

**Acceptance criteria:**
- [ ] `ReelsScriptAgent` generates scripts for all 5 content types
- [ ] Scripts are under the target word count for the target duration (avg 130 words/min speaking pace)
- [ ] Scripts follow the correct formula for each content type
- [ ] Hareen's voice rules from `_PERSONA_INSTRUCTION` apply to script writing
- [ ] Web UI shows script in readable format with copy button per segment
- [ ] Scripts stored in Firestore per post

---

### F2.3 — Recurring Series Templates

**Problem:** No recurring series means the algorithm can't classify the account. Series create appointment viewing and compound audience expectations.

**Three series to implement:**

**Series 1: "This Week in AI" (Monday)**
- Format: Carousel, 8–10 slides
- Structure: Cover → 5–7 story tiles (one stat + one implication each) → CTA
- Source: Top 5–7 stories from the week's rundownai newsletters or manual selection
- Template: Horizontal dividers between stories, consistent numbered layout
- Caption structure: "5 AI stories from this week that actually matter 👇"

**Series 2: "Worth It or Hype?" (Wednesday)**
- Format: Carousel + companion Reel script
- Structure: Cover with product name → Verdict pill (WORTH IT / HYPE / WATCH THIS SPACE) → 3 slides of evidence → "Who this is for" → "Who this isn't for" → CTA
- Source: Any `tool_review` content type story
- Template: Verdict colour-coding (green = worth it, red = hype, yellow = watch)

**Series 3: "Hot Take" (Friday)**
- Format: Reel script (primary) + quote card carousel (secondary)
- Structure: Bold contrarian statement → 3 supporting points → open question for comments
- Source: Any `opinion_hot_take` content type story
- Template: Large text quote cards, minimal design, Hareen's face on cover expected

**Implementation:**
- New `series_type` field on `Story`: `None | "weekly_roundup" | "worth_it_or_hype" | "hot_take"`
- Series routing happens in content type classifier (F2.1)
- Each series has its own carousel template variant in `carousel_renderer.py`
- Web UI shows series badge on post cards
- New `POST /api/v2/posts/{post_id}/series` endpoint to manually assign a series

**Acceptance criteria:**
- [ ] Each series has a distinct visual template
- [ ] Series type is displayed in the web UI
- [ ] "This Week in AI" can be triggered from the v2 Web UI with multiple story inputs
- [ ] "Worth It or Hype?" verdict is LLM-generated based on story content
- [ ] "Hot Take" automatically generates a companion Reel script

---

### F2.4 — Stories Pipeline

**Problem:** No Stories = no daily algorithm signals, no community retention, no discovery from followers who check Stories daily.

**What this builds:** Auto-generation of 3 Story cards from every approved carousel post.

**Story card types (generated per post):**

1. **Teaser card** — Hook stat from slide 2, large text, accent background, "NEW POST" label
2. **Key insight card** — One key_stat from the carousel, formatted as a pull quote
3. **Engagement card** — A poll or question based on the story: "Would you use this?" / "Does this worry you?" / "Rate this tool: 🔥 or 💀"

**Technical approach:**
- New `StoriesGenerator` utility in `src/utils/stories_generator.py`
- Uses Pillow renderer, Stories format: 1080×1920px (9:16)
- Outputs 3 PNG files per post
- Uploaded to GCS alongside carousel slides
- Stored in Firestore as `story_cards: list[str]` on the post document

**Web UI:**
- New "Story Cards" section on PostCard (collapsed by default, expandable)
- Shows 3 thumbnails
- "Download All" button for Stories (Hareen posts manually to Instagram Stories)
- Poll text shown below engagement card so Hareen can type it when posting

**Story card design:**
- Background: `#8075FF` (accent) for teaser, `#1A1A2E` for insight, `#1A1A2E` for engagement
- Font: Anton for headline, Inter for body
- `@techwithhareen` watermark top-left
- No GCS slide counter (Stories are single cards)

**Acceptance criteria:**
- [ ] 3 Story cards generated for every approved post
- [ ] All cards are 1080×1920px
- [ ] Poll question is contextual to the story
- [ ] Story cards visible in web UI
- [ ] Download button works
- [ ] Story cards stored in GCS + Firestore

---

## 4. Out of Scope for v4

- Instagram Graph API publishing (remains manual through v4)
- TikTok / YouTube Shorts adaptation
- Mixed-media carousels (image + video clips) — deferred to v5
- Collaboration post features
- Scheduling / posting calendar automation
- Analytics ingestion (Instagram Insights API)
- A/B testing of carousel variants

---

## 5. Technical Architecture Changes

| Component | v3 State | v4 Changes |
|-----------|----------|------------|
| `carousel_renderer.py` | 6 slide types | +2 slide types (mid-CTA, series variants), bg colour fix |
| `caption_writer/agent.py` | 4 voice modes, 15-20 hashtags | 5 content types, 3-5 hashtags, DM-share CTA |
| `story.py` | 10 fields | +2 fields: `content_type`, `series_type` |
| `orchestrator/handler.py` | Post creator → caption → analyzer | +classifier step before post creator |
| `api/routes_v2.py` | 10 endpoints | +2 endpoints: `/reel-script`, `/series` |
| `src/agents/reels_script/` | Not exists | New agent |
| `src/utils/stories_generator.py` | Not exists | New utility |
| `src/utils/content_classifier.py` | Not exists | New utility |
| Frontend `PostCard.tsx` | Caption edit, slide edit | +Reel script modal, +Story cards section, +series/type badges |
| Firestore posts schema | 12 fields | +4 fields: `content_type`, `series_type`, `reel_script`, `story_cards` |

---

## 6. Phased Delivery Plan

### Phase 1 — Algorithm Compliance (Week 1)
- F1.1: Hashtags 3–5
- F1.2: Background colour #1A1A2E
- F1.3: Two-CTA strategy
- F1.4: Caption 125-char hook
- F1.5: Slide 2 standalone hook

**Exit criteria:** All 5 fixes deployed to production. No regression on existing pipeline.

### Phase 2A — Classification + Series (Week 2–3)
- F2.1: Content type classifier
- F2.3: Recurring series templates

**Exit criteria:** Stories are routed to correct templates. 3 series templates render correctly.

### Phase 2B — Reels + Stories (Week 3–4)
- F2.2: Reels Script Agent
- F2.4: Stories Pipeline

**Exit criteria:** Reel script generated and displayed in web UI for test stories. Story cards generated and downloadable.

---

## 7. Open Questions

| # | Question | Owner | Priority |
|---|----------|-------|----------|
| Q1 | Should the content type classifier run before or after research validation? | Hareen | High |
| Q2 | "Worth It or Hype?" verdict — should Hareen input a verdict or should LLM generate it? | Hareen | Medium |
| Q3 | Should Story cards be generated for all posts or only on Hareen's request? | Hareen | Medium |
| Q4 | For "This Week in AI" roundup — manual story selection or auto-pull from the week's posts? | Hareen | High |
| Q5 | Reel script target length — 30s default or should Hareen choose per story? | Hareen | Low |

---

## 8. Success Criteria (Definition of Done)

v4 is complete when all of the following are true:

- [ ] All Phase 1 fixes deployed and validated in production
- [ ] Content type classifier correctly classifies ≥ 90% of test stories
- [ ] `ReelsScriptAgent` produces scripts Hareen rates as "usable without major edits" for ≥ 70% of stories
- [ ] All 3 series templates render correctly and are selectable in web UI
- [ ] Story cards generated for 3 test posts, all downloadable from web UI
- [ ] System supports a 5×/week posting workflow without increasing approval time
- [ ] Hashtag count validated to 3–5 on all new posts
- [ ] Background colour confirmed #1A1A2E across all slide types
- [ ] Final CTA confirmed as DM-share on all new carousels

---
