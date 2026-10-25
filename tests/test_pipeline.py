import json
from types import SimpleNamespace

import pytest

from backend.config import Settings
from backend.core.pipeline import build_prompt, generate_concept
from backend.services.llm_service import ProviderError, generate_text
from backend.utils.validators import StartupInputs


@pytest.fixture
def inputs():
    return StartupInputs("Students need affordable meals.", "University students", "Bengaluru", "Low budget", "Canteen")


def test_prompt_contains_all_user_inputs(inputs):
    prompt = build_prompt(inputs)
    assert "Students need affordable meals." in prompt
    assert "Never invent market size" in prompt
    assert "Use a hypothesis or a question to validate" in prompt
    assert "smallest practical first version" in prompt
    assert "later-phase note" in prompt


def test_demo_pipeline_returns_required_sections(inputs):
    result = generate_concept(inputs, Settings(provider="demo"))
    assert result.mode == "Demo mode"
    assert result.concept_brief
    assert result.validation_checklist
    assert result.assumptions
    assert result.unverified


def test_demo_does_not_claim_verified_market_facts(inputs):
    result = generate_concept(inputs, Settings(provider="demo"))
    combined = " ".join(result.unverified).lower()
    assert "unverified" in combined


def test_unsupported_provider_fails_readably(inputs):
    with pytest.raises(ProviderError, match="Unsupported provider"):
        generate_text(build_prompt(inputs), Settings(provider="other", api_key="not-a-real-key"))


def test_malformed_provider_response_is_rejected(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: ("not json", "Test provider"),
    )
    with pytest.raises(ProviderError, match="unreadable response"):
        generate_concept(inputs, Settings(provider="mock"))


def test_invalid_provider_section_is_rejected(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: ('{"concept_brief": "brief"}', "Test provider"),
    )
    with pytest.raises(ProviderError, match="missing required planning sections"):
        generate_concept(inputs, Settings(provider="mock"))


def test_fenced_json_provider_response_is_accepted(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: ('```json\n{"concept_brief":"brief","value_proposition":"value","mvp_features":[],"risks":[],"interview_questions":[],"pitch_outline":[],"validation_checklist":[],"assumptions":[],"unverified":[]}\n```', "Test provider"),
    )
    result = generate_concept(inputs, Settings(provider="mock"))
    assert result.concept_brief == "brief"


def _valid_response(**overrides):
    response = {
        "concept_brief": "brief",
        "value_proposition": "value",
        "mvp_features": [],
        "risks": [],
        "interview_questions": [],
        "pitch_outline": [],
        "validation_checklist": [],
        "assumptions": [],
        "unverified": [],
    }
    response.update(overrides)
    return response


def test_json_list_response_is_rejected(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: ("[]", "Test provider"),
    )
    with pytest.raises(ProviderError, match="JSON object"):
        generate_concept(inputs, Settings(provider="mock"))


def test_wrong_section_type_is_rejected(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: (json.dumps(_valid_response(mvp_features=[1])), "Test provider"),
    )
    with pytest.raises(ProviderError, match="invalid section format"):
        generate_concept(inputs, Settings(provider="mock"))


def test_empty_provider_response_is_rejected(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: ("", "Test provider"),
    )
    with pytest.raises(ProviderError, match="empty response"):
        generate_concept(inputs, Settings(provider="mock"))


def test_valid_provider_response_becomes_generation_result(monkeypatch, inputs):
    monkeypatch.setattr(
        "backend.core.pipeline.generate_text",
        lambda prompt, settings: (json.dumps(_valid_response()), "Test provider"),
    )
    result = generate_concept(inputs, Settings(provider="mock"))
    assert result.value_proposition == "value"
    assert result.mode == "Test provider"


def test_groq_request_uses_structured_json(monkeypatch):
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content='{"ok": true}'),
                )],
            )

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("groq.Groq", FakeGroq)
    text, mode = generate_text("Return JSON.", Settings(provider="groq", api_key="test-key"))

    assert text == '{"ok": true}'
    assert mode == "Groq"
    assert calls[0]["model"] == "openai/gpt-oss-20b"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["reasoning_format"] == "hidden"


def test_groq_truncated_response_is_reported_safely(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    finish_reason="length",
                    message=SimpleNamespace(content="{"),
                )],
            )

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("groq.Groq", FakeGroq)
    with pytest.raises(ProviderError, match="incomplete response"):
        generate_text("Return JSON.", Settings(provider="groq", api_key="test-key"))


def test_groq_api_error_is_safe(monkeypatch):
    class FakeGroq:
        def __init__(self, **kwargs):
            raise RuntimeError("secret-key-value should not be shown")

    monkeypatch.setattr("groq.Groq", FakeGroq)
    with pytest.raises(ProviderError, match="AI provider was unavailable") as error:
        generate_text("Return JSON.", Settings(provider="groq", api_key="secret-key-value"))
    assert "secret-key-value" not in str(error.value)
