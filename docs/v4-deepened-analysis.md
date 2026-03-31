# v4 BRD + PRD — Deepened Analysis & Recommendations
**Deepened:** 2026-03-25
**Method:** 4 parallel research agents across Instagram algorithm verification, feature ROI analysis, Reels script design, and Stories strategy
**Purpose:** Identify what's truly needed vs. over-engineered before building starts

---

## TL;DR — The Verdict

| Feature | Original Verdict | Research Verdict |
|---|---|---|
| **Phase 1 (all 5 fixes)** | Required | ✅ Confirmed — ship all 5, unchanged |
| **F2.1 Classifier (5 types)** | Required | ⚠️ Simplify to 3 types — 5 is over-engineered |
| **F2.2 Reels Script Agent** | Required | ✅ Highest ROI in v4. Ship it. One constraint added. |
| **F2.3 Series (3 templates)** | Required | ⚠️ Ship 1 series only ("This Week in AI"), defer other 2 to v5 |
| **F2.4 Stories (3 cards)** | Required | ⚠️ Ship 1 card only (teaser), defer insight + poll to v5 |

**Bottom line:** Phase 1 is untouched — build all of it. Phase 2 needs pruning. The Reels Script Agent is the highest-leverage thing in the entire doc. The Series and Stories features are scoped too ambitiously for v4.

---

## Part 1 — Algorithm Claims: What's Real vs. Overclaimed

The BRD presents several specific claims as verified facts. Here's the actual status of each, which matters because overclaimed metrics drive bad prioritization decisions.

### Claim 1: "3–5 hashtag cap, December 2025, active distribution penalty"
**Status: Directionally correct. The specifics are overclaimed.**

The 3–5 recommendation is real and safe to enforce. Instagram guidance shifted away from spray-and-pray hashtag use years ago, and Adam Mosseri has consistently recommended fewer, more relevant tags. However:
- No primary source confirms a "December 2025" hard cap triggering an active penalty
- Instagram's actual position: the algorithm ignores irrelevant hashtags but doesn't actively suppress you for using more of them
- The practical benefit of 3–5 is eliminating visual clutter and tag irrelevance, not avoiding a penalty mechanism

**Updated framing for the PRD:** "3–5 relevant hashtags is current best practice. Large hashtag stacks deliver negligible additional reach and create visual noise." Remove "active penalty" language.

### Claim 2: "DM shares confirmed as #1 algorithm signal, January 2025"
**Status: Directionally correct. "Confirmed #1" is overstated.**

Instagram has emphasised sends and saves as high-weight signals consistently since 2023. The "send this to someone" CTA strategy is well-founded. However:
- Instagram has never published a ranked signal list
- Watch-time completion rate and re-watch rate for Reels are equally or more important for distribution
- The DM-share CTA is worth keeping, but add "complete the Reel" as an implicit goal too (don't cut content to drive shares at the expense of completion rate)

**Updated framing:** "Instagram consistently cites DM sends and saves as high-weight signals. Design CTAs for shares and ensure Reels have high completion rates."

### Claim 3: "Pure black #000000 causes halation"
**Status: Real concern — but not an Instagram-specific penalty.**

OLED screen halation is a genuine visual phenomenon. White text on pure black creates blooming/glow at character edges on OLED and AMOLED screens. The #1A1A2E recommendation is correct and backed by Apple HIG and Material Design guidance. However, Instagram doesn't algorithmically penalise pure black. This is a design quality decision, not an algorithm compliance fix.

**Impact on PRD:** F1.2 is still worth shipping — but frame it as "improves visual quality on modern OLED screens" not "algorithm compliance." This affects how Hareen communicates the change if anyone asks.

### Claim 4: "Instagram re-shows carousels from slide 2"
**Status: Widely reported, not officially documented. Low risk to act on.**

This behaviour is widely observed and treated as established by most content strategists, consistent with Instagram's goal of maximising content value per impression. The risk of acting on it is minimal — even if the mechanism is slightly different, designing slide 2 as a standalone hook is sound practice regardless.

**Keep F1.5 as-is.**

### Claim 5: "Reels get 2.25x more reach"
**Status: Unverified as a precise figure. Direction is correct.**

Reels consistently outperform carousels on reach. Instagram actively promotes Reels as a discovery format. However, the "2.25x" multiplier has no traceable primary source — it originates from a third-party study applied to a specific account sample at a specific time and has been repeated without context.

**Updated framing:** Remove the multiplier or caveat it. The decision to add Reels doesn't need this number. Say: "Reels are Instagram's primary discovery format, consistently generating greater non-follower reach than carousels." That's accurate and sufficient.

### Claim 6: "40/40/20 content mix (timely/evergreen/opinion)"
**Status: A constructed heuristic, not a research-backed ratio.**

The underlying three-category framework (timely + evergreen + opinion) is standard content strategy advice with solid logic. But the 40/40/20 split specifically is not derived from any Instagram study. There is no evidence it outperforms 50/30/20 or 33/33/33 for a tech/AI account at this stage.

**Updated framing:** Treat as a starting hypothesis, not a target. The right mix will emerge from actual post performance data. Enforcing 40/40/20 from day one could cause Hareen to post evergreen or opinion content that underperforms if the audience is primarily there for timely AI news.

### Claim 7: "5x posts per week target"
**Status: Risky framing for a solo creator.**

Buffer's data supporting 3–5 posts/week is real, but measured across all account types. For a solo creator producing handcrafted content, 5x/week risks quality degradation, audience fatigue, and creator burnout — the most common failure mode for solo-operated content accounts.

**Updated framing:** 5x is a ceiling, not a floor. Target 3x consistently as the non-negotiable minimum. Scale toward 5x as the pipeline reduces per-post effort. A missed week after 5x posting hurts more than a consistent 3x cadence.

---

## Part 2 — Phase 1: Algorithm Compliance (Confirmed. Build all of it.)

All 5 Phase 1 fixes survive scrutiny. These should be the first thing shipped.

| Fix | Verdict | Notes |
|---|---|---|
| F1.1 Hashtags 3–5 | ✅ Ship as-is | Remove "active penalty" framing from comments/docs |
| F1.2 Background #1A1A2E | ✅ Ship as-is | Frame as OLED readability improvement, not algorithm fix |
| F1.3 Two-CTA strategy | ✅ Ship as-is | Both DM-share CTA and mid-carousel bookmark are sound |
| F1.4 Caption 125-char hook | ✅ Ship as-is | Correct and important |
| F1.5 Slide 2 standalone | ✅ Ship as-is | Low risk, high design value |

**One addition for F1.3:** The caption DM-share CTA logic is right, but note that for Reels (when F2.2 is built), completion rate is equally important as DM shares. The CTA should not cause content to be cut short to drive shares. Ensure the "Send this" CTA comes at the natural end of the content, not truncating it.

---

## Part 3 — Phase 2: What's Needed vs. Over-Engineered

### F2.1 — Content Type Classifier: Simplify from 5 types to 3

**The problem with the current 5-type spec:**

In practice, the rundownai newsletter and v2 research pipeline produce content that skews heavily toward 2–3 buckets. `opinion_hot_take` and `evergreen_explainer` are almost never sourced from a news feed — they require Hareen's original voice and framing, which the system cannot generate from a newsletter story. Building routing logic for 5 types when 2–3 types handle 85–90% of traffic creates unnecessary complexity and misclassification risk (an LLM that confidently mislabels a "tool funding announcement" as `tool_review` instead of `breaking_news` fires the wrong template, wrong caption voice, and wrong CTA — three cascading errors).

**Revised spec: 3 types**

| New Type | Maps From | Carousel Template | Caption Voice | CTA |
|---|---|---|---|---|
| `news_and_announcements` | breaking_news + funding_acquisition | Standard UncoverAI | Contrarian analyst | DM-share |
| `tool_and_product` | tool_review | "Worth it/Hype" verdict layout | Translator (practical) | Save |
| `educational` | research_finding + evergreen_explainer | Data-forward, stat-heavy | Accessible + actionable | Save |

**What to do with `opinion_hot_take`:**
Don't route it from classification at all. Opinion content requires Hareen's original framing, not an LLM decision on a newsletter story. Add it later as a manual entry point in the web UI where Hareen writes her own hot take, then the system formats and schedules it.

**Result:** 3 template variants instead of 5, fewer misclassification edge cases, lower maintenance surface.

---

### F2.2 — Reels Script Agent: ✅ Ship It (highest ROI in v4)

**Why this is the most important Phase 2 feature:**

Zero Reels = zero discovery engine. The script agent is also the simplest Phase 2 build: one new agent, one new dataclass, one modal in the web UI, no renderer changes. Everything else in Phase 2 is more complex and delivers less incremental value.

**One constraint to enforce from the original spec:**

The script should be generated **on-demand** from the web UI ("Generate Reel Script" button per post), not automatically for every post in the pipeline. Auto-generation on every story produces scripts Hareen never looks at, pollutes Firestore with unused data, and adds latency to the pipeline for a feature requiring her active participation. On-demand generation ties script creation to her actual intent to record.

**PRD changes the research supports — incorporate these before building:**

**1. Update the word-count spec. The PRD uses 130 wpm — this is too slow.**

High-performing Reels creators speak at 150–170 wpm on-camera. Revised targets at 150 wpm:

| Duration | At 130 wpm (current PRD) | At 150 wpm (recommended) |
|---|---|---|
| 15s | 33 words | 37–38 words |
| 30s | 65 words | 75 words |
| 45s | 97 words | 112 words |
| 60s | 130 words | 150 words |

Note: segments with silent on-screen moments (like the 3s stat card in `breaking_news`) don't count against the spoken-word budget. Track spoken-word budget separately from total duration in the agent.

**2. Redefine the on_screen_text relationship in ReelsSegment.**

The PRD doesn't define the relationship between `spoken_text` and `on_screen_text`. This gap will cause AI-generated scripts to produce on-screen text as a transcript of the spoken words — which is wrong.

Add an `overlay_type` field to `ReelsSegment`:

```python
@dataclass
class ReelsSegment:
    spoken_text: str          # what Hareen says aloud (in spoken phrases, not sentences)
    on_screen_text: str       # the visual headline of the spoken thought
    overlay_type: Literal["anchor", "contrast", "reinforcement"]
    duration_seconds: int
```

Rules:
- `anchor` (most common): on-screen shows the core number/verdict/noun; spoken provides context
- `contrast` (most powerful): on-screen delivers the punchline to what was spoken. Creates comedy/tension beat.
- `reinforcement` (use only for hook and CTA): on-screen repeats the exact spoken phrase word-for-word

**3. Revise two script formulas.**

`breaking_news` — Change "What to do (7s)" to "What this changes (7s)":
Breaking news is rarely immediately actionable. The value is in shifting understanding, not prescribing action. The Hareen voice is an analyst, not an advisor.

```
Hook stat on screen (3s) → What happened (5s) → Why it matters (12s, this is Hareen's value-add) → What this changes (7s) → CTA (3s)
```

`tool_review` — Move verdict to the front (verdict-first structure):
The current formula buries the verdict at second 28. That's the entire reason someone watches a tool review. Use a verdict-first sandwich:

```
Verdict declared upfront (3s): "I've been using [tool] for 3 weeks — here's the real verdict."
The problem it solves (5s)
Demo of the key feature (12s)
One thing it does badly (5s) ← the credibility moment; admitting a flaw makes the positive verdict land harder
Final verdict + CTA (5s)
```

**4. Add a speakability system prompt rule.**

The `ReelsScriptAgent` system prompt must include:

> "Write in spoken phrases, not written sentences. Use short clauses. Never use passive voice. Never use: 'Furthermore,' 'Additionally,' 'In conclusion,' 'It has been suggested,' 'Many experts believe.' Write only words Hareen would say aloud to a smart friend — not words she'd write in an email."

**5. Add a banned phrase list.**

Banned openers/phrases: "You're not going to believe this," "Game changer," "Revolutionary," "I wanted to share," "As we know," "It's no secret that," "In today's fast-paced world," anything starting with "So," anything starting with "Hey guys."

These are the specific patterns AI-generated scripts produce when trying to sound casual. They read correctly but sound template-generated when spoken.

**6. Add a hook constraint.**

The `hook_line` spec (< 10 words, opens cold) is correct. Add one format constraint: the hook must be a complete declarative sentence or a two-part contrast ("Everyone thinks X. They're wrong."), never a question with an obvious answer, never a sentence fragment.

---

### F2.3 — Recurring Series Templates: Ship 1, Defer 2

**The algorithm benefit claim for recurring series is weaker than it appears.**

The BRD's claim that recurring series "train the algorithm to classify the account" is about topic consistency, not series format labels. There is no data linking a "This Week in AI" banner to algorithmic benefit. The real benefit of series is operational: they constrain content decisions upfront, reducing planning cognitive load for a solo creator.

**The complexity problem with building all 3:**

- Three distinct carousel template variants with divergent layouts is significant renderer work
- "This Week in AI" requires a different data model (multiple stories as inputs, not one story)
- "Worth It or Hype?" depends on F2.1 classification working correctly
- "Hot Take" is Reel-primary — it depends on F2.2 being shipped AND adopted before the series template adds value

Building series 2 and 3 before F2.2 has any usage data is backwards sequencing.

**Revised spec: Build 1 series only.**

**Ship:** "This Week in AI" (Monday roundup)
- Natural data source: the week's processed stories
- Addresses the most common failure mode for aggregator accounts (nothing to post when no major news breaks)
- Does not depend on F2.1 or F2.2
- Clear trigger: Hareen manually selects 5–7 stories from the week in the web UI → system assembles the roundup carousel

**Defer to v5:** "Worth It or Hype?" and "Hot Take"
- "Worth It or Hype?" needs stable F2.1 routing and a proven verdict-generation pattern
- "Hot Take" is Reel-primary; build the series wrapper after F2.2 adoption is established
- Both require Hareen's original framing that goes beyond what the aggregator pipeline provides

---

### F2.4 — Stories Pipeline: Build 1 Card, Defer 2

**Key finding: Stories drive follower retention, not discovery.**

Instagram runs separate ranking systems for Feed, Reels, and Stories. Stories have zero reach to non-followers. For an account growing from 0 to 10K, the overwhelming majority of growth comes from carousels (saves, shares) and Reels (completion rate, DM sends). Stories are a community retention tool, not a growth lever.

This fundamentally changes the ROI calculation for building the full 3-card spec now.

**What the research says about auto-generated Story cards:**

- Teaser cards (hook stat, large text, accent background): perform at roughly 60–70% of native Stories value when the hook stat is the entire content of the card — not when it's a "NEW POST" promotional wrapper. The PRD's design approach is actually the right one.
- Key insight card (pull quote): derivative for followers who already saw the carousel. Filler at low follower counts.
- Engagement/poll card: highest-value Story type, BUT poll response rates below 2K followers are typically 1–3 responses — which signals low engagement to the algorithm rather than high. Build this after 5K followers when the community can generate meaningful poll volumes.

**Revised spec: 1 card, on-demand.**

Build only the **teaser card** for v4:
- 1080×1920px, accent (`#8075FF`) background
- Hook stat number from slide 2 in massive Anton type (the stat IS the card, not a promotional wrapper)
- `@techwithhareen` watermark, no "NEW POST" branding
- Generated on-demand via "Generate Story Card" button per PostCard (not auto-generated for every post)
- Download button in web UI

**Defer to v5 (gate on 5K followers):**
- Key insight card (second Story card type)
- Engagement/poll card — build after the community is large enough to make polls meaningful
- Any native Stories automation or scheduling

**Why on-demand, not automatic?**
Hareen will not post a Story for every carousel that goes through the pipeline. Auto-generating cards for posts she doesn't use creates queue noise and wasted GCS storage.

---

## Part 4 — Open Questions Answered

The PRD lists 5 open questions. Research provides clear answers to 4 of them.

**Q1: Should the content type classifier run before or after research validation?**
**Answer: Before.** Classification informs the entire downstream cascade (template, caption voice, CTA). Running it after validation means validated stories enter the post creator with no type context, requiring a late-stage LLM call that can't inform validation. Run classification at the end of the synthesis pass in `ResearchOrchestrator` (v2) and at the end of `ContentFetcherAgent` (v1), before `ContentValidator`.

**Q2: "Worth It or Hype?" verdict — Hareen inputs or LLM generates?**
**Answer: Moot for v4.** The "Worth It or Hype?" series is deferred to v5. When it is built, the recommendation is LLM-generated verdict as a draft + Hareen override in the web UI. The LLM can assess evidence but Hareen's credibility is the brand asset — she should confirm the verdict before it renders on the slide.

**Q3: Should Story cards be generated for all posts or only on request?**
**Answer: On request only.** See F2.4 recommendation above. Hareen's intent to post Stories is a selective action, not a universal one.

**Q4: For "This Week in AI" roundup — manual story selection or auto-pull?**
**Answer: Manual selection via the web UI.** Auto-pull from the week's posts requires the system to evaluate story quality/relevance across a week of processed content, which introduces a new ranking signal that isn't yet defined. More importantly, Hareen's editorial judgment on which stories were actually interesting that week is part of the brand value. Build a "Select for Weekly Roundup" checkbox on each PostCard in the History page. On Mondays, she checks 5–7 stories and triggers the roundup assembly.

**Q5: Reel script target length — 30s default or Hareen chooses?**
**Answer: Hareen chooses from 4 options (15/30/45/60), with a smart default based on content type.**

| Content Type | Default Length |
|---|---|
| breaking_news | 30s |
| tool_and_product | 30s |
| opinion_hot_take | 15s |
| educational | 45s |
| evergreen_explainer | 60s |

Expose the override as a simple radio button in the "Generate Reel Script" modal before script generation, defaulting to the content-type recommendation.

---

## Part 5 — Revised Build Sequence

Given the analysis above, the optimal Phase 2 build order for value-per-unit-complexity:

**Phase 2A (Week 2) — Two foundational pieces, lowest complexity**
1. **F2.1 (3-type classifier):** One LLM call per story. Feeds caption voice differentiation already partially implemented. No renderer changes.
2. **F2.2 (Reels Script Agent):** One new agent, one modal in web UI. No renderer changes. Highest ROI in v4.

**Phase 2B (Week 3) — Scoped-down additions**
3. **F2.3 simplified (This Week in AI only):** One new roundup template + multi-story input API. No other series.
4. **F2.4 simplified (teaser card only):** One new canvas size (1080×1920), simplified layout using existing Pillow renderer.

**Deferred to v5 (gate on 5K followers or F2.2 adoption data):**
- F2.1 extension: `opinion_hot_take` type + manual entry point in web UI
- F2.3 extension: "Worth It or Hype?" and "Hot Take" series
- F2.4 extension: insight card + poll/engagement card
- Close Friends / Broadcast Channels

---

## Part 6 — Risk Table Updates

The BRD's risk table is sound but two risks need updating:

| Risk | Original | Updated Assessment |
|---|---|---|
| Reels scripts feel generic | Medium likelihood | Mitigated by speakability rules + banned phrases in system prompt. The verdict-first structure for tool reviews and the "What this changes" ending for breaking news are the most important anti-generic signals. |
| Stories pipeline adds workflow overhead | Medium | **Resolved by scoping to 1 on-demand teaser card.** Zero marginal workflow overhead if generation is on-demand. |

**New risk to add:**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Classifier misroutes stories | Medium | Medium | 3-type system is significantly more accurate than 5-type. Log classifier decisions in Firestore. Add a "wrong type?" correction in web UI that re-routes and re-renders. |
| 5x/week posting causes quality drop | Medium | High | Set 3x as the floor, 5x as the ceiling. Track engagement rate per post — if it drops significantly when frequency increases, pull back. |

---

## Summary: What to Build in v4

### Build all of this
- ✅ F1.1 – F1.5 (all Phase 1 algorithm compliance fixes, as-is)
- ✅ F2.1 (content classifier, simplified to 3 types)
- ✅ F2.2 (Reels Script Agent, on-demand, with revised word counts + script formulas)
- ✅ F2.3 minimal ("This Week in AI" roundup only)
- ✅ F2.4 minimal (1 teaser Story card, on-demand)

### Don't build in v4
- ❌ F2.1 `opinion_hot_take` type — needs manual entry point, not classifier routing
- ❌ F2.3 "Worth It or Hype?" series — depends on F2.2 adoption data
- ❌ F2.3 "Hot Take" series — Reel-primary, premature without F2.2 baseline
- ❌ F2.4 insight card and poll/engagement card — poll ROI requires 5K+ follower community
- ❌ Broadcast Channels / Close Friends — premature at any sub-10K count

---
