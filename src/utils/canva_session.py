"""
Canva Session Manager — uses claude-agent-sdk to drive Canva MCP tools.

Since Canva MCP tools are LLM-dispatched (not directly callable from Python),
we spawn a Claude agent session with the Canva MCP server enabled and instruct
Claude to perform carousel creation via natural language.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

CANVA_TEMPLATE_ID = os.environ.get("CANVA_TEMPLATE_ID", "DAHDs0ivk0M")
BRAND_NAME = "@techwithhareen"
BRAND_WEBSITE = "techwithhareen"
TEMPLATE_BRAND_PLACEHOLDER = "BrocelleTech"
TEMPLATE_WEBSITE_PLACEHOLDER = "www.reallygreatsite.com"


@dataclass
class CarouselResult:
    """Result from Post Creator Agent."""
    design_id: str
    export_urls: list[str] = field(default_factory=list)
    slide_count: int = 0
    success: bool = True
    error: Optional[str] = None


def build_carousel_prompt(
    headline: str,
    key_stats: list[str],
    image_url: Optional[str],
) -> str:
    """
    Build the natural language prompt sent to Claude + Canva MCP session.
    """
    stats_text = "\n".join(f"- {stat}" for stat in key_stats)
    image_instruction = (
        f"\n5. Add this image to the content slide(s): {image_url}"
        if image_url
        else "\n5. No image to add — keep the content slide background as-is."
    )

    # Determine how many content slides to create based on stat count
    extra_slides = ""
    if len(key_stats) > 3:
        extra_slides = (
            f"\n   Duplicate slide 3 as many times as needed to fit all {len(key_stats)} stats "
            f"(3 stats per slide maximum)."
        )

    return f"""Open Canva design {CANVA_TEMPLATE_ID}. Make the following changes carefully:

1. On ALL slides: Replace every instance of "{TEMPLATE_BRAND_PLACEHOLDER}" with "{BRAND_NAME}".
   Replace every instance of "{TEMPLATE_WEBSITE_PLACEHOLDER}" with "{BRAND_WEBSITE}".

2. Slide 1 (Cover slide — the "Do you know" slide):
   Update the hook text to: "Do you know {headline}?"
   Keep all other design elements the same.

3. Slide 2 (Teaser slide — "Let me tell you"):
   Keep as-is. No changes needed.

4. Slide 3 (Content slide — stats/bullet points):
   Replace the existing stats/bullet points with these:
{stats_text}{extra_slides}
{image_instruction}

6. Slide 4 (CTA slide — "Follow for more"):
   Keep as-is. No changes needed.

7. After all edits are complete, export ALL slides as PNG images.

Please complete all steps and confirm when the export is done."""


async def create_carousel(
    headline: str,
    key_stats: list[str],
    image_url: Optional[str] = None,
) -> CarouselResult:
    """
    Create an Instagram carousel in Canva using claude-agent-sdk + Canva MCP.

    Spawns a Claude agent session with Canva MCP tools and instructs it to:
    1. Open the template
    2. Fill in story content
    3. Replace brand placeholders
    4. Export as PNG

    Returns CarouselResult with export URLs.
    """
    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions  # type: ignore

        options = ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            system_prompt=(
                "You are a Canva design assistant. Your job is to open a Canva template, "
                "make the specified text changes, and export the slides. "
                "Follow instructions precisely. After exporting, list all exported PNG URLs."
            ),
            mcp_servers={
                "canva": {
                    "command": "npx",
                    "args": ["@canva/cli@latest", "mcp"],
                    "type": "stdio",
                }
            },
            allowed_tools=["mcp__canva__*"],
        )

        prompt = build_carousel_prompt(headline, key_stats, image_url)
        export_urls = []
        design_id = CANVA_TEMPLATE_ID

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                # Extract export URLs from agent response text
                text = getattr(message, "text", "") or ""
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("http") and (".png" in line.lower() or "export" in line.lower()):
                        export_urls.append(line)
                    # Try to extract design ID if agent mentions it
                    if "design" in line.lower() and "DAH" in line:
                        for word in line.split():
                            if word.startswith("DAH"):
                                design_id = word.strip(".,\"'")

        logger.info(
            f"Carousel created for '{headline[:50]}': "
            f"{len(export_urls)} slides exported, design_id={design_id}"
        )

        return CarouselResult(
            design_id=design_id,
            export_urls=export_urls,
            slide_count=len(export_urls),
            success=True,
        )

    except Exception as e:
        logger.error(f"Canva session failed for '{headline[:50]}': {e}", exc_info=True)
        return CarouselResult(
            design_id=CANVA_TEMPLATE_ID,
            export_urls=[],
            slide_count=0,
            success=False,
            error=str(e),
        )
