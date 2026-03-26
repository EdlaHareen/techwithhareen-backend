# Roadmap: techwithhareen — v4.0 Algorithm Compliance + Content Engine

## Milestones

- ✅ **v1.0 Gmail Pipeline** — Phases 1–3 (shipped 2026-02-01)
- ✅ **v2.0 Web UI Research** — Phases 4–6 (shipped 2026-03-15)
- ✅ **v3.0 Content Voice + Slide Editor** — Phases 7–9 (shipped 2026-03-25)
- 🚧 **v4.0 Algorithm Compliance + Content Engine** — Phases 1–4 (in progress)

---

## v4.0 Phases

### Phase Summary

- [ ] **Phase 1: Algorithm Compliance** - Fix hashtag count, background colour, CTA slides, caption hook, and Slide 2 hook to match Instagram best practices
- [ ] **Phase 2: Content Classification** - Add a 3-type content classifier that runs before carousel creation and surfaces in the web UI
- [ ] **Phase 3: Reels Script Agent** - On-demand Reel script generation with Hareen's voice, all 3 content types, 4 target lengths, per-segment structure
- [ ] **Phase 4: Series + Stories** - "This Week in AI" roundup template and on-demand Story teaser card generation

## Phase Details

### Phase 1: Algorithm Compliance
**Goal**: Every post leaving the system complies with Instagram's 2025 algorithm best practices — correct hashtag count, background colour, CTA placement, and standalone hook copy.
**Depends on**: Nothing (first phase of v4)
**Requirements**: ALGO-01, ALGO-02, ALGO-03, ALGO-04, ALGO-05, ALGO-06, ALGO-07
**Success Criteria** (what must be TRUE):
  1. The caption writer produces exactly 3–5 hashtags per post (1 branded + 1–2 niche + 1 broad), never more
  2. Every carousel slide background is `#1A1A2E` — no slide in any post has a `#000000` background
  3. Carousels with 8+ slides include a mid-carousel "BOOKMARK THIS" slide; all final CTA slides say "SEND THIS TO SOMEONE"
  4. Every caption hook is ≤ 120 characters and a grammatically complete sentence that makes sense without reading the rest of the caption
  5. Slide 2 contains a complete self-contained stat statement — the phrase "SWIPE TO FIND OUT WHY" does not appear on any slide
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Carousel renderer: #1A1A2E background, BOOKMARK THIS mid-slide, SEND THIS TO SOMEONE CTA, remove SWIPE TO FIND OUT WHY
- [ ] 01-02-PLAN.md — Caption writer + post analyzer: 3-5 hashtag cap, ≤120-char hook enforcement, DM-share primary CTA

### Phase 2: Content Classification
**Goal**: Every story is automatically labelled with one of three content types before carousel creation, so templates, caption voice, and CTAs are driven by the type of content rather than generic defaults.
**Depends on**: Phase 1
**Requirements**: CLASS-01, CLASS-02, CLASS-03
**Success Criteria** (what must be TRUE):
  1. Every story processed by the pipeline has a `content_type` field set to one of: `news_and_announcements`, `tool_and_product`, or `educational`
  2. The classifier output visibly influences the carousel and caption — a `tool_and_product` post uses a different caption voice than an `educational` post
  3. The web UI approval queue shows a content type badge on each post card, and Hareen can see at a glance what type each post is
**Plans**: TBD

### Phase 3: Reels Script Agent
**Goal**: Hareen can generate a ready-to-record Reel script for any approved post, on demand, with structured per-segment output that tells her exactly what to say and show at each moment.
**Depends on**: Phase 2
**Requirements**: REEL-01, REEL-02, REEL-03, REEL-04, REEL-05, REEL-06, REEL-07
**Success Criteria** (what must be TRUE):
  1. A "Generate Reel Script" button exists on each PostCard in the web UI; clicking it generates a script without re-running the full carousel pipeline
  2. The generated script has segments with `spoken_text`, `on_screen_text`, `overlay_type`, and `duration_seconds` — Hareen can follow it without interpretation
  3. Script word count stays within the target length (30s = ≤ 75 words, 45s = ≤ 112 words, 60s = ≤ 150 words), and Hareen can switch target length before generating
  4. Scripts are saved to Firestore and viewable in a modal with per-segment copy buttons — Hareen can copy each segment to her recording notes
  5. Script language uses no passive voice, no filler phrases, and sounds like Hareen talking — not an LLM summary
**Plans**: TBD

### Phase 4: Series + Stories
**Goal**: Hareen can assemble a "This Week in AI" roundup carousel from existing approved posts, and generate a 9:16 teaser Story card for any post — both on demand from the web UI.
**Depends on**: Phase 2
**Requirements**: SERIES-01, SERIES-02, SERIES-03, SERIES-04, STORY-01, STORY-02, STORY-03
**Success Criteria** (what must be TRUE):
  1. The carousel renderer has a roundup template — selecting 5–7 approved posts and triggering roundup assembly produces a carousel with a Cover → story tiles → CTA slide structure
  2. Hareen can select multiple posts from the History page and trigger roundup assembly without any manual slide editing required for a first draft
  3. Post cards assigned to the "This Week in AI" series show a series badge in the web UI
  4. A "Generate Story Card" button exists on each PostCard; clicking it produces a 1080×1920px teaser card with the hook stat in large Anton type and the `#8075FF` accent background, downloadable from the web UI
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Algorithm Compliance | 0/2 | Not started | - |
| 2. Content Classification | 0/? | Not started | - |
| 3. Reels Script Agent | 0/? | Not started | - |
| 4. Series + Stories | 0/? | Not started | - |

---
*Roadmap created: 2026-03-25 for v4.0 milestone*
*Phase 1 plans written: 2026-03-25*
