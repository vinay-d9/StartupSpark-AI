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
    assert calls[0]["max_completion_tokens"] == 4096
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


def test_groq_api_error_is_safe_and_logs_metadata(monkeypatch, caplog):
    class FakeGroq:
        def __init__(self, **kwargs):
            error = RuntimeError("secret-key-value and private prompt should not be shown")
            error.status_code = 401
            error.body = {"error": {"code": "invalid_api_key", "type": "authentication_error"}}
            error.response = type("Response", (), {"headers": {"x-request-id": "req-123"}})()
            raise error

    monkeypatch.setattr("groq.Groq", FakeGroq)
    caplog.set_level("WARNING", logger="backend.services.llm_service")
    with pytest.raises(ProviderError, match="AI provider was unavailable") as error:
        generate_text("private prompt", Settings(provider="groq", api_key="secret-key-value"))
    assert "secret-key-value" not in str(error.value)
    assert "private prompt" not in caplog.text
    assert "secret-key-value" not in caplog.text
    assert "exception_type=RuntimeError" in caplog.text
    assert "status_code=401" in caplog.text
    assert "provider_code=invalid_api_key" in caplog.text
    assert "provider_error_type=authentication_error" in caplog.text
    assert "request_id=req-123" in caplog.text


def test_groq_json_validation_error_is_distinct(monkeypatch, caplog):
    class FakeGroq:
        def __init__(self, **kwargs):
            error = RuntimeError("private request content must not be logged")
            error.status_code = 400
            error.body = {
                "error": {
                    "code": "json_validate_failed",
                    "type": "invalid_request_error",
                    "param": "response_format",
                },
            }
            error.request_id = "req-json-123"
            raise error

    monkeypatch.setattr("groq.Groq", FakeGroq)
    caplog.set_level("WARNING", logger="backend.services.llm_service")
    with pytest.raises(ProviderError, match="rejected the JSON response format"):
        generate_text("private request content", Settings(provider="groq", api_key="test-key"))
    assert "provider_code=json_validate_failed" in caplog.text
    assert "provider_error_type=invalid_request_error" in caplog.text
    assert "parameter=response_format" in caplog.text
    assert "request_id=req-json-123" in caplog.text
    assert "private request content" not in caplog.text
