"""
Research Orchestrator — runs Exa, Tavily, and Serper in parallel for a given topic,
then uses Claude to synthesise the raw results into Story objects.

Inputs:  topic string (from Web UI)
Outputs: list[Story] — same schema as the newsletter parser output

Pipeline:
  1. Dispatch ExaAgent, TavilyAgent, SerperNewsAgent concurrently
  2. Aggregate all RawResults; deduplicate by URL
  3. LLM synthesis pass — produce 1-5 Story objects from aggregated content
  4. If all agents fail → raise ResearchError (caller handles UI feedback)
  5. If 1-2 agents fail → continue with available results, log partial failure
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass

import anthropic

from src.agents.research_orchestrator.exa_agent import ExaAgent, RawResult
from src.agents.research_orchestrator.serper_agent import SerperNewsAgent
from src.agents.research_orchestrator.tavily_agent import TavilyAgent
from src.utils.story import Story

logger = logging.getLogger(__name__)

MAX_STORIES_PER_TOPIC = 5


class ResearchError(Exception):
    """Raised when all research agents fail and no content is available."""
    pass


class ResearchOrchestrator:
    """
    Coordinates parallel research agents and synthesises results into Story objects.

    Inputs:  topic string
    Outputs: list[Story] (1-5 stories, same schema as v1 newsletter path)
    """

    def __init__(self):
        self._exa = ExaAgent()
        self._tavily = TavilyAgent()
        self._serper = SerperNewsAgent()
        self._llm = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def run(self, topic: str) -> list[Story]:
        """
        Research a topic and return Story objects ready for the carousel pipeline.

        Args:
            topic: Topic string entered by the owner in the Web UI.

        Returns:
            List of Story objects (1 to MAX_STORIES_PER_TOPIC).

        Raises:
            ResearchError: If all three agents return no results.
        """
        logger.info(f"ResearchOrchestrator: starting research for '{topic}'")

        # Step 1 — Run all three agents in parallel
        exa_results, tavily_results, serper_results = await asyncio.gather(
            self._exa.run(topic),
            self._tavily.run(topic),
            self._serper.run(topic),
            return_exceptions=True,
        )

        # Collect results, tolerate individual agent failures
        all_results: list[RawResult] = []
        agents_failed = 0

        for label, outcome in [("Exa", exa_results), ("Tavily", tavily_results), ("Serper", serper_results)]:
            if isinstance(outcome, Exception):
                logger.error(f"ResearchOrchestrator: {label} agent raised exception: {outcome}")
                agents_failed += 1
            elif not outcome:
                logger.warning(f"ResearchOrchestrator: {label} returned no results")
                agents_failed += 1
            else:
                all_results.extend(outcome)

        if agents_failed == 3:
            raise ResearchError(f"All research agents failed for topic: '{topic}'")

        if agents_failed > 0:
            logger.warning(f"ResearchOrchestrator: {agents_failed}/3 agents failed — continuing with {len(all_results)} results")

        # Step 2 — Deduplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[RawResult] = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        logger.info(f"ResearchOrchestrator: {len(unique_results)} unique results after dedup (from {len(all_results)} total)")

        # Step 3 — LLM synthesis into Story objects
        stories = await self._synthesise(topic, unique_results)
        logger.info(f"ResearchOrchestrator: synthesised {len(stories)} stories for '{topic}'")
        return stories

    async def _synthesise(self, topic: str, results: list[RawResult]) -> list[Story]:
        """
        Use Claude to synthesise raw research results into Story objects.

        Returns up to MAX_STORIES_PER_TOPIC stories. Each Story follows the
        same schema as the newsletter parser — feeding directly into the existing pipeline.
        """
        # Build a compact representation of the raw results for the prompt
        results_text = "\n\n".join(
            f"[{i+1}] SOURCE: {r.source_agent.upper()}\n"
            f"Title: {r.title}\n"
            f"URL: {r.url}\n"
            f"Date: {r.published_date or 'unknown'}\n"
            f"Content: {r.body[:800]}"
            for i, r in enumerate(results[:15])  # cap at 15 to avoid token overflow
        )

        prompt = f"""You are a content strategist for @techwithhareen — an Instagram page about Tech, AI, and Startups.

Topic the owner wants to post about: "{topic}"

Below are raw research results from multiple sources. Your job is to identify the {MAX_STORIES_PER_TOPIC} best distinct story angles for Instagram carousel posts.

RAW RESEARCH RESULTS:
{results_text}

For each story angle, extract:
- headline: concise hook headline (max 12 words, no punctuation at end)
- summary: 2-4 sentence summary of the key points, written for a tech-savvy Instagram audience
- url: the best source URL for this angle
- key_stats: list of 8-12 items. Each item must be formatted as "STAT HEADLINE\nOne sentence explanation." The headline is a punchy ALL CAPS fact or number (e.g. "1M TOKEN CONTEXT WINDOW"). The explanation adds one sentence of context (e.g. "Processes entire codebases and long documents in a single pass.")
- hook_stat_value: the single most shocking number or percentage (e.g. "70%", "$4B"). Max 5 chars.
- hook_stat_label: ALL CAPS context phrase for the number (e.g. "OF DEVELOPERS USE AI DAILY"). Max 6 words.
- image_query: a 3-5 word Google image search query for a relevant visual (e.g. "OpenAI GPT-5 robot")
- source: which agent found it ("exa", "tavily", or "serper")

Rules:
- Only include genuinely interesting, factual angles — skip vague or low-quality content
- Each angle must be meaningfully different from the others
- If the research only supports 1-2 good angles, return only those — don't pad
- Do not invent facts not present in the source material

Return a JSON array of story objects. Return ONLY valid JSON, no explanation."""

        try:
            response = self._llm.messages.create(
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
                headline = item.get("headline", "").strip()
                summary = item.get("summary", "").strip()
                if not headline or not summary:
                    continue
                stories.append(Story(
                    headline=headline,
                    summary=summary,
                    url=item.get("url"),
                    key_stats=item.get("key_stats", []),
                    hook_stat_value=item.get("hook_stat_value", "").strip(),
                    hook_stat_label=item.get("hook_stat_label", "").strip(),
                    image_query=item.get("image_query", headline),
                    source=item.get("source", "serper"),
                    topic=topic,
                ))

            return stories[:MAX_STORIES_PER_TOPIC]

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"ResearchOrchestrator: LLM synthesis failed: {e}")
            return []
