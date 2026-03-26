---
phase: 01-algorithm-compliance
verified: 2026-03-25T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "The DM-share CTA ('Send this to someone') is the primary CTA for all story types — both fallback code paths now use the correct CTA string"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Render a full carousel with 10 stats and visually inspect the bookmark slide"
    expected: "Accent-purple slide appears at roughly the mid-point of the carousel with 'BOOKMARK THIS' in large Anton type"
    why_human: "Pixel tests confirm the function is called and the correct number of slides is produced, but visual placement and legibility of the bookmark slide require human review"
  - test: "Generate a caption for a tool_feature story and inspect the CTA field"
    expected: "CTA contains 'Send this to someone who needs to see it 👇', not 'Follow @techwithhareen'"
    why_human: "LLM prompt instructs this but the LLM may not always comply — only a live generation run can confirm end-to-end CTA selection"
---

# Phase 1: Algorithm Compliance Verification Report

**Phase Goal:** Every post leaving the system complies with Instagram's 2025 algorithm best practices — correct hashtag count, background colour, CTA placement, and standalone hook copy.
**Verified:** 2026-03-25T00:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure

## Re-verification Summary

The single gap from the initial verification (ALGO-05 — DM-share CTA in all code paths) has been resolved. Both fallback paths in `src/agents/caption_writer/agent.py` now use `"Send this to someone who needs to see it 👇"`:

- **Line 182** (JSON field absent path): `data.get("cta", "Send this to someone who needs to see it 👇")` — old `"Follow @techwithhareen for daily AI updates ⚡"` default is gone.
- **Line 202** (exception path): `cta="Send this to someone who needs to see it 👇"` — old fallback string is gone.

The string `"Follow @techwithhareen"` does not appear anywhere in `caption_writer/agent.py` or `post_analyzer/agent.py`.

All 6 previously-passing items show no regression.

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Every carousel slide has a dark navy background (#1A1A2E), not pure black (#000000) | VERIFIED | `BG = (26, 26, 46)` at line 35 of `carousel_renderer.py`; `_black_canvas()` returns `Image.new("RGB", (W, H), BG)` |
| 2  | Carousels with 8 or more slides include a mid-carousel BOOKMARK THIS slide | VERIFIED | `_slide_bookmark()` at line 473; `has_bookmark = len(stat_chunks) >= 2` at line 579; injection at lines 594–595 |
| 3  | The final CTA slide says SEND THIS TO SOMEONE, not FOLLOW FOR MORE | VERIFIED | `lines_big = ["SEND THIS TO", "SOMEONE"]` at line 523; "FOLLOW FOR MORE" absent from source |
| 4  | Slide 2 contains the hook stat and a self-contained label — SWIPE TO FIND OUT WHY does not appear on any slide | VERIFIED | String "SWIPE TO FIND OUT WHY" absent from `carousel_renderer.py` source |
| 5  | Every generated caption contains exactly 3–5 hashtags (1 branded + 1–2 niche + 1–2 broad) | VERIFIED | `Caption.is_valid()` rejects count < 3 (line 97) and count > 5 (line 99); LLM prompt instructs "exactly 3–5 hashtags"; `_FALLBACK_HASHTAGS` has 3 entries |
| 6  | The DM-share CTA ("Send this to someone") is the primary CTA for all story types | VERIFIED | LLM prompt (line 144) instructs DM-share; `data.get("cta", "Send this to someone who needs to see it 👇")` at line 182; exception-path fallback `cta="Send this to someone who needs to see it 👇"` at line 202; "Follow @techwithhareen" absent from entire file |
| 7  | Caption validation rejects captions with fewer than 3 or more than 5 hashtags | VERIFIED | `Caption.is_valid()` lines 97–100 and `PostAnalyzerAgent._check_hashtags()` lines 149–152 both enforce the 3–5 range |
| 8  | Caption validation rejects hooks longer than 120 characters | VERIFIED | `Caption.is_valid()` lines 90–91; `PostAnalyzerAgent._check_hook()` lines 114–116 |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `src/utils/carousel_renderer.py` | Dark navy bg, bookmark slide, correct CTA copy, Slide 2 without swipe prompt | VERIFIED | `BG = (26, 26, 46)` at line 35; `_slide_bookmark()` at line 473; `lines_big = ["SEND THIS TO", "SOMEONE"]` at line 523; "SWIPE TO FIND OUT WHY" absent |
| `src/agents/caption_writer/agent.py` | 3–5 hashtag enforcement, 120-char hook constraint, DM-share primary CTA in all code paths | VERIFIED | Validation logic correct; LLM prompt correct; line 182 default and line 202 exception fallback both use DM-share CTA; "Follow @techwithhareen" absent |
| `src/agents/post_analyzer/agent.py` | Hashtag count validation (3–5) and hook length check (≤120) | VERIFIED | `_check_hashtags()` enforces count < 3 and count > 5; `_check_hook()` enforces length > 120 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `carousel_renderer.py` | `_black_canvas()` | `BG = (26, 26, 46)` replaces BLACK | WIRED | `return Image.new("RGB", (W, H), BG)` confirmed present |
| `carousel_renderer.py` | `render_carousel()` | `_slide_bookmark` injected when `len(stat_chunks) >= 2` | WIRED | Lines 579, 594–595 inject bookmark at halfway chunk |
| `carousel_renderer.py` | `_slide_cta()` | CTA text updated to SEND THIS TO SOMEONE | WIRED | `lines_big = ["SEND THIS TO", "SOMEONE"]` at line 523 |
| `caption_writer/agent.py` | `Caption.is_valid()` | Hashtag count check updated from `< 10` to `< 3 or > 5` | WIRED | Lines 97–100 confirmed |
| `post_analyzer/agent.py` | `_check_hashtags()` | Check enforces 3–5 range | WIRED | Lines 149–152 confirmed |
| `post_analyzer/agent.py` | `_check_hook()` | Hook length ≤120 enforced | WIRED | Lines 114–116 confirmed |
| `caption_writer/agent.py` | JSON-absent CTA default (line 182) | DM-share CTA is primary | WIRED | `data.get("cta", "Send this to someone who needs to see it 👇")` — gap CLOSED |
| `caption_writer/agent.py` | Exception-path Caption fallback (line 202) | DM-share CTA is primary | WIRED | `cta="Send this to someone who needs to see it 👇"` — gap CLOSED |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ALGO-01 | 01-02-PLAN | System generates exactly 3–5 hashtags per post | SATISFIED | `Caption.is_valid()` enforces range; LLM prompt instructs 3–5; `_FALLBACK_HASHTAGS` has 3 entries |
| ALGO-02 | 01-01-PLAN | All carousel slides render with `#1A1A2E` background | SATISFIED | `BG = (26, 26, 46)` used by `_black_canvas()` |
| ALGO-03 | 01-01-PLAN | Carousels with 8+ slides include a mid-carousel bookmark slide | SATISFIED | `_slide_bookmark()` exists and is injected when `len(stat_chunks) >= 2` |
| ALGO-04 | 01-01-PLAN | Final CTA slide says "SEND THIS TO SOMEONE" | SATISFIED | `lines_big = ["SEND THIS TO", "SOMEONE"]`; "FOLLOW FOR MORE" absent |
| ALGO-05 | 01-02-PLAN | Caption DM-share CTA is primary for news/tool stories | SATISFIED | LLM prompt correct; line 182 default fixed; line 202 exception fallback fixed; "Follow @techwithhareen" absent from entire file |
| ALGO-06 | 01-02-PLAN | Caption hook is ≤120 chars and grammatically complete standalone sentence | SATISFIED | Both validation layers enforce ≤120; LLM prompt instructs it; grammatical completeness left to LLM (needs human check) |
| ALGO-07 | 01-01-PLAN | Slide 2 hook stat is self-contained — "SWIPE TO FIND OUT WHY" removed | SATISFIED | String fully absent from source |

**All 7 requirements satisfied. No orphaned requirements.**

---

### Anti-Patterns Found

No blockers or warnings. The two previously-flagged anti-patterns (lines 182 and 202 of `caption_writer/agent.py`) have been resolved. No new anti-patterns introduced.

---

### Human Verification Required

#### 1. Bookmark Slide Visual Inspection

**Test:** Generate a carousel with at least 8 stats and open the output PNGs in sequence.
**Expected:** A slide appears at roughly the midpoint showing "BOOKMARK THIS" on an accent-purple (#8075FF) background in large Anton type, with "SAVE THIS FOR LATER" in smaller Inter SemiBold below.
**Why human:** Pixel tests confirm correct function call and slide count, but visual position, font rendering, and legibility require human review.

#### 2. End-to-End CTA Compliance on Happy Path

**Test:** Run a full v1 or v2 pipeline story through the caption writer with a tool_feature story type.
**Expected:** The generated caption's CTA field contains "Send this to someone who needs to see it 👇", not "Follow @techwithhareen".
**Why human:** The LLM prompt instructs DM-share as primary, but LLM compliance is probabilistic — a live generation run is needed to confirm the model follows the instruction. All code-level fallbacks are now correct; this check covers the happy-path LLM output only.

---

### Summary

All 7 must-haves are now verified at the code level. The single gap from the initial verification (ALGO-05 — DM-share CTA on error/fallback paths) is closed: both `data.get("cta", ...)` default (line 182) and the exception-path `Caption(cta=...)` constructor (line 202) now use `"Send this to someone who needs to see it 👇"`. The string `"Follow @techwithhareen for daily AI updates"` is absent from the entire caption writer file.

No regressions detected on the 6 previously-verified items. The phase goal is achieved at the implementation level. Two human verification items remain (visual bookmark slide legibility and live LLM CTA compliance) — these are observational checks, not code gaps.

---

_Verified: 2026-03-25T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
