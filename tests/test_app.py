from streamlit.testing.v1 import AppTest


SAMPLE = [
    "Students need affordable meals.",
    "University students",
    "Bengaluru",
    "Low budget",
    "Canteen and delivery apps",
]


def test_home_page_renders_required_controls():
    app = AppTest.from_file("app.py").run()
    assert not app.exception
    assert any("StartupSpark AI" in item.value for item in app.markdown)
    assert len(app.text_area) == 3
    assert len(app.text_input) == 2


def test_empty_submission_shows_five_validation_messages():
    app = AppTest.from_file("app.py").run()
    app.button[0].click().run()
    assert len(app.error) == 5


def test_valid_submission_renders_brief_and_extensions(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "demo")
    monkeypatch.setenv("GROQ_API_KEY", "")
    app = AppTest.from_file("app.py").run()
    app.text_area[0].set_value(SAMPLE[0])
    app.text_input[0].set_value(SAMPLE[1])
    app.text_input[1].set_value(SAMPLE[2])
    app.text_area[1].set_value(SAMPLE[3])
    app.text_area[2].set_value(SAMPLE[4])
    app.button[0].click().run()
    assert not app.exception
    assert any("Your concept brief" in item.value for item in app.subheader)
    assert any("Advanced extensions" in item.value for item in app.markdown)
