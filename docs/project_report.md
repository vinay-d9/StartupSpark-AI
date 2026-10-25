# StartupSpark AI Project Report

## 1. Problem and users

Student innovators and entrepreneurship clubs often have a rough idea but need help turning it into a problem statement, target customer, value proposition, and learning plan. StartupSpark AI is an educational planning assistant for that early structuring step.

## 2. Objectives and success criteria

The MVP succeeds when a user can enter five required inputs, receive a readable concept brief, see assumptions separated from user-provided statements, and leave with practical customer-validation actions. It must also fail clearly when inputs or the provider are unavailable.

## 3. User scenarios

1. A student enters a campus-food idea and receives a first concept brief and interview questions.
2. An entrepreneurship club member compares user-listed alternatives without being shown invented competitor facts.
3. A founder tests editable unit assumptions and creates a two-week evidence-gathering plan without mistaking arithmetic or AI text for validation.

## 4. Scope

The MVP includes input collection, validation, generation, structured output, demo mode, optional Groq mode, and error handling. The implemented secondary extensions are user-input-only alternative comparison, editable unit economics, and a two-week experiment template. Authentication, databases, uploads, payments, dashboards, and separate APIs are out of scope.

## 5. Architecture and data flow

`app.py` collects inputs -> `validators.py` validates them -> `pipeline.py` builds the StartupSpark prompt -> `llm_service.py` calls Groq or the explicit demo fallback -> the result schema is validated -> Streamlit renders the brief and extensions.

The model prompt requires JSON sections, grounds content in the five inputs, labels assumptions and unverified information, and prohibits invented market size, competitor facts, costs, revenue, and financial projections.

## 6. Modules

- `app.py`: Streamlit page, forms, loading/error states, reset, and result presentation.
- `backend/config.py`: Streamlit secrets and environment configuration.
- `backend/utils/validators.py`: required-field and maximum-length validation.
- `backend/core/pipeline.py`: prompt construction, provider response parsing, and output schema checks.
- `backend/services/llm_service.py`: Groq adapter, timeout, provider errors, and demo response.
- `backend/core/extensions.py`: responsible advanced planning tools.
- `tests/`: automated behavior checks.

## 7. Testing and results

The local suite contains 18 tests covering normal, empty, oversized, ambiguous/extra-field, provider-error, malformed-output, unverified-claim, competitor-input, unit-economics, experiment-plan, and Streamlit UI cases. Observed result on 2026-10-25: `18 passed in 0.85s` under Python 3.14.7. A browser smoke check also verified the home page, empty validation messages, and successful demo generation.

Manual checks still required before a final submission include browser interaction with reset and form submission, live Groq behavior with a student-owned key, and deployment smoke tests.

## 8. Results and limitations

Demo mode makes the workflow reproducible without a key but is template-based and not research. Groq output can be wrong or incomplete. The application does not verify demand, market size, competitors, costs, revenue, or financial projections. Unit economics only calculates supplied assumptions. No user history or persistent storage is provided.

## 9. Responsible use and privacy

Users should enter synthetic, public, or permission-approved information only. They should not submit passwords, API keys, personal student records, private documents, or confidential institutional data. Important outputs must be checked through actual customer research.

## 10. Future work

Potential future work includes verified research workflows with citations, richer evidence capture, optional persistence with an explicit privacy policy, and a deployed Community Cloud instance. These should be added only with clear source and data handling rules.