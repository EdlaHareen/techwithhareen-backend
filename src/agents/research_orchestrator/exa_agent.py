"""
Exa Agent — semantic search for topic research via Exa.ai.

Inputs:  topic string
Outputs: list of RawResult (title, body, url, published_date)

Exa specialises in semantic/concept search — great for finding articles,
Reddit threads, and thought-pieces related to a topic by meaning, not keywords.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

EXA_SEARCH_URL = "https://api.exa.ai/search"


@dataclass
class RawResult:
    """A single result from any research agent before synthesis."""
    title: str
    body: str
    url: str
    published_date: Optional[str] = None
    source_agent: str = "exa"


class ExaAgent:
    """
    Searches Exa.ai for semantically relevant content on a given topic.

    Inputs:  topic string
    Outputs: list[RawResult]
    """

    def __init__(self):
        self._api_key = os.environ.get("EXA_API_KEY", "")

    async def run(self, topic: str, num_results: int = 5) -> list[RawResult]:
        """
        Search Exa for articles relevant to the topic.

        Args:
            topic:       Topic string from the Web UI (e.g., "OpenAI GPT-5 release").
            num_results: Number of results to fetch.

        Returns:
            List of RawResult. Empty list on failure (non-blocking).
        """
        if not self._api_key:
            logger.warning("EXA_API_KEY not set — skipping Exa search")
            return []

        logger.info(f"ExaAgent: searching for '{topic}'")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    EXA_SEARCH_URL,
                    headers={
                        "x-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": topic,
                        "numResults": num_results,
                        "contents": {
                            "text": {"maxCharacters": 1500},
                        },
                        "type": "neural",
                        "useAutoprompt": True,
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("results", []):
                title = item.get("title", "").strip()
                body = (item.get("text") or "").strip()
                url = item.get("url", "").strip()
                if not title or not url:
                    continue
                results.append(RawResult(
                    title=title,
                    body=body,
                    url=url,
                    published_date=item.get("publishedDate"),
                    source_agent="exa",
                ))

            logger.info(f"ExaAgent: found {len(results)} results for '{topic}'")
            return results

        except httpx.HTTPError as e:
            logger.error(f"ExaAgent: HTTP error for '{topic}': {e}")
            return []
        except Exception as e:
            logger.error(f"ExaAgent: unexpected error for '{topic}': {e}", exc_info=True)
            return []
