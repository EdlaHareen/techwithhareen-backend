---
date: 2026-03-12
topic: insta-handler-manager
---

# @techwithhareen — Insta Handler Manager

## What We're Building

A cloud-hosted multi-agent system that autonomously runs the Instagram page **@techwithhareen** (AI Powered Feed for Tech + AI + Startups). It monitors Gmail for the daily rundownai newsletter, converts every story into a carousel post using Canva, runs it through a quality analyzer, then sends it to the owner via Telegram for one-tap approval before publishing immediately.

## Agent Architecture

```
Gmail Pub/Sub (rundownai arrives)
            ↓
[Content Fetching Agent]
 - Parse newsletter HTML
 - Extract all stories (no deduplication)
            ↓ (per story, parallel)
[Post Creator Subagent]  ←→  Canva MCP
 - Image Fetcher: Google Images → relevant image → upload to Canva
 - Build carousel: Cover → Teaser → Content slides (duped as needed) → CTA
 - Replace BrocelleTech → @techwithhareen throughout
            ↓
[Caption Writer Agent]
 - Hook line + 3-4 sentence summary + CTA + AI-generated hashtags
            ↓
[Post Analyzer Agent]
 - Design consistency, hook, hashtags, caption, CTA
 - 1 auto-fix retry → skip + Telegram alert if still failing
            ↓
[Telegram Bot]
 - Burst sends all posts at once for approval
 - Owner replies approve/reject per post
 - On approve → publish immediately
            ↓
[Publishing Module — TBD]
 - Instagram Graph API or manual export
```

## Why This Approach

Linear pipeline with human-in-the-loop approval keeps full automation benefits while maintaining brand quality. Parallel per-story processing keeps it fast. Dedicated agents per concern (content, creation, caption, analysis) makes each independently improvable.

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Trigger | Gmail Pub/Sub | Real-time, zero manual effort |
| Story coverage | All stories per newsletter | Maximum content output |
| Post format | Carousel, flexible slides (3-4 short / 6-7 deep) | Best engagement for educational content |
| Visuals | Same template background + Google Images per story | Consistent brand + relevant context |
| Template | Canva DAHDs0ivk0M (4 pages) | Existing design, just fill content |
| Caption | Dedicated Caption Writer Agent | Clean separation, independently improvable |
| Caption format | Hook + summary + CTA + hashtags | Proven engagement format |
| Hashtags | AI-generated per post | Contextually relevant |
| Analyzer failure | 1 auto-retry → skip + alert | No complex state machine |
| Deduplication | None — trust the source | Simplicity |
| Telegram mode | Burst all at once | User reviews on own time |
| Publish timing | Immediately on approval | No scheduling complexity |
| Infrastructure | GCP (Cloud Run + Pub/Sub + Firestore + Secret Manager) | Always-on, native Gmail integration |
| Publishing | TBD / pluggable | Unblocks rest of build |

## Canva Template Details

- **Template ID**: DAHDs0ivk0M
- **Slide 1 — Cover**: "Do you know... [hook question]?" + brand
- **Slide 2 — Teaser**: "Let me tell you / check next slide" (evergreen)
- **Slide 3 — Content**: Stats/key points, duplicate for more content
- **Slide 4 — CTA**: "Follow for more!" (evergreen)
- Replace `BrocelleTech` → `@techwithhareen` and `www.reallygreatsite.com` throughout

## Open Questions

- Which Instagram publishing method: Graph API vs manual export?
- Optimal number of content slides per story — any hard cap?
- Google Images API (Custom Search) or alternative image source?

## Next Steps

→ `/compound-engineering:workflows:plan` for implementation details
