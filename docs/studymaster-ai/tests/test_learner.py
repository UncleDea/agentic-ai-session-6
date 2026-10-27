"""Tests for the learner id on a saved pack.

These tests use a temporary database. They do not open the real study file.
"""

from pathlib import Path

import pytest

from studymaster.storage.database import LOCAL_LEARNER_ID, StorageError, StudyStore
from studymaster.ui.study_flow import open_saved, saved_studies, waiting_questions


def test_another_learner_stays_off_the_saved_list(tmp_path: Path) -> None:
    """A pack owned by someone else is not listed, opened, or deleted."""
    store = StudyStore(tmp_path / "study.db")
    mine = store.save_resource(
        url="https://example.com/mine",
        title="My pack",
        status="ok",
        level="beginner",
        goal="Explain the page",
        minutes=20,
        owner_id=LOCAL_LEARNER_ID,
    )
    theirs = store.save_resource(
        url="https://example.com/theirs",
        title="Their pack",
        status="ok",
        level="beginner",
        goal="Explain the page",
        minutes=20,
        owner_id="other",
    )

    titles = [item.title for item in saved_studies(store)]
    assert titles == ["My pack"]
    assert mine.owner_id == LOCAL_LEARNER_ID

    opened = open_saved(store, theirs.id)
    assert opened.ok is False
    assert opened.message == "This study belongs to another learner."
    assert "Their pack" not in opened.message

    with pytest.raises(StorageError, match="another learner"):
        store.delete_resource(theirs.id)
    assert store.get_resource(theirs.id).title == "Their pack"


def test_a_correct_answer_stays_off_the_waiting_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A correct score leaves the list. Opening a waiting question does not call the model."""
    from streamlit.testing.v1 import AppTest

    def fail_openai(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an OpenAI client was built")

    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_openai)
    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    mine = store.save_resource(
        url="https://example.com/mine",
        title="My pack",
        status="ok",
        owner_id=LOCAL_LEARNER_ID,
    )
    other = store.save_resource(
        url="https://example.com/theirs",
        title="Their pack",
        status="ok",
        owner_id="other",
    )
    store.replace_lesson_checks(
        mine.id,
        [
            ("What is still waiting?", "hidden waiting answer", "The page says so."),
            ("What is already correct?", "hidden correct answer", "The page says so."),
            ("What was only partial?", "hidden partial answer", "The page says so."),
        ],
    )
    store.replace_lesson_checks(
        other.id,
        [("What belongs to someone else?", "hidden other answer", "The page says so.")],
    )
    store.save_attempt(
        resource_id=mine.id,
        question="What is already correct?",
        learner_answer="The right reply",
        score="correct",
        hint="That matches the page.",
    )
    store.save_attempt(
        resource_id=mine.id,
        question="What was only partial?",
        learner_answer="Part of the reply",
        score="partial",
        hint="Look again.",
    )

    questions = [item.question for item in waiting_questions(store)]
    assert questions == ["What is still waiting?", "What was only partial?"]

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    assert "What is already correct?" not in _button_labels(app)
    assert "What belongs to someone else?" not in _button_labels(app)
    next(button for button in app.button if button.label == "What is still waiting?").click()
    app.run()
    page = _page_text(app)
    assert "My pack" in page
    assert "What is still waiting?" in page
    assert "hidden waiting answer" not in page


def _button_labels(app: object) -> list[str]:
    return [str(button.label) for button in app.button]


def test_wrong_password_hides_packs_and_the_right_one_shows_one_learner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A wrong password leaves every pack hidden. The right password shows one learner."""
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://example.com/mine",
        title="My pack",
        status="ok",
        owner_id=LOCAL_LEARNER_ID,
    )
    store.save_resource(
        url="https://example.com/theirs",
        title="Their pack",
        status="ok",
        owner_id="other",
    )
    store.create_learner(name="Ada", password="correct-horse")

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    assert "My pack" not in _page_text(app)
    assert "Their pack" not in _page_text(app)

    _sign_in(app, "Ada", "wrong-password")
    assert "That name or password is not right." in _page_text(app)
    assert "My pack" not in _page_text(app)

    _sign_in(app, "Ada", "correct-horse")
    page = _page_text(app)
    assert "My pack" in page
    assert "Their pack" not in page


def test_public_page_asks_for_a_login_before_it_shows_a_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public page hides every pack until a login is created."""
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("REQUIRE_LOGIN", "true")
    store = StudyStore(database)
    store.save_resource(
        url="https://example.com/mine",
        title="My pack",
        status="ok",
        owner_id=LOCAL_LEARNER_ID,
    )

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    page = _page_text(app)
    assert "Create a login" in _button_labels(app)
    assert "Page link" not in [box.label for box in app.text_input]
    assert "My pack" not in page


def _sign_in(app: object, name: str, password: str) -> None:
    next(box for box in app.text_input if box.label == "Name").set_value(name)
    next(box for box in app.text_input if box.label == "Password").set_value(password)
    next(button for button in app.button if button.label == "Sign in").click()
    app.run()


def _page_text(app: object) -> str:
    parts: list[str] = []
    for collection in ("markdown", "subheader", "header", "caption", "error"):
        for block in getattr(app, collection):
            parts.append(str(getattr(block, "value", "")))
    return "\n".join(parts)

