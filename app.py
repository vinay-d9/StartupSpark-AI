"""Streamlit entry point for StartupSpark AI."""

from __future__ import annotations

import html

import streamlit as st

from backend.config import get_settings
from backend.core.extensions import build_two_week_experiment_plan, calculate_unit_economics, compare_user_alternatives
from backend.core.pipeline import generate_concept
from backend.services.llm_service import ProviderError
from backend.utils.validators import validate_inputs


def _format_economics_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "Not available"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{float(value):.2f}"


st.set_page_config(page_title="StartupSpark AI", page_icon="✦", layout="wide")

st.markdown("""
<style>
:root { --ink: #19231f; --mint: #d8f3e6; --coral: #f06f52; --paper: #f7f4ed; }
.stApp { background: var(--paper); color: var(--ink); }
.block-container { max-width: 1120px; padding-top: 4rem; }
.hero { background: var(--ink); color: #f8f4e8; padding: 2.2rem 2.4rem; border-radius: 6px; margin-bottom: 1.5rem; }
.hero h1 { font-size: clamp(2rem, 5vw, 4.4rem); line-height: 1.05; margin: 0 0 .8rem; padding-top: .15rem; letter-spacing: 0; overflow: visible; }
.hero p { max-width: 700px; font-size: 1.05rem; margin: 0; color: #d8e8de; }
[data-testid="stForm"] { border: 1px solid #d7ded7; border-radius: 6px; padding: 1.2rem; background: #fffdf8; }
.section { border-top: 3px solid var(--coral); padding-top: .65rem; margin-top: 1.8rem; }
.fact { background: var(--mint); border-left: 4px solid #2f7b58; padding: .8rem 1rem; border-radius: 3px; }
.notice { background: #fff1d6; border-left: 4px solid #d18a22; padding: .8rem 1rem; border-radius: 3px; }
.experiment-table-wrap { width: 100%; overflow-x: auto; }
.experiment-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: #fffdf8; }
.experiment-table th, .experiment-table td { border: 1px solid #d7ded7; padding: .7rem; text-align: left; vertical-align: top; overflow-wrap: anywhere; white-space: normal; }
.experiment-table th { background: var(--mint); }
.experiment-table th:first-child, .experiment-table td:first-child { width: 14%; }
.experiment-table th:nth-child(2), .experiment-table td:nth-child(2) { width: 43%; }
.experiment-table th:nth-child(3), .experiment-table td:nth-child(3) { width: 43%; }
.economics-table th:first-child, .economics-table td:first-child { width: 62%; }
.economics-table th:nth-child(2), .economics-table td:nth-child(2) { width: 38%; }
@media (max-width: 700px) {
    .block-container { padding-top: 2rem; }
    .hero { padding: 1.5rem; }
    .experiment-table { min-width: 560px; }
}
</style>
""", unsafe_allow_html=True)

if "generated" not in st.session_state:
    st.session_state.generated = None
if "startup_inputs" not in st.session_state:
    st.session_state.startup_inputs = None
if "reset_version" not in st.session_state:
    st.session_state.reset_version = 0

widget_suffix = str(st.session_state.reset_version)

st.markdown('<div class="hero"><h1>StartupSpark AI</h1><p>Turn a rough startup idea into a grounded concept brief, a first pitch, and a practical validation plan.</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.subheader("Build status")
    st.write("MVP workflow: ready")
    st.caption("The app separates your inputs, assumptions, and claims that still need verification.")
    st.divider()
    st.subheader("Provider mode")
    settings = get_settings()
    st.write("Demo mode" if settings.provider in {"demo", "mock"} or not settings.api_key else settings.provider.title())
    st.caption("Demo mode is deterministic and does not claim to be a live AI response.")

st.subheader("Start with the idea")
st.caption("Use specific, recent examples where possible. All five fields are required for a useful brief.")
with st.form(f"startup_form_{widget_suffix}"):
    problem = st.text_area("Problem or rough idea", placeholder="Students struggle to find affordable, healthy meals between classes.", key=f"problem_{widget_suffix}")
    col1, col2 = st.columns(2)
    with col1:
        target_customer = st.text_input("Target customer", placeholder="University students living off campus", key=f"target_customer_{widget_suffix}")
        geography = st.text_input("Geography", placeholder="One university campus in Bengaluru", key=f"geography_{widget_suffix}")
    with col2:
        constraints = st.text_area("Constraints", placeholder="Two founders, low budget, no delivery fleet", key=f"constraints_{widget_suffix}")
        alternatives = st.text_area("Existing alternatives", placeholder="Canteen, food delivery apps, cooking at home", key=f"alternatives_{widget_suffix}")
    submitted = st.form_submit_button("Generate concept brief", type="primary", width="stretch")

reset_col, status_col = st.columns([1, 4])
with reset_col:
    if st.button("Reset", width="stretch"):
        st.session_state.reset_version += 1
        st.session_state.generated = None
        st.session_state.startup_inputs = None
        st.rerun()

if submitted:
    values = {"problem": problem, "target_customer": target_customer, "geography": geography, "constraints": constraints, "alternatives": alternatives}
    inputs, errors = validate_inputs(values)
    if errors:
        for error in errors:
            st.error(error)
    else:
        with st.spinner("Structuring the idea and preparing validation questions..."):
            try:
                st.session_state.generated = generate_concept(inputs, settings)
                st.session_state.startup_inputs = inputs
            except ProviderError as exc:
                st.session_state.generated = None
                st.session_state.startup_inputs = None
                st.error(str(exc))

result = st.session_state.generated
saved_inputs = st.session_state.startup_inputs
if result and saved_inputs:
    st.divider()
    st.subheader("Your concept brief")
    st.caption(f"Generated in {result.mode}. Review every output before using it in a decision.")
    st.markdown(f'<div class="fact"><strong>Concept brief</strong><br>{result.concept_brief}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section"><h3>Inputs and interpretation</h3></div>', unsafe_allow_html=True)
    st.info("User-provided facts are the five entries above. They are not independently verified.")
    st.markdown("**Assumptions to test**")
    for item in result.assumptions:
        st.markdown(f"- {item}")
    st.markdown("**Still unverified**")
    for item in result.unverified:
        st.markdown(f"- {item}")

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section"><h3>Value proposition</h3></div>', unsafe_allow_html=True)
        st.write(result.value_proposition)
        st.markdown("**MVP features**")
        for item in result.mvp_features:
            st.markdown(f"- {item}")
        st.markdown("**Key risks**")
        for item in result.risks:
            st.markdown(f"- {item}")
    with right:
        st.markdown('<div class="section"><h3>Pitch outline</h3></div>', unsafe_allow_html=True)
        for item in result.pitch_outline:
            st.markdown(f"- {item}")
        st.markdown("**Customer interview questions**")
        for item in result.interview_questions:
            st.markdown(f"- {item}")

    st.markdown('<div class="section"><h3>Validation checklist</h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="notice">This checklist is a plan for learning, not proof that the business idea is validated.</div>', unsafe_allow_html=True)
    for item in result.validation_checklist:
        st.checkbox(item, key=f"check_{hash(item)}")

    st.markdown('<div class="section"><h3>Advanced extensions</h3></div>', unsafe_allow_html=True)
    st.caption("These tools use only your inputs or editable assumptions. They do not verify a market or predict financial performance.")
    competitor_tab, economics_tab, experiment_tab = st.tabs(["Alternative comparison", "Unit economics", "Two-week experiment"])
    with competitor_tab:
        st.info("Alternatives below come only from your input. Add real evidence during research before treating any comparison as factual.")
        for row in compare_user_alternatives(saved_inputs):
            st.markdown(f"**{row.alternative}**")
            st.write(row.known_from_user)
            st.caption(row.question_to_verify)
    with economics_tab:
        st.warning("All values are editable assumptions. Currency is intentionally unspecified.")
        econ_col1, econ_col2 = st.columns(2)
        with econ_col1:
            price = st.number_input("Price per customer", min_value=0.0, value=10.0, step=1.0)
            variable_cost = st.number_input("Variable cost per customer", min_value=0.0, value=4.0, step=1.0)
        with econ_col2:
            fixed_costs = st.number_input("Monthly fixed costs", min_value=0.0, value=100.0, step=10.0)
            customers = st.number_input("Expected customers this month", min_value=0, value=25, step=1)
        economics = calculate_unit_economics(price, variable_cost, fixed_costs, customers)
        economics_rows = "".join(
            f"<tr><td>{html.escape(str(row.Metric))}</td><td>{html.escape(_format_economics_value(row.Value))}</td></tr>"
            for row in economics.itertuples(index=False)
        )
        st.markdown(
            "<div class='experiment-table-wrap'><table class='experiment-table economics-table'>"
            "<thead><tr><th>Metric</th><th>Value</th></tr></thead>"
            f"<tbody>{economics_rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )
    with experiment_tab:
        st.info("Success means collecting evidence. No market threshold is assumed by the app.")
        plan = build_two_week_experiment_plan(saved_inputs)
        table_rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(row[column])}</td>" for column in ("Period", "Action", "Evidence")) + "</tr>"
            for row in plan
        )
        st.markdown(
            "<div class='experiment-table-wrap'><table class='experiment-table'>"
            "<thead><tr><th>Period</th><th>Action</th><th>Evidence</th></tr></thead>"
            f"<tbody>{table_rows}</tbody></table></div>",
            unsafe_allow_html=True,
        )

st.divider()
st.caption("StartupSpark AI is an educational planning assistant. It does not verify market facts, competitor claims, costs, revenue, or demand. Do not submit confidential or personal information.")
