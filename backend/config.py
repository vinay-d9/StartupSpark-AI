"""Configuration and secret access for StartupSpark AI."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    provider: str = "demo"
    api_key: str | None = None
    model_name: str = "openai/gpt-oss-20b"
    timeout_seconds: float = 30.0


def _secret_value(name: str) -> str | None:
    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name)


def get_settings() -> Settings:
    provider = (_secret_value("LLM_PROVIDER") or "demo").strip().lower()
    api_key = _secret_value("GROQ_API_KEY")
    model_name = _secret_value("MODEL_NAME") or "openai/gpt-oss-20b"
    return Settings(provider=provider, api_key=api_key, model_name=model_name)
