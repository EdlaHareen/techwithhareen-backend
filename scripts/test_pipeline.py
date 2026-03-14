#!/usr/bin/env python3
"""
Local pipeline test — runs one story through:
  1. Image search (Serper) — optional, skipped if SERPER_API_KEY not set
  2. Carousel render (Pillow)
  3. Caption writer (Anthropic)
  4. Post analyzer (Anthropic)

No server, no Telegram, no Gmail required.
Opens generated slides in your default image viewer.

Usage:
  python scripts/test_pipeline.py
  python scripts/test_pipeline.py --headline "Your headline" --summary "Your summary"
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Make src importable from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


SAMPLE_HEADLINE = "OpenAI just launched GPT-5 and it's 10x cheaper than GPT-4"
SAMPLE_SUMMARY = (
    "OpenAI announced GPT-5 today, claiming it scores 95% on the MMLU benchmark, "
    "supports real-time voice and vision in a single model, and costs 10x less per token "
    "than GPT-4. It's rolling out to all ChatGPT users starting today."
)
SAMPLE_STATS = [
    "GPT-5 scores 95% on MMLU benchmark",
    "10x cheaper than GPT-4 per token",
    "Real-time voice + vision in one model",
    "Available to all ChatGPT users on day 1",
]


def open_images(paths: list[str]) -> None:
    """Open PNGs in the default viewer (macOS: Preview, Linux: xdg-open)."""
    if sys.platform == "darwin":
        subprocess.run(["open"] + paths)
    else:
        for p in paths:
            subprocess.run(["xdg-open", p])


async def run(headline: str, summary: str) -> None:
    from src.agents.content_fetcher.newsletter_parser import Story
    from src.agents.post_creator.image_fetcher import build_image_query, search_image
    from src.utils.carousel_renderer import render_carousel
    from src.utils.canva_session import create_carousel

    story = Story(headline=headline, summary=summary, url="https://example.com")

    # ── Step 1: Image search ────────────────────────────────────────────────
    print("\n[1/4] Image search...")
    image_url = None
    if os.environ.get("SERPER_API_KEY"):
        query = build_image_query(headline)
        image_url = await search_image(query)
        print(f"  Image URL: {image_url or '(not found)'}")
    else:
        print("  SERPER_API_KEY not set — skipping image search")

    # ── Step 2: Carousel render ─────────────────────────────────────────────
    print("\n[2/4] Rendering carousel...")
    carousel = await create_carousel(
        headline=headline,
        key_stats=SAMPLE_STATS if story.key_stats == [] else (story.key_stats or SAMPLE_STATS),
        image_url=image_url,
        hook_stat_value=story.hook_stat_value or "10x",
        hook_stat_label=story.hook_stat_label or "CHEAPER THAN GPT-4 PER TOKEN",
    )
    if not carousel.success:
        print(f"  ERROR: {carousel.error}")
        return

    print(f"  OK: {carousel.slide_count} slides → {carousel.export_urls[0].replace('file://', '')} ...")
    slide_paths = [url.replace("file://", "") for url in carousel.export_urls]

    # ── Step 3: Caption writer ──────────────────────────────────────────────
    caption = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("\n[3/4] Writing caption...")
        from src.agents.caption_writer.agent import CaptionWriterAgent
        caption = await CaptionWriterAgent().run(story, carousel)
        print(f"  Hook: {caption.hook}")
        print(f"  CTA:  {caption.cta}")
        print(f"  Hashtags ({len(caption.hashtags)}): {' '.join(caption.hashtags[:5])} ...")
    else:
        print("\n[3/4] ANTHROPIC_API_KEY not set — skipping caption writer")

    # ── Step 4: Post analyzer ───────────────────────────────────────────────
    if os.environ.get("ANTHROPIC_API_KEY") and caption:
        print("\n[4/4] Running post analyzer...")
        from src.agents.post_analyzer.agent import PostAnalyzerAgent
        analysis = await PostAnalyzerAgent().run(story, carousel, caption)
        status = "✅ PASSED" if analysis.passed else f"❌ FAILED — {analysis.issues}"
        print(f"  {status}")
    else:
        print("\n[4/4] Skipping post analyzer (no caption or API key)")

    # ── Show slides ─────────────────────────────────────────────────────────
    print(f"\nOpening {len(slide_paths)} slides...")
    open_images(slide_paths)
    print("\nDone. Slide files:")
    for p in slide_paths:
        print(f"  {p}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the carousel pipeline locally")
    parser.add_argument("--headline", default=SAMPLE_HEADLINE)
    parser.add_argument("--summary", default=SAMPLE_SUMMARY)
    args = parser.parse_args()

    asyncio.run(run(args.headline, args.summary))


if __name__ == "__main__":
    main()
