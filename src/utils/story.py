"""
Shared Story dataclass — used by all agents across both pipeline entry points.

Sources:
  "newsletter" — parsed from rundownai Gmail newsletter (v1 path)
  "exa"        — discovered via Exa semantic search (v2 path)
  "tavily"     — discovered via Tavily deep content extraction (v2 path)
  "serper"     — discovered via Serper Google News (v2 path)
"""

from dataclasses import dataclass, field
from typing import Literal, Optional

Source = Literal["newsletter", "exa", "tavily", "serper"]


@dataclass
class Story:
    """A single news story ready to enter the carousel/caption/analyzer pipeline."""

    # Core content
    headline: str
    summary: str
    url: Optional[str]

    # Carousel slide content
    key_stats: list[str] = field(default_factory=list)
    hook_stat_value: str = ""   # e.g. "70%" — shown large on content slide
    hook_stat_label: str = ""   # e.g. "OF SAMSUNG RAM GOES TO NVIDIA"

    # Provenance (v2 fields — optional for v1 newsletter path)
    source: Source = "newsletter"
    topic: Optional[str] = None         # topic entered in Web UI; None for newsletter path
    image_query: str = ""               # Serper image search query for content slide

    # Validation result (set by ContentValidator on v2 path)
    validation_passed: Optional[bool] = None
    validation_notes: str = ""

    # Content classification (set by ContentClassifier on v2 path; canonical field for Phase 2)
    # Values: "news" | "educational" | "news_and_announcements" | "tool_and_product" | None
    # Phase 2 classifier will SET this field — it does not add it.
    content_type: Optional[str] = None

    # Carousel format — set by TopicClarifierAgent for educational posts
    # Values: "A" (Mistakes→Right Way) | "B" (Pillars) | "C" (Cheat Sheet) | None (legacy step-by-step)
    carousel_format: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "headline": self.headline,
            "summary": self.summary,
            "url": self.url,
            "key_stats": self.key_stats,
            "hook_stat_value": self.hook_stat_value,
            "hook_stat_label": self.hook_stat_label,
            "source": self.source,
            "topic": self.topic,
            "image_query": self.image_query,
            "validation_passed": self.validation_passed,
            "validation_notes": self.validation_notes,
            "content_type": self.content_type,
            "carousel_format": self.carousel_format,
        }
