---
date: 2026-03-24
topic: v3-features
---

# v3 Feature Set

## What We're Building

Three enhancements to the post creation and approval experience:

1. **Carousel Slide Editor** — edit slide text, add slides, reorder slides in the Web UI before approving
2. **Personal Touch in Captions** — context-aware voice layer in the Caption Writer agent
3. **Source Link CTA** — source URL in caption + "Read More" slide second-to-last

---

## Feature 1: Carousel Slide Editor

### What
Full slide editor in the Web UI (approval queue / Dashboard). After a post is generated, the owner can:
- Edit text on any existing slide
- Add new slides (content, quote, or CTA type)
- Reorder slides via drag-and-drop
- Save → backend re-renders all slides via Pillow → updated PNGs replace old ones in GCS

### Approach
Re-render on save. User edits the underlying slide data (not the PNG directly). On save, backend accepts updated slide data, Pillow regenerates all PNGs, new URLs written back to Firestore post document.

### Why This Approach
Keeps design 100% consistent with the UncoverAI system. No canvas overlay complexity on the frontend. Single source of truth stays in the backend renderer.

### Key Decisions
- Slide data structure needs to be persisted in Firestore (currently only PNG URLs are stored)
- Backend needs a new endpoint: `POST /api/v2/posts/{post_id}/slides` — accepts updated slide data, re-renders, returns new URLs
- Frontend: slide editor panel opens when user clicks "Edit Slides" on a PostCard

### Open Questions
- Should slide data be stored as-is from the LLM output, or normalized into a typed schema?
- Drag-and-drop library: react-beautiful-dnd or dnd-kit?

---

## Feature 2: Personal Touch in Captions

### What
The Caption Writer agent detects the story type and adds a context-aware personal voice layer on top of the existing hook + summary + CTA + hashtags format.

| Story Type | Voice Layer Added |
|---|---|
| Major news / announcement | Owner's opinion/take — "Here's what I think about this..." |
| Feature update / product release | Personal experience angle — "I tried this and..." |
| General info / explainer | Conversational tone, rhetorical questions to the audience |

### Approach
Add a "story type" classification step in the Caption Writer agent. LLM classifies the story (major_news / feature_update / general_info), then the caption prompt includes a persona instruction matching that type.

### Why This Approach
No new agent needed. One extra LLM pass inside Caption Writer. Story type classification is fast and cheap.

### Key Decisions
- Story type: auto-detected by LLM (not manually tagged by user)
- Persona instructions live in the Caption Writer prompt, not a separate config file
- Output format unchanged — personal touch is woven into existing sections

### Open Questions
- Should the owner be able to override the detected story type before approving?

---

## Feature 3: Source Link CTA

### What
Every post surfaces the original source URL in two places:

1. **Caption** — actual URL included + "Link in Description 🔗" nudge
2. **Second-to-last slide** — new "Read More" slide inserted before the final Follow/CTA slide, showing the source URL as text

### Approach
- Story object already carries a `url` field (from research agents). Pass it through to both Caption Writer and Post Creator.
- Caption Writer appends the URL + link nudge at the end of the caption (before hashtags).
- Post Creator inserts a "Read More" slide as the second-to-last slide in the carousel.

### Key Decisions
- URL placement in caption: after CTA line, before hashtags
- "Read More" slide design: matches UncoverAI style — black bg, accent URL text, simple layout
- If no source URL available (edge case): skip the Read More slide silently, omit from caption

---

## Next Steps
→ `/workflows:plan` for implementation details
