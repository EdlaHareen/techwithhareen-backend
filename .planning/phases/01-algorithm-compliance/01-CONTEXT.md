# Phase 1: Algorithm Compliance - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Update the caption writer and carousel renderer so every post leaving the system meets Instagram's 2025 algorithm requirements — correct hashtag count, background colour, CTA placement, and standalone hook copy.

</domain>

<decisions>
## Implementation Decisions

### Hashtag enforcement
- Enforce 3–5 hashtags via the LLM prompt — no post-processing trim needed
- Required mix: 1 branded (`#techwithhareen`) + 2 niche + 1–2 broad
- `#techwithhareen` instructed via prompt, not hardcoded in template
- If Post Analyzer catches a count violation: 1 auto-fix retry (regenerate caption), then skip + Telegram alert if still failing — consistent with existing retry logic

### Claude's Discretion
- BOOKMARK slide: exact position within 8+ slide carousels, visual design
- Caption hook validation: how to handle hooks over 120 chars (truncate vs regenerate)
- Slide 2 redesign: what replaces "SWIPE TO FIND OUT WHY" — phrase removal vs full slide rework
- Background colour enforcement: how to audit/fix any remaining #000000 slides

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the Claude's Discretion items above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-algorithm-compliance*
*Context gathered: 2026-03-25*
