"""Responsible, input-only advanced planning extensions."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import re
from math import ceil

from backend.utils.validators import StartupInputs


@dataclass(frozen=True)
class CompetitorRow:
    alternative: str
    known_from_user: str
    question_to_verify: str


def compare_user_alternatives(inputs: StartupInputs) -> list[CompetitorRow]:
    """Turn user-entered alternatives into research prompts, not factual claims."""
    alternatives = []
    for raw_item in inputs.alternatives.replace(",", "\n").splitlines():
        item = re.sub(r"\s+", " ", raw_item).strip().rstrip(".!?").strip()
        item = re.sub(r"^(?:and|or)\s+", "", item, flags=re.IGNORECASE)
        if item:
            alternatives.append(item)
    return [
        CompetitorRow(
            alternative=alternative,
            known_from_user="Listed by the user as an existing alternative; performance is unverified.",
            question_to_verify=f"What does the target customer like and dislike about {alternative}?",
        )
        for alternative in alternatives
    ]


def calculate_unit_economics(
    price_per_customer: float,
    variable_cost_per_customer: float,
    monthly_fixed_costs: float,
    expected_customers: int,
) -> pd.DataFrame:
    """Calculate transparent arithmetic from editable assumptions only."""
    contribution = price_per_customer - variable_cost_per_customer
    revenue = price_per_customer * expected_customers
    variable_costs = variable_cost_per_customer * expected_customers
    operating_result = revenue - variable_costs - monthly_fixed_costs
    exact_break_even = None if contribution <= 0 else monthly_fixed_costs / contribution
    whole_break_even = (
        f"Cannot reach break-even: contribution per customer is {contribution:.2f}."
        if exact_break_even is None
        else ceil(exact_break_even)
    )
    return pd.DataFrame(
        {
            "Metric": [
                "Revenue",
                "Variable costs",
                "Contribution margin",
                "Monthly fixed costs",
                "Operating result",
                "Exact break-even customers",
                "Required whole customers",
            ],
            "Value": [
                revenue,
                variable_costs,
                contribution * expected_customers,
                monthly_fixed_costs,
                operating_result,
                exact_break_even,
                whole_break_even,
            ],
        }
    )


def build_two_week_experiment_plan(inputs: StartupInputs) -> list[dict[str, str]]:
    """Create a small learning plan whose success criteria remain user-verifiable."""
    audience = inputs.target_customer.rstrip(".")
    return [
        {"Period": "Days 1-2", "Action": f"Recruit 5 people who match: {audience}.", "Evidence": "Five completed conversations or a documented recruitment blocker."},
        {"Period": "Days 3-5", "Action": "Ask about the last real occurrence, current workaround, and consequences.", "Evidence": "Repeated behaviors and verbatim pain points, not preferences alone."},
        {"Period": "Days 6-8", "Action": "Show a low-fidelity concept and ask the participant to attempt the core task.", "Evidence": "Observed completion, confusion points, and requested changes."},
        {"Period": "Days 9-11", "Action": "Offer a small manual pilot to willing participants.", "Evidence": "Sign-ups, attempted use, completion, and drop-off notes."},
        {"Period": "Days 12-14", "Action": "Review evidence and decide whether to refine, pause, or continue.", "Evidence": "A written decision linked to observed evidence; no threshold is assumed by the AI."},
    ]