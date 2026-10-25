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
