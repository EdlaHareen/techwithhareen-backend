# Business Requirements Document — @techwithhareen v4
**Version:** 4.0
**Date:** 2026-03-25
**Owner:** Hareen Edla
**Status:** Draft

---

## 1. Executive Summary

@techwithhareen is an AI-powered Instagram page covering Tech, AI, and Startups. The system currently automates carousel post creation from two sources: the rundownai newsletter (v1) and a web UI topic research pipeline (v2). v3 added a slide editor and personal-voice captions.

Despite solid technical infrastructure, the content strategy scores **4/10** against 2025 Instagram best practices. The primary gaps are: zero Reels (missing the 2.25× reach engine), outdated hashtag usage (15–20 vs. the December 2025 cap of 3–5), CTAs optimised for saves rather than DM shares (Instagram's #1 algorithm signal), and 100% news aggregation with no evergreen or opinion content.

v4 addresses all of this. The goal is to evolve from a newsletter-to-carousel converter into a **full multi-format content engine** that produces carousels, Reels scripts, and Stories — posting 5× per week — with content classified by type and structured around recurring series that train the algorithm to categorise the account.

The Instagram AI education space is significantly less saturated than YouTube, X, or newsletters. Major AI voices (Matt Wolfe, The AI Solopreneur) have negligible Instagram presences. v4 is the build that captures that first-mover advantage before the window closes.

---

## 2. Business Objectives

| # | Objective | Rationale |
|---|-----------|-----------|
| B1 | Post 5× per week consistently | Buffer data: 3–5 weekly posts more than doubles follower growth vs. 1–2/week |
| B2 | Add Reels as a discovery format | Reels get 2.25× more reach than any other format; zero Reels = no discovery engine |
| B3 | Optimise for DM shares as the primary engagement signal | Instagram confirmed DM shares as the #1 algorithm signal (Jan 2025) |
| B4 | Diversify content mix to 40/40/20 | 100% news aggregation is penalised by the Dec 2025 algorithm update |
| B5 | Establish recurring content series | Series create appointment viewing + train the algorithm to classify the account |
| B6 | Fix algorithm compliance issues immediately | Hashtag count (15–20 → 3–5) and bg colour (#000 → #1A1A2E) are active penalties |

---

## 3. Current State

### What exists (v1–v3)

| Capability | Status |
|------------|--------|
| Newsletter → carousel pipeline | ✅ Live |
| Web UI topic research → carousel pipeline | ✅ Live |
| Pillow PNG carousel renderer (UncoverAI design) | ✅ Live |
| GCS upload + public URLs | ✅ Live |
| Personal-voice captions (Hareen's tone, 4 story types) | ✅ Live (v3) |
| Slide editor (edit/reorder/delete slides in web UI) | ✅ Live (v3) |
| Telegram approval | ✅ Live |
| Web UI approval queue | ✅ Live |
| Reels | ❌ Not started |
| Stories | ❌ Not started |
| Content type classification | ❌ Not started |
| Recurring series templates | ❌ Not started |

### Key gaps vs. 2025 Instagram best practices

| Gap | Current | Required | Business Impact |
|-----|---------|----------|-----------------|
| Reels production | 0 per week | 3 per week (50% of content) | Missing 2.25× reach multiplier |
| Hashtag count | 15–20 | 3–5 | Active distribution penalty since Dec 2025 |
| Background colour | #000000 | #1A1A2E | Text readability + aesthetic credibility |
| CTA strategy | Save / Follow | DM-share as primary | Missing #1 algorithm signal |
| Mid-carousel CTA | None | Slide 4–5 soft CTA | Two-CTA strategy = higher saves + shares |
| Caption hook (first 125 chars) | Not enforced | Standalone hook required | Instagram truncates before "...more" |
| Slide 2 as standalone hook | "SWIPE TO FIND OUT WHY" | Works for cold viewers | Re-shows from slide 2 to non-swipers |
| Content mix | 100% news | 40% timely / 40% evergreen / 20% opinion | Evergreen compounds saves over weeks |
| Recurring series | None | 3 series minimum | Algorithm micro-niche classification |
| Stories | None | 3–5 daily | Community retention + algorithm signals |

---

## 4. Success Metrics (6-Month Targets)

| Metric | Current Baseline | v4 Target | How Measured |
|--------|-----------------|-----------|--------------|
| Posts per week | 1–3 (variable) | 5 (consistent) | Instagram Insights |
| Reels per week | 0 | 3 | Instagram Insights |
| Engagement rate | Baseline TBD | 5%+ (AI/tech avg: 1.92%) | Instagram Insights |
| DM shares per carousel | Baseline TBD | 2× baseline | Instagram Insights |
| Save rate per carousel | Baseline TBD | 1.5× baseline | Instagram Insights |
| Hashtag count per post | 15–20 | 3–5 | Caption audit |
| Content mix compliance | 0% | 40/40/20 by Week 4 | Post tagging in system |

---

## 5. Stakeholder Requirements

**Hareen (sole operator):**
- Must still review and approve every post before it goes live — no autonomous publishing
- Web UI remains the primary approval interface; Telegram remains opt-in
- Workflow must not increase manual effort; ideally reduces it
- Reels scripts are generated for Hareen to record — the system writes, she speaks
- Series scheduling should be suggested by the system, not mandated

**Audience (AI-curious professionals, students, developers):**
- Want "signal not noise" — curated, explained content, not raw headlines
- Trust drops sharply with generic AI-written content; Hareen's voice must be present
- Evergreen content (tool guides, explainers) saves better than timely news
- DM-shareable content ("send this to someone who needs it") drives organic reach

---

## 6. Business Constraints

| Constraint | Detail |
|------------|--------|
| No autonomous publishing | All posts require Hareen's approval before going live |
| Budget | GCP free tier + existing API keys; no new paid infrastructure without explicit sign-off |
| Single operator | All workflows must be completable by one person (Hareen) without a team |
| Instagram Graph API | Not integrated (manual export + post); publishing remains manual through v4 |
| Content sourcing | Reels scripts are written by the system; recording is done by Hareen |
| No TikTok / YouTube Shorts | Instagram-only scope for v4 |

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Reels scripts feel generic / off-brand | Medium | High | Train script agent on Hareen's voice examples (same approach as caption agent) |
| Algorithm changes during v4 build | Low | Medium | Build against principles (DM shares, saves), not specific hacks |
| Content mix shift confuses existing audience | Low | Low | Introduce series gradually; keep breaking news as anchor |
| Stories pipeline adds workflow overhead | Medium | Medium | Make Stories optional / auto-generated from existing carousel content |

---

## 8. v4 Milestone Definition

v4 is complete when:
- [ ] Algorithm compliance fixes are live (hashtags, bg colour, CTA, slide 2, caption hook)
- [ ] Reels Script Agent produces approved scripts for 3 test stories
- [ ] Content type classifier routes stories to correct template
- [ ] 3 recurring series templates are live in the system
- [ ] Stories pipeline generates Story cards from approved carousels
- [ ] System can support a 5×/week posting schedule without increasing Hareen's manual workload beyond current approval time

---
