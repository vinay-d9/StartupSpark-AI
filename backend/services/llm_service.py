"""LLM provider calls and deterministic demo fallback."""

from __future__ import annotations

from typing import Any

from backend.config import Settings


class ProviderError(RuntimeError):
    """Raised when a configured provider cannot generate a response."""


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
            max_tokens=1800,
            messages=[
                {
                    "role": "system",
                    "content": "You are a careful startup planning assistant. Follow the requested JSON schema and never invent verified facts.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "", "Groq"
    except Exception as exc:
        raise ProviderError("The AI provider was unavailable. Check your key, model, network, or rate limit.") from exc


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
