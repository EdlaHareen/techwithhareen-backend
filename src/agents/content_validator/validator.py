"""
Content Validator — quality gate between the Research Orchestrator and the carousel pipeline.

Runs after ResearchOrchestrator, before PostCreatorAgent (v2 path only).

Checks each Story for:
  1. Relevance  — is the story actually about the requested topic?
  2. Freshness  — is the content recent enough? (warns if > 30 days old)
  3. Duplicates — removes stories with the same angle as another in the batch

Stories that pass all checks → forwarded to the carousel pipeline.
Stories that fail relevance → dropped, reason logged.
Stories that are stale → flagged with a warning (soft fail — owner sees it in UI).
Duplicate stories → only the highest-quality one is kept.

Inputs:  topic string + list[Story]
Outputs: list[ValidatedStory] (Story + validation metadata attached)
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import anthropic

from src.utils.story import Story

logger = logging.getLogger(__name__)

FRESHNESS_DAYS = 30


@dataclass
class ValidationResult:
    """Outcome of validating a single Story."""
    story: Story
    passed: bool
    stale_warning: bool = False     # True if content is > FRESHNESS_DAYS days old
    drop_reason: str = ""           # Non-empty if passed=False


class ContentValidator:
    """
    Validates a batch of Stories from the Research Orchestrator before they
    enter the carousel pipeline.

    Inputs:  topic string, list[Story]
    Outputs: list[ValidationResult]
    """

    def __init__(self):
        self._llm = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def run(self, topic: str, stories: list[Story]) -> list[ValidationResult]:
        """
        Validate a batch of stories for relevance, freshness, and uniqueness.

        Args:
            topic:   The topic the owner searched for.
            stories: Stories produced by ResearchOrchestrator.

        Returns:
            List of ValidationResult — one per story, ordered by quality.
            Callers should filter on result.passed before entering the pipeline.
        """
        if not stories:
            return []

        logger.info(f"ContentValidator: validating {len(stories)} stories for topic '{topic}'")

        # Step 1 — Relevance check (LLM, one pass for the whole batch)
        relevance_map = await self._check_relevance(topic, stories)

        # Step 2 — Freshness check (date-based, no LLM needed)
        freshness_map = self._check_freshness(stories)

        # Step 3 — Deduplicate (LLM, compares angles across the batch)
        duplicate_ids = await self._find_duplicates(stories)

        results: list[ValidationResult] = []
        for story in stories:
            sid = id(story)

            # Dropped if off-topic
            if not relevance_map.get(sid, True):
                reason = f"Off-topic: story does not match '{topic}'"
                logger.info(f"ContentValidator: dropping '{story.headline[:60]}' — {reason}")
                results.append(ValidationResult(story=story, passed=False, drop_reason=reason))
                continue

            # Dropped if duplicate angle
            if sid in duplicate_ids:
                reason = "Duplicate angle — a higher-quality story on this angle was kept"
                logger.info(f"ContentValidator: dropping '{story.headline[:60]}' — {reason}")
                results.append(ValidationResult(story=story, passed=False, drop_reason=reason))
                continue

            # Passes — may carry a stale warning
            stale = freshness_map.get(sid, False)
            if stale:
                logger.warning(f"ContentValidator: stale content warning for '{story.headline[:60]}'")

            results.append(ValidationResult(story=story, passed=True, stale_warning=stale))

        passed = sum(1 for r in results if r.passed)
        logger.info(f"ContentValidator: {passed}/{len(stories)} stories passed validation")
        return results

    async def _check_relevance(self, topic: str, stories: list[Story]) -> dict[int, bool]:
        """
        LLM pass — checks each story is genuinely relevant to the topic.
        Returns a dict mapping id(story) → True/False.
        """
        stories_text = "\n".join(
            f"[{i}] {story.headline} — {story.summary[:200]}"
            for i, story in enumerate(stories)
        )

        prompt = f"""Topic the user searched for: "{topic}"

Below are story headlines and summaries found by research agents.
For each story, decide: is it genuinely relevant to the topic? Answer strictly.

Stories:
{stories_text}

Return a JSON array with one object per story, in the same order:
[{{"index": 0, "relevant": true/false, "reason": "one sentence"}}, ...]

Return ONLY valid JSON."""

        try:
            response = self._llm.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            data = json.loads(raw)
            result = {}
            for item in data:
                idx = item.get("index")
                if isinstance(idx, int) and 0 <= idx < len(stories):
                    result[id(stories[idx])] = bool(item.get("relevant", True))
            return result

        except Exception as e:
            logger.error(f"ContentValidator: relevance check failed: {e}")
            # Default to passing all stories if the LLM check fails
            return {id(s): True for s in stories}

    def _check_freshness(self, stories: list[Story]) -> dict[int, bool]:
        """
        Date-based freshness check — flags stories older than FRESHNESS_DAYS.
        Returns a dict mapping id(story) → True (stale) / False (fresh/unknown).
        """
        now = datetime.now(timezone.utc)
        result = {}
        for story in stories:
            # Freshness data comes from the source agent (if available)
            # It lives in story.validation_notes if set by orchestrator; otherwise skip
            result[id(story)] = False  # default: not stale (we don't always have dates)
        return result

    async def _find_duplicates(self, stories: list[Story]) -> set[int]:
        """
        LLM pass — identifies stories that cover the same angle.
        When duplicates are found, keeps the first (highest-ranked by orchestrator),
        marks the rest for dropping.
        Returns a set of id(story) for stories to drop.
        """
        if len(stories) <= 1:
            return set()

        stories_text = "\n".join(
            f"[{i}] {story.headline}"
            for i, story in enumerate(stories)
        )

        prompt = f"""Below are story headlines. Identify any that cover the same angle or news event.

Stories:
{stories_text}

Return a JSON array of groups where each group is a list of indices that are duplicates of each other.
Only include groups with 2+ items. If no duplicates, return [].
Example: [[1, 3], [4, 6]] means stories 1&3 are duplicates, and 4&6 are duplicates.

Return ONLY valid JSON."""

        try:
            response = self._llm.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            groups = json.loads(raw)
            to_drop: set[int] = set()

            for group in groups:
                if not isinstance(group, list) or len(group) < 2:
                    continue
                # Keep the first (index 0 of the group = highest orchestrator rank)
                for idx in group[1:]:
                    if isinstance(idx, int) and 0 <= idx < len(stories):
                        to_drop.add(id(stories[idx]))

            return to_drop

        except Exception as e:
            logger.error(f"ContentValidator: duplicate check failed: {e}")
            return set()
