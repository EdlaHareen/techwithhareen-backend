---
date: 2026-04-04
topic: carousel-template-system
---

# Carousel Template System

## What We're Building

A template-based carousel system that separates **visual style** (template) from **content structure** (format). Users pick a template and format in the Web UI, type a topic, and the backend generates carousels using Pillow with the selected template's rendering config. Defaults are saved per-user in Firestore so you can just type a keyword and go.

## Why This Approach

The current system has a single fixed design (UncoverAI dark navy). Content quality issues stem partly from the text/copy generation, but also from only having one visual style — dark tech aesthetic doesn't suit every content type (e.g., listicles, tool roundups look better on clean/light backgrounds like @vishakha.sadhwani's style). Instead of moving to browser rendering (complex architectural shift), we keep Pillow and treat templates as rendering config objects (color palettes, font sets, layout params).

## Key Decisions

### Templates (visual style) and Formats (content structure) are separate choices
- **Template** = colors, fonts, backgrounds, accent style
- **Format** = what goes on each slide (news stats, mistakes/fixes, pillars, cheat sheet, listicle)
- Any template can render any format (template is a skin, format is the skeleton)

### Start with 2 templates
1. **Dark Tech** — existing UncoverAI design (navy #1A1A2E bg, periwinkle #8075FF accent, Anton + Inter fonts). Default for news content.
2. **Clean Light** — white/light gray bg, black text, colored accent highlights (red/blue per category), handwritten-style + bold sans fonts. Inspired by @vishakha.sadhwani. Default for educational/listicle content.

### Add "Listicle" as a new format
- Each slide = one specific tool/product/resource
- Structure per slide: number (#1, #2...) + tool name + logo + category pill + one-liner value prop + 3 bullet details with highlighted keywords
- Cover: personal framing ("My Favorite...", "Best tools for...")
- CTA: engagement-first ("Comment [KEYWORD] for links in DMs")
- Reference: @vishakha.sadhwani's GitHub repos post

### Defaults saved in Firestore
- Per-user preferences: `default_template` and `default_format`
- Stored in Firestore (not localStorage) — persists across devices
- Pre-selected in Web UI, user can override per post

### Rendering stays in Pillow (backend)
- Templates are Python config dicts (colors, fonts, spacings, layout rules)
- No browser rendering / html-to-image — stays within current architecture
- Template config passed to renderer alongside format and content

## Web UI Flow
1. Open web UI
2. Template selector (Dark Tech / Clean Light) — default pre-selected from Firestore
3. Format selector (News / Mistakes / Pillars / Cheat Sheet / Listicle) — default pre-selected
4. Type topic/keyword
5. Hit Generate
6. Backend uses selected template + format to render carousel PNGs

## Existing Formats (carried forward)
- **News** — cover + hook stat + content slides (4 stats per slide) + bookmark + read more + CTA
- **Format A: Mistakes** — cover + "MOST PEOPLE DO IT WRONG" + mistake/fix slides + bookmark + CTA
- **Format B: Pillars** — cover + hook stat + principle slides + bookmark + CTA
- **Format C: Cheat Sheet** — cover + "CHEAT SHEET" intro + 3-tips-per-slide batches + CTA (save)
- **NEW — Listicle** — cover + 1-tool-per-slide + CTA (comment keyword for DMs)

## Open Questions
- Should the LLM synthesis prompt adapt per template (not just format)? e.g., Clean Light might want more casual/personal copy tone
- Should template preview thumbnails be shown in the Web UI selector?
- How to handle tool logos in the Listicle format — Serper image search for "[tool name] logo"?
- Caption voice: does it change per template or stay Hareen's voice always?

## Next Steps
-> `/workflows:plan` for implementation details
