"""
Serper Agent — Google News search for topic research via Serper.dev.

Inputs:  topic string
Outputs: list of RawResult (title, body, url, published_date)

Serper is already in the stack for image fetching. Here it is repurposed
to hit the /news endpoint for current events and trending angles on a topic.
"""

import logging
import os

import httpx

from src.agents.research_orchestrator.exa_agent import RawResult

logger = logging.getLogger(__name__)

SERPER_NEWS_URL = "https://google.serper.dev/news"


class SerperNewsAgent:
    """
    Searches Google News via Serper.dev for recent coverage of a topic.

    Inputs:  topic string
    Outputs: list[RawResult]
    """

    def __init__(self):
        self._api_key = os.environ.get("SERPER_API_KEY", "")

    async def run(self, topic: str, num_results: int = 5) -> list[RawResult]:
        """
        Search Google News for recent articles on the topic.

        Args:
            topic:       Topic string from the Web UI.
            num_results: Number of results to fetch.

        Returns:
            List of RawResult. Empty list on failure (non-blocking).
        """
        if not self._api_key:
            logger.warning("SERPER_API_KEY not set — skipping Serper news search")
            return []

        logger.info(f"SerperNewsAgent: searching for '{topic}'")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    SERPER_NEWS_URL,
                    headers={
                        "X-API-KEY": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json={"q": topic, "num": num_results},
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("news", []):
                title = item.get("title", "").strip()
                body = item.get("snippet", "").strip()
                url = item.get("link", "").strip()
                if not title or not url:
                    continue
                results.append(RawResult(
                    title=title,
                    body=body,
                    url=url,
                    published_date=item.get("date"),
                    source_agent="serper",
                ))

            logger.info(f"SerperNewsAgent: found {len(results)} results for '{topic}'")
            return results

        except httpx.HTTPError as e:
            logger.error(f"SerperNewsAgent: HTTP error for '{topic}': {e}")
            return []
        except Exception as e:
            logger.error(f"SerperNewsAgent: unexpected error for '{topic}': {e}", exc_info=True)
            return []
