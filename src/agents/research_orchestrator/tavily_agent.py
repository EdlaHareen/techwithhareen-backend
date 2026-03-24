"""
Tavily Agent — deep content extraction for topic research via Tavily.

Inputs:  topic string
Outputs: list of RawResult (title, body, url, published_date)

Tavily specialises in extracting full article content — ideal for feeding
detailed source material to the LLM synthesis step.
"""

import logging
import os
from typing import Optional

import httpx

from src.agents.research_orchestrator.exa_agent import RawResult

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyAgent:
    """
    Searches Tavily for deeply extracted article content on a given topic.

    Inputs:  topic string
    Outputs: list[RawResult]
    """

    def __init__(self):
        self._api_key = os.environ.get("TAVILY_API_KEY", "")

    async def run(self, topic: str, num_results: int = 5) -> list[RawResult]:
        """
        Search Tavily for articles and extract their content.

        Args:
            topic:       Topic string from the Web UI.
            num_results: Number of results to fetch.

        Returns:
            List of RawResult. Empty list on failure (non-blocking).
        """
        if not self._api_key:
            logger.warning("TAVILY_API_KEY not set — skipping Tavily search")
            return []

        logger.info(f"TavilyAgent: searching for '{topic}'")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    TAVILY_SEARCH_URL,
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self._api_key,
                        "query": topic,
                        "max_results": num_results,
                        "search_depth": "advanced",
                        "include_raw_content": False,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("results", []):
                title = item.get("title", "").strip()
                body = item.get("content", "").strip()
                url = item.get("url", "").strip()
                if not title or not url:
                    continue
                results.append(RawResult(
                    title=title,
                    body=body,
                    url=url,
                    published_date=item.get("published_date"),
                    source_agent="tavily",
                ))

            logger.info(f"TavilyAgent: found {len(results)} results for '{topic}'")
            return results

        except httpx.HTTPError as e:
            logger.error(f"TavilyAgent: HTTP error for '{topic}': {e}")
            return []
        except Exception as e:
            logger.error(f"TavilyAgent: unexpected error for '{topic}': {e}", exc_info=True)
            return []
