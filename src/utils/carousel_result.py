"""
CarouselResult — shared dataclass representing the output of the carousel renderer.

Used by PostCreatorAgent, CaptionWriterAgent, PostAnalyzerAgent, and the orchestrator.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CarouselResult:
    """Result from the carousel renderer."""

    design_id: str
    export_urls: list[str] = field(default_factory=list)
    slide_count: int = 0
    success: bool = True
    error: Optional[str] = None
