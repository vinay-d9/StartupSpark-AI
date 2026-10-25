"""StartupSpark-specific generation workflow."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from backend.config import Settings, get_settings
from backend.services.llm_service import ProviderError, generate_text
from backend.utils.validators import StartupInputs


@dataclass(frozen=True)
class GenerationResult:
    concept_brief: str
    value_proposition: str
    mvp_features: list[str]
    risks: list[str]
    interview_questions: list[str]
    pitch_outline: list[str]
    validation_checklist: list[str]
    assumptions: list[str]
    unverified: list[str]
    mode: str


def build_prompt(inputs: StartupInputs) -> str:
    return """Create a StartupSpark concept brief for an early-stage founder.
Return JSON with exactly these keys: concept_brief, value_proposition, mvp_features, risks,
interview_questions, pitch_outline, validation_checklist, assumptions, unverified.
Use arrays for every key except concept_brief and value_proposition. Ground all content in
INPUTS_JSON. Treat inputs as user-provided statements, not independently verified facts.
Never invent market size, competitor facts, costs, revenue, or financial projections.
Include practical customer-validation actions. Explicitly label assumptions and unverified items.
In pitch_outline, treat alternatives, competitors, market position, and uniqueness as unverified
unless supported by evidence in INPUTS_JSON; user-provided alternatives are not verified evidence.
Use a hypothesis or a question to validate instead of categorical claims such as "none provide"
or "no competitor offers".
Make MVP features the smallest practical first version for the supplied team, budget, staffing,
constraints, and timeline. Do not automatically recommend scraping or automated aggregation,
push notifications, personalized profiles, or admin interfaces when the inputs do not support
their implementation or operation. Put effort-heavy ideas in a later-phase note inside the
MVP features section instead of presenting them as required MVP functionality.

INPUTS_JSON: %s""" % json.dumps(inputs.as_dict(), ensure_ascii=True)


def generate_concept(inputs: StartupInputs, settings: Settings | None = None) -> GenerationResult:
    raw, mode = generate_text(build_prompt(inputs), settings or get_settings())
    if not isinstance(raw, str) or not raw.strip():
        raise ProviderError("The provider returned an empty response. Please try again.")
    try:
        data = json.loads(_clean_json_response(raw))
    except json.JSONDecodeError as exc:
        raise ProviderError("The provider returned an unreadable response. Please try again.") from exc

    if not isinstance(data, dict):
        raise ProviderError("The provider response must be a JSON object.")

    required = ("concept_brief", "value_proposition", "mvp_features", "risks", "interview_questions", "pitch_outline", "validation_checklist", "assumptions", "unverified")
    if any(key not in data for key in required):
        raise ProviderError("The provider response was missing required planning sections.")

    if not isinstance(data["concept_brief"], str) or not isinstance(data["value_proposition"], str):
        raise ProviderError("The provider returned an invalid text section format.")

    return GenerationResult(
        concept_brief=data["concept_brief"],
        value_proposition=data["value_proposition"],
        mvp_features=_as_list(data["mvp_features"]),
        risks=_as_list(data["risks"]),
        interview_questions=_as_list(data["interview_questions"]),
        pitch_outline=_as_list(data["pitch_outline"]),
        validation_checklist=_as_list(data["validation_checklist"]),
        assumptions=_as_list(data["assumptions"]),
        unverified=_as_list(data["unverified"]),
        mode=mode,
    )


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ProviderError("The provider returned an invalid section format.")
    return value


def _clean_json_response(raw: str) -> str:
    """Accept plain JSON or the fenced JSON commonly returned by chat models."""
    cleaned = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else cleaned
