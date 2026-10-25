from backend.utils.validators import MAX_FIELD_LENGTH, validate_inputs


def valid_values():
    return {
        "problem": "Students need affordable meals.",
        "target_customer": "University students",
        "geography": "Bengaluru",
        "constraints": "Low budget",
        "alternatives": "Canteen and delivery apps",
    }


def test_valid_input_is_accepted():
    inputs, errors = validate_inputs(valid_values())
    assert not errors
    assert inputs.problem == "Students need affordable meals."


def test_empty_required_input_is_rejected():
    values = valid_values()
    values["problem"] = "  "
    inputs, errors = validate_inputs(values)
    assert inputs is None
    assert "problem or rough idea" in errors[0]


def test_oversized_input_is_rejected():
    values = valid_values()
    values["constraints"] = "x" * (MAX_FIELD_LENGTH + 1)
    inputs, errors = validate_inputs(values)
    assert inputs is None
    assert "2000 characters" in errors[0]


def test_all_missing_inputs_are_reported():
    inputs, errors = validate_inputs({})
    assert inputs is None
    assert len(errors) == 5


def test_unknown_fields_do_not_replace_required_inputs():
    values = valid_values()
    values["extra"] = "ignored"
    inputs, errors = validate_inputs(values)
    assert not errors
    assert "extra" not in inputs.as_dict()
