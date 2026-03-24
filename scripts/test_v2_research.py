#!/usr/bin/env python3
"""
v2 Research pipeline integration test.

Tests the full v2 path end-to-end (no server, no Telegram, no Firestore):
  1. ResearchOrchestrator — Exa + Tavily + Serper in parallel → Story objects
  2. ContentValidator     — relevance, freshness, dedup
  3. (Optional) PostCreator + CaptionWriter — if ANTHROPIC_API_KEY is set

Usage:
  python scripts/test_v2_research.py
  python scripts/test_v2_research.py --topic "Meta AI Llama 4 release"
  python scripts/test_v2_research.py --topic "AI agents" --skip-pipeline
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def run(topic: str, skip_pipeline: bool) -> None:
    from src.agents.research_orchestrator.orchestrator import ResearchOrchestrator, ResearchError
    from src.agents.content_validator.validator import ContentValidator

    print(f"\n{'='*60}")
    print(f"v2 Research Pipeline Test")
    print(f"Topic: {topic!r}")
    print(f"{'='*60}")

    # ── Step 1: Research ────────────────────────────────────────────────────
    print("\n[1/3] Running Research Orchestrator (Exa + Tavily + Serper)...")
    orchestrator = ResearchOrchestrator()
    try:
        stories = await orchestrator.run(topic)
    except ResearchError as e:
        print(f"  ERROR: {e}")
        print("  Make sure EXA_API_KEY, TAVILY_API_KEY, and SERPER_API_KEY are set in .env")
        return

    if not stories:
        print("  No stories returned — check API keys and topic")
        return

    print(f"  OK: {len(stories)} stories synthesised")
    for i, s in enumerate(stories, 1):
        print(f"\n  Story {i}: {s.headline}")
        print(f"    Source:  {s.source}")
        print(f"    URL:     {s.url}")
        print(f"    Stats:   {len(s.key_stats)} key stats")
        print(f"    Hook:    {s.hook_stat_value} — {s.hook_stat_label}")

    # ── Step 2: Validate ────────────────────────────────────────────────────
    print(f"\n[2/3] Running Content Validator...")
    validator = ContentValidator()
    results = await validator.run(topic, stories)

    passed = [r for r in results if r.passed]
    dropped = [r for r in results if not r.passed]
    stale = [r for r in results if r.stale_warning]

    print(f"  OK: {len(passed)} passed, {len(dropped)} dropped, {len(stale)} stale warnings")
    for r in dropped:
        print(f"  Dropped: {r.story.headline[:60]} — {r.drop_reason}")
    for r in stale:
        print(f"  Stale warning: {r.story.headline[:60]}")

    if not passed:
        print("  No stories passed validation — nothing to send to pipeline")
        return

    # ── Step 3: Pipeline (optional) ─────────────────────────────────────────
    if skip_pipeline:
        print(f"\n[3/3] Skipping pipeline (--skip-pipeline flag set)")
        print(f"\nDone. {len(passed)} stories ready for the carousel pipeline.")
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"\n[3/3] Skipping pipeline (ANTHROPIC_API_KEY not set)")
        print(f"\nDone. {len(passed)} stories ready for the carousel pipeline.")
        return

    print(f"\n[3/3] Running pipeline for {len(passed)} stories (PostCreator + CaptionWriter)...")

    from src.agents.post_creator.agent import PostCreatorAgent
    from src.agents.caption_writer.agent import CaptionWriterAgent

    creator = PostCreatorAgent()
    captioner = CaptionWriterAgent()

    for i, result in enumerate(passed, 1):
        story = result.story
        print(f"\n  Story {i}: {story.headline[:60]}")

        carousel = await creator.run(story)
        if carousel.success:
            print(f"    Carousel: ✅ {carousel.slide_count} slides")
            print(f"    Slides:   {carousel.export_urls[0].replace('file://', '')} ...")
        else:
            print(f"    Carousel: ❌ {carousel.error}")
            continue

        caption = await captioner.run(story, carousel)
        passed_val, issues = caption.is_valid()
        if passed_val:
            print(f"    Caption:  ✅ {len(caption.hashtags)} hashtags")
            print(f"    Hook:     {caption.hook[:80]}")
        else:
            print(f"    Caption:  ⚠️  {issues}")

    print(f"\n{'='*60}")
    print(f"Test complete.")
    print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the v2 research pipeline locally")
    parser.add_argument(
        "--topic",
        default="OpenAI latest AI model release 2025",
        help="Topic to research (default: OpenAI latest AI model release 2025)",
    )
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Stop after validation — skip PostCreator and CaptionWriter",
    )
    args = parser.parse_args()
    asyncio.run(run(args.topic, args.skip_pipeline))


if __name__ == "__main__":
    main()
