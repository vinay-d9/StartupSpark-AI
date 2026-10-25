"""Input validation for the StartupSpark workflow."""

from __future__ import annotations

from dataclasses import dataclass


FIELDS = ("problem", "target_customer", "geography", "constraints", "alternatives")
MAX_FIELD_LENGTH = 2000


@dataclass(frozen=True)
class StartupInputs:
    problem: str
    target_customer: str
    geography: str
    constraints: str
    alternatives: str

    def as_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in FIELDS}


def validate_inputs(values: dict[str, str]) -> tuple[StartupInputs | None, list[str]]:
    errors: list[str] = []
    cleaned: dict[str, str] = {}
    labels = {
        "problem": "problem or rough idea",
        "target_customer": "target customer",
        "geography": "geography",
        "constraints": "constraints",
        "alternatives": "existing alternatives",
    }

    for field in FIELDS:
        value = str(values.get(field, "")).strip()
        if not value:
            errors.append(f"Enter the {labels[field]}.")
        elif len(value) > MAX_FIELD_LENGTH:
            errors.append(f"The {labels[field]} must be {MAX_FIELD_LENGTH} characters or fewer.")
        else:
            cleaned[field] = value

    if errors:
        return None, errors
    return StartupInputs(**cleaned), []
