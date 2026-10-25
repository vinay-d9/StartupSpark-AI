"""LLM provider calls and deterministic demo fallback."""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.config import Settings


class ProviderError(RuntimeError):
    """Raised when a configured provider cannot generate a response."""


logger = logging.getLogger(__name__)


def generate_text(prompt: str, settings: Settings) -> tuple[str, str]:
    """Return generated text and its mode label without exposing provider secrets."""
    if settings.provider in {"demo", "mock"} or not settings.api_key:
        return _demo_response(prompt), "Demo mode"

    if settings.provider != "groq":
        raise ProviderError(f"Unsupported provider '{settings.provider}'. Choose demo or groq.")

    try:
        from groq import Groq

        client = Groq(api_key=settings.api_key, timeout=settings.timeout_seconds)
        response = client.chat.completions.create(
            model=settings.model_name,
            temperature=0.2,
            max_completion_tokens=4096,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful startup planning assistant. Return only one valid JSON object, "
                        "with exactly these nine keys: concept_brief, value_proposition, mvp_features, risks, "
                        "interview_questions, pitch_outline, validation_checklist, assumptions, and unverified. "
                        "Use strings for the first two keys and arrays of strings for the remaining keys. "
                        "Do not use Markdown fences or add any other keys. Never invent verified facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            reasoning_format="hidden",
        )
        if response.choices[0].finish_reason == "length":
            raise ProviderError("The AI provider returned an incomplete response. Please try again.")
        return response.choices[0].message.content or "", "Groq"
    except ProviderError:
        raise
    except Exception as exc:
        error_details = _provider_error_details(exc)
        _log_provider_failure(settings, exc, error_details)
        if error_details["code"] == "json_validate_failed":
            raise ProviderError("The AI provider rejected the JSON response format. Please try again.") from exc
        raise ProviderError("The AI provider was unavailable. Check your key, model, network, or rate limit.") from exc


def _provider_error_details(exc: Exception) -> dict[str, str]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", {}) if response is not None else {}
    body = getattr(exc, "body", None)
    error_body = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error_body, dict):
        error_body = {}
    return {
        "code": _safe_metadata(error_body.get("code")),
        "type": _safe_metadata(error_body.get("type")),
        "parameter": _safe_metadata(error_body.get("param")),
        "request_id": _safe_metadata(
            getattr(exc, "request_id", None)
            or headers.get("x-request-id")
            or headers.get("request-id")
        ),
    }


def _log_provider_failure(
    settings: Settings,
    exc: Exception,
    error_details: dict[str, str],
) -> None:
    """Log provider diagnostics without exception text or request content."""
    logger.warning(
        "Groq request failed provider=%s model=%s provider_configured=%s "
        "api_key_present=%s exception_type=%s status_code=%s provider_code=%s "
        "provider_error_type=%s parameter=%s request_id=%s",
        settings.provider,
        settings.model_name,
        bool(settings.provider),
        bool(settings.api_key),
        type(exc).__name__,
        _safe_metadata(getattr(exc, "status_code", None)),
        error_details["code"],
        error_details["type"],
        error_details["parameter"],
        error_details["request_id"],
    )


def _safe_metadata(value: Any) -> str:
    """Keep diagnostic values short and limited to non-sensitive identifiers."""
    text = str(value) if value is not None else "unknown"
    return text if re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", text) else "redacted"


def _demo_response(prompt: str) -> str:
    """Provide an honest local response when no hosted provider is configured."""
    import json
    import re

    match = re.search(r"INPUTS_JSON:\s*(\{.*\})", prompt, re.DOTALL)
    inputs: dict[str, Any] = json.loads(match.group(1)) if match else {}
    problem = inputs.get("problem", "the stated problem")
    customer = inputs.get("target_customer", "the target customer")
    geography = inputs.get("geography", "the stated geography")
    alternatives = inputs.get("alternatives", "the listed alternatives")
    constraints = inputs.get("constraints", "the listed constraints")
    return json.dumps({
        "concept_brief": f"Help {customer} in {geography} address {problem}. User-provided inputs are the basis for this brief; market demand is unverified.",
        "value_proposition": f"A focused way for {customer} to make progress on {problem}, within {constraints}.",
        "mvp_features": ["A narrow intake or discovery flow", "One core outcome for the target customer", "A feedback capture step"],
        "risks": ["The problem may not be urgent enough to change behavior", "The listed alternatives may already solve the need", "The constraints may limit delivery quality"],
        "interview_questions": ["When did this problem last happen?", "How do you solve it today?", "What would make a new solution worth trying?"],
        "pitch_outline": ["Problem: the user-provided need", "Customer: the stated audience", "Solution: a narrow first workflow", "Proof plan: interviews and a small experiment"],
        "validation_checklist": ["Interview at least five people matching the target customer", "Ask for recent behavior rather than opinions", "Test a low-fidelity version of the core workflow", "Record evidence and revise the assumptions"],
        "assumptions": [f"The target customer experiences {problem} often enough to seek help", f"{alternatives} are relevant alternatives, not verified competitor facts"],
        "unverified": ["Demand, market size, competitor performance, costs, revenue, and financial projections are unverified."],
    }, ensure_ascii=True)
