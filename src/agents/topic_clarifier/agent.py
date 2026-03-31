"""
TopicClarifierAgent — generates dynamic clarifying questions before educational research fires.

Pipeline:
  1. Receives a topic string from the Web UI.
  2. Uses claude-sonnet-4-6 with extended thinking to generate 3-5 multiple-choice questions
     tailored to the topic, always including a format question (id="format", options A/B/C).
  3. Returns ClarifierResult with a list of ClarifierQuestion objects.

On any failure → caller should return hardcoded Format B defaults (never block the user).
"""

import json
import logging
from dataclasses import dataclass

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are generating clarifying questions for an Instagram educational post creator (@techwithhareen).

Given a topic, generate 3-5 multiple-choice questions that help determine:
1. The specific content angle (what aspect of the topic to focus on)
2. The target audience (who is this post for)
3. The carousel format (always required — A, B, or C)

Rules:
- Always include a question with id="format" and exactly these 3 options:
    A: "Mistakes → Right Way — what most people get wrong + the fix"
    B: "Core Concepts / Pillars — 3–5 key ideas, each slide standalone"
    C: "Cheat Sheet — dense tips, optimized for saves"
- Generate 2-4 additional questions tailored to the specific topic (angle, audience, depth, etc.)
- Total questions: 3-5 (including the format question)
- All questions are single-select multiple choice — no free-text answers
- Each question must have a "default" value (your recommended answer for this topic)
- Return ONLY valid JSON — no markdown fences, no explanation

JSON schema:
{
  "questions": [
    {
      "id": "string (short snake_case identifier)",
      "text": "string (the question as shown to the user)",
      "options": [
        {"value": "string", "label": "string"}
      ],
      "default": "string (value of the recommended option)"
    }
  ]
}
"""


@dataclass
class ClarifierOption:
    value: str
    label: str


@dataclass
class ClarifierQuestion:
    id: str
    text: str
    options: list[ClarifierOption]
    default: str


@dataclass
class ClarifierResult:
    questions: list[ClarifierQuestion]


class TopicClarifierAgent:
    """
    Generates dynamic multiple-choice clarifying questions for a given educational topic.

    Uses claude-sonnet-4-6 with extended thinking (budget_tokens=5000) so the model
    can reason about the best angle, audience, and format for the topic before
    generating questions.

    Usage::

        agent = TopicClarifierAgent()
        result = await agent.run("how to use Manus AI the right way")
        # result.questions — list of ClarifierQuestion
    """

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic()
        self._model = "claude-sonnet-4-6"

    async def run(self, topic: str) -> ClarifierResult:
        """
        Generate clarifying questions for a topic.

        Args:
            topic: The educational topic entered in the Web UI.

        Returns:
            ClarifierResult with 3-5 questions including the format question.

        Raises:
            ValueError: If the LLM returns malformed JSON or the format question is missing.
        """
        raw_data = await self._generate_questions(topic)
        questions = self._parse_questions(raw_data)
        return ClarifierResult(questions=questions)

    async def _generate_questions(self, topic: str) -> dict:
        """
        Call claude-sonnet-4-6 with extended thinking to generate questions.

        Returns parsed JSON dict. Raises ValueError on bad JSON.
        """
        user_prompt = f'Generate clarifying questions for this Instagram educational post topic: "{topic}"'

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=8000,
            thinking={
                "type": "enabled",
                "budget_tokens": 5000,
            },
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract text content block (skip thinking blocks)
        raw = ""
        for block in response.content:
            if block.type == "text":
                raw = block.text.strip()
                break

        if not raw:
            raise ValueError("TopicClarifierAgent: LLM returned no text content")

        # Strip markdown fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"TopicClarifierAgent: LLM returned invalid JSON: {exc}\nRaw: {raw[:300]}") from exc

        return data

    def _parse_questions(self, data: dict) -> list[ClarifierQuestion]:
        """
        Parse and validate the LLM response into ClarifierQuestion objects.

        Validates that the format question is present. Raises ValueError if missing.
        """
        questions_raw = data.get("questions", [])
        if not questions_raw:
            raise ValueError("TopicClarifierAgent: no questions in LLM response")

        questions: list[ClarifierQuestion] = []
        has_format_question = False

        for q in questions_raw:
            q_id = str(q.get("id", "")).strip()
            q_text = str(q.get("text", "")).strip()
            q_default = str(q.get("default", "")).strip()
            q_options_raw = q.get("options", [])

            if not q_id or not q_text or not q_options_raw:
                logger.warning("TopicClarifierAgent: skipping malformed question: %s", q)
                continue

            options = [
                ClarifierOption(
                    value=str(opt.get("value", "")).strip(),
                    label=str(opt.get("label", "")).strip(),
                )
                for opt in q_options_raw
                if opt.get("value") and opt.get("label")
            ]

            if not options:
                logger.warning("TopicClarifierAgent: skipping question with no valid options: %s", q_id)
                continue

            # Validate default is one of the option values
            option_values = {o.value for o in options}
            if q_default not in option_values:
                q_default = options[0].value
                logger.warning("TopicClarifierAgent: default not in options for %s — using first option", q_id)

            if q_id == "format":
                has_format_question = True

            questions.append(ClarifierQuestion(
                id=q_id,
                text=q_text,
                options=options,
                default=q_default,
            ))

        if not has_format_question:
            raise ValueError("TopicClarifierAgent: format question (id='format') missing from LLM response")

        return questions
