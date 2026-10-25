import pandas as pd

from backend.core.extensions import (
    build_two_week_experiment_plan,
    calculate_unit_economics,
    compare_user_alternatives,
)
from backend.utils.validators import StartupInputs


def test_alternative_comparison_uses_only_user_entries():
    inputs = StartupInputs("Need", "Students", "Campus", "Low budget", "Canteen, Cooking at home, and college portals.")
    rows = compare_user_alternatives(inputs)
    assert [row.alternative for row in rows] == ["Canteen", "Cooking at home", "college portals"]
    assert all("unverified" in row.known_from_user for row in rows)


def test_unit_economics_calculates_editable_assumptions():
    table = calculate_unit_economics(10, 4, 100, 25)
    assert isinstance(table, pd.DataFrame)
    values = dict(zip(table["Metric"], table["Value"]))
    assert values["Revenue"] == 250
    assert values["Variable costs"] == 100
    assert values["Contribution margin"] == 150
    assert values["Operating result"] == 50
    assert values["Exact break-even customers"] == 100 / 6
    assert values["Required whole customers"] == 17


def test_unit_economics_handles_non_positive_contribution():
    table = calculate_unit_economics(4, 4, 100, 25)
    values = dict(zip(table["Metric"], table["Value"]))
    assert "Cannot reach break-even" in values["Required whole customers"]


def test_unit_economics_handles_negative_contribution():
    table = calculate_unit_economics(3, 4, 100, 25)
    values = dict(zip(table["Metric"], table["Value"]))
    assert "Cannot reach break-even" in values["Required whole customers"]


def test_experiment_plan_has_two_weeks_of_evidence_actions():
    inputs = StartupInputs("Need", "Student founders", "Campus", "Low budget", "Clubs")
    plan = build_two_week_experiment_plan(inputs)
    assert len(plan) == 5
    assert all(row["Evidence"] for row in plan)
    assert plan[0]["Action"].endswith(".")
    assert ".." not in plan[0]["Action"]
