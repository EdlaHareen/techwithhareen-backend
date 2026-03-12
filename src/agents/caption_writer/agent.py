"""
Caption Writer Agent — generates Instagram captions for each story.

Output format (strictly enforced):
  1. Hook line (punchy, no emoji)
  2. 3-4 sentence summary
  3. CTA ("Save this post 🔖" or "Follow @techwithhareen for daily AI updates")
  4. 15-20 AI/tech/startup hashtags (mix of high-volume + niche + branded)
"""

import json
import logging
import os
from dataclasses import dataclass, field

import anthropic

from src.agents.content_fetcher.newsletter_parser import Story
from src.utils.canva_session import CarouselResult

logger = logging.getLogger(__name__)

INSTAGRAM_MAX_CAPTION_LENGTH = 2200

BASE_HASHTAGS = [
    "#AI", "#ArtificialIntelligence", "#Tech", "#Technology",
    "#Startups", "#Innovation", "#techwithhareen",
]


@dataclass
class Caption:
    """Structured Instagram caption."""
    hook: str
    body: str
    cta: str
    hashtags: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        hashtag_line = " ".join(self.hashtags)
        return f"{self.hook}\n\n{self.body}\n\n{self.cta}\n\n{hashtag_line}"

    def is_valid(self) -> tuple[bool, list[str]]:
        """Validate caption meets all requirements. Returns (passed, issues)."""
        issues = []
        if not self.hook or len(self.hook.strip()) < 10:
            issues.append("Hook line is missing or too short")
        sentences = [s.strip() for s in self.body.split(".") if s.strip()]
        if len(sentences) < 3:
            issues.append(f"Body has only {len(sentences)} sentences — need at least 3")
        if not self.cta:
            issues.append("CTA is missing")
        if len(self.hashtags) < 10:
            issues.append(f"Only {len(self.hashtags)} hashtags — need at least 10")
        if len(self.full_text) > INSTAGRAM_MAX_CAPTION_LENGTH:
            issues.append(f"Caption is {len(self.full_text)} chars — exceeds Instagram 2,200 limit")
        return len(issues) == 0, issues


class CaptionWriterAgent:
    """Generates a structured Instagram caption for a story + carousel."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def run(self, story: Story, carousel: CarouselResult) -> Caption:
        """
        Generate an Instagram caption.

        Args:
            story: The news story being captioned.
            carousel: The carousel created for this story (used for context).

        Returns:
            Caption dataclass with all fields populated and validated.
        """
        logger.info(f"CaptionWriterAgent: writing caption for '{story.headline[:60]}'")

        prompt = f"""Write an Instagram caption for @techwithhareen — an AI-powered feed for Tech, AI, and Startups.

Story headline: {story.headline}
Story summary: {story.summary}
Key stats: {json.dumps(story.key_stats)}

Return a JSON object with these exact fields:
{{
  "hook": "One punchy sentence that grabs attention. No emoji. No hashtags.",
  "body": "3-4 sentences expanding on the story. Conversational, insightful, easy to read.",
  "cta": "Either 'Save this post 🔖' or 'Follow @techwithhareen for daily AI updates ⚡'",
  "hashtags": ["#AI", "#Tech", ... 15-20 total hashtags mixing high-volume + niche + branded]
}}

Hashtag rules:
- Include 3-4 story-specific niche tags (e.g., #MicrosoftCopilot, #OpenAI, #AIStartups)
- Include 5-6 mid-volume tags (#AITools, #TechNews, #FutureOfWork, #MachineLearning)
- Include 3-4 broad tags (#AI, #Tech, #Innovation, #Startups)
- Always include #techwithhareen
- Total: 15-20 hashtags

Return ONLY valid JSON."""

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            data = json.loads(raw)
            caption = Caption(
                hook=data.get("hook", "").strip(),
                body=data.get("body", "").strip(),
                cta=data.get("cta", "Follow @techwithhareen for daily AI updates ⚡").strip(),
                hashtags=data.get("hashtags", BASE_HASHTAGS),
            )

            passed, issues = caption.is_valid()
            if not passed:
                logger.warning(f"Caption validation issues: {issues}")
            else:
                logger.info("CaptionWriterAgent: ✅ caption validated successfully")

            return caption

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Caption generation failed: {e}")
            # Return a minimal fallback caption
            return Caption(
                hook=story.headline,
                body=story.summary,
                cta="Follow @techwithhareen for daily AI updates ⚡",
                hashtags=BASE_HASHTAGS,
            )
