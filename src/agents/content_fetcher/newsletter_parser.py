"""
Newsletter parser — converts rundownai HTML email to structured Story objects.

Uses html2text to convert HTML → markdown, then Claude Haiku to extract
structured story data. This approach is resilient to DOM changes.
"""

import json
import logging
from typing import Optional

import anthropic
import html2text

from src.utils.story import Story

logger = logging.getLogger(__name__)


def html_to_markdown(html: str) -> str:
    """Convert newsletter HTML to clean markdown for LLM processing."""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.body_width = 0       # Disable line wrapping
    converter.ignore_images = True
    converter.ignore_emphasis = False
    return converter.handle(html)


def extract_stories_with_llm(markdown: str, client: anthropic.Anthropic) -> list[Story]:
    """
    Use Claude Haiku to extract structured stories from newsletter markdown.
    Haiku is fast + cheap — ideal for structured extraction tasks.
    """
    # Trim to avoid hitting token limits (newsletters are typically < 5000 tokens)
    trimmed = markdown[:10000]

    prompt = f"""Extract all news stories from this AI/tech newsletter.

For each story, extract:
- headline: the story title (concise, no punctuation at end)
- summary: 2-3 sentence summary of the key points
- url: the main source URL (or null if not present)
- key_stats: list of 8-12 items. Each item must be formatted as "STAT HEADLINE\nOne sentence explanation." The headline is a punchy ALL CAPS fact or number (e.g. "$4B RAISED IN SERIES B"). The explanation adds one sentence of context (e.g. "The round was led by Andreessen Horowitz at a $20B valuation.")
- hook_stat_value: the single most shocking number or percentage from the story (e.g. "70%", "$4B", "10x"). Short — 1-5 chars max.
- hook_stat_label: a short ALL CAPS phrase that gives the number context (e.g. "OF SAMSUNG RAM GOES TO NVIDIA", "RAISED IN SERIES B"). Max 6 words.

Return a JSON array of story objects. Only include genuine news stories — skip ads, footers, and navigation links.

Newsletter content:
{trimmed}

Return ONLY valid JSON, no explanation:"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        stories_data = json.loads(raw)
        stories = []
        for item in stories_data:
            story = Story(
                headline=item.get("headline", "").strip(),
                summary=item.get("summary", "").strip(),
                url=item.get("url"),
                key_stats=item.get("key_stats", []),
                hook_stat_value=item.get("hook_stat_value", "").strip(),
                hook_stat_label=item.get("hook_stat_label", "").strip(),
            )
            if story.headline and story.summary:
                stories.append(story)

        logger.info(f"Extracted {len(stories)} stories from newsletter")
        return stories

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse LLM story extraction: {e}")
        return []
