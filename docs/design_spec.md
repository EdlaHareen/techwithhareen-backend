# @techwithhareen Carousel Design Spec
## Extracted from Canva template DAHDs0ivk0M

### Canvas
- Size: 1080 × 1350px (portrait 4:5)

### Colors
- Background: Dark charcoal gradient (~#1C1C1E → #252525), subtle noise texture
- Primary text: #FFFFFF (white, bold uppercase)
- Accent text: ~#C084FC / #A855F7 (bright purple/violet)
- Bullet markers: Same purple asterisk/star (❊ or ✳)

### Typography
- Style: Bold, ALL CAPS, tight tracking
- Font: Geometric sans-serif (Space Grotesk Bold or Barlow Condensed Bold — confirm)
- Accent lines (e.g. "DO YOU KNOW", "LET ME TELL YOU"): purple, ~48px
- Main headline: white, ~80–90px
- Body/stats text: white caps, ~28–32px
- Footer text: ~20px, muted white + purple

### Header (all slides)
- Top-left: X-shaped logo mark in purple + brand name "BrocelleTech" (→ replace with "@techwithhareen") in white, 2 lines
- Top-right: Circle with → arrow, white stroke

### Footer (all slides)
- Bottom-left: website URL (white/gray)
- Bottom-right: contact/CTA text (purple)

### Slide 1 — Cover
- Accent line: "DO YOU KNOW" (purple, large)
- Main text: [HOOK / HEADLINE] (white, very large bold uppercase, wraps 3–4 lines)
- Footer right: phone placeholder → replace with "#techwithhareen"

### Slide 2 — Teaser (evergreen, no dynamic content)
- Accent: "LET ME TELL YOU" (purple)
- Main: "CHECK THE NEXT SLIDE!" (white bold)
- Small decorative purple shape (stylized W/crown icon)

### Slide 3 — Content (dynamic)
- 3 bullet points, each:  ❊ [STAT TEXT IN CAPS] (white bold)
- Footer right: "and many more.." (purple)
- Optional: story-relevant image in background or corner

### Slide 4 — CTA (evergreen)
- Accent question: "STILL REFUSING TO ADAPT TO AI?" → replace with evergreen variant
- Main CTA: "FOLLOW FOR MORE INFORMATION!" (white bold)
- Decorative: geometric network lines (bottom right, subtle)

### Pipeline Plan
Replace canva_session.py with a Pillow-based renderer:
1. Load background texture PNG (pre-generated from the dark gradient)
2. Draw header (logo + brand name + arrow circle)
3. Draw dynamic text with correct fonts/colors per slide type
4. Draw footer
5. Composite story image (from Serper) on slide 3 as background/overlay
6. Output 4 PNGs (1080×1350) → these are the carousel_export_urls

Figma workflow (optional):
- Create Figma file with exact frames matching spec above
- Use Figma REST API to export frames as PNG base images
- Pillow composites only the dynamic text on top
