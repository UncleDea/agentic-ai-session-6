"""Tests for the grader.

The model client is fake. These tests do not call OpenAI.
"""

import json
from pathlib import Path

import pytest

from studymaster.agents.coordinator import HiddenCheck
from studymaster.agents.errors import EmptyReplyError, MissingApiKeyError, ModelResponseError
from studymaster.agents.grader import grade_reply, record_attempt
from studymaster.config import Settings
from studymaster.prompts.grade import grade_instructions, grade_prompt
from studymaster.storage.database import StudyStore
from studymaster.ui.study_flow import StudyOutcome, display_blocks
from tests.test_specialists import GOOD_QUOTE, HIDDEN_ANSWER

QUESTION = "What do plants use to make food?"
EXCERPT = GOOD_QUOTE
REPLY = "They use sunlight."
HINT = "Name the three ingredients from the excerpt."


def settings(path: Path) -> Settings:
    return Settings(
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        fetch_timeout_seconds=10,
        max_response_bytes=1_000_000,
        max_source_chars=20_000,
        min_source_chars=400,
        database_path=path,
        openai_timeout_seconds=60,
        openai_temperature=0.2,
    )


def _grade_json(score: str = "partial", hint: str = HINT) -> str:
    return json.dumps({"score": score, "hint": hint})


def test_grade_prompt_contains_the_excerpt_and_the_rule():
    prompt = grade_prompt(
        question=QUESTION,
        learner_answer=REPLY,
        answer=HIDDEN_ANSWER,
        excerpt=EXCERPT,
    )
    assert EXCERPT in prompt
    assert HIDDEN_ANSWER in prompt
    assert REPLY in prompt
    assert "use only this source" in prompt.casefold()
    assert "use only this source" in grade_instructions().casefold()


def test_blank_reply_never_calls_the_model():
    def fail(*, instructions: str, prompt: str) -> str:
        raise AssertionError("the model was called")

    with pytest.raises(EmptyReplyError):
        grade_reply(
            question=QUESTION,
            learner_answer="   ",
            answer=HIDDEN_ANSWER,
            excerpt=EXCERPT,
            complete=fail,
        )


def test_missing_api_key_stops_before_openai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OpenAI was constructed")

    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_if_called)
    with pytest.raises(MissingApiKeyError):
        grade_reply(
            question=QUESTION,
            learner_answer=REPLY,
            answer=HIDDEN_ANSWER,
            excerpt=EXCERPT,
            settings=settings(tmp_path / "study.db"),
        )


def test_attempt_is_saved_and_the_hint_is_not_the_answer(tmp_path: Path):
    def complete(*, instructions: str, prompt: str) -> str:
        assert EXCERPT in prompt
        return _grade_json()

    store = StudyStore(tmp_path / "study.db")
    resource = store.save_resource(
        url="https://example.com/plants",
        title="Photosynthesis",
        status="ok",
        extracted_text="Plants make food from sunlight, water, and carbon dioxide.",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
    )
    attempt = record_attempt(
        store=store,
        resource_id=resource.id,
        question=QUESTION,
        learner_answer=REPLY,
        answer=HIDDEN_ANSWER,
        excerpt=EXCERPT,
        complete=complete,
    )
    saved = store.list_attempts(resource.id)
    assert saved[0].id == attempt.id
    assert saved[0].score == "partial"
    assert saved[0].hint == HINT
    assert HIDDEN_ANSWER not in saved[0].hint
    assert saved[0].learner_answer == REPLY


def test_unreadable_grade_is_not_saved(tmp_path: Path):
    def complete(*, instructions: str, prompt: str) -> str:
        return _grade_json(score="almost")

    store = StudyStore(tmp_path / "study.db")
    resource = store.save_resource(
        url="https://example.com/plants",
        title="Photosynthesis",
        status="ok",
        extracted_text="Plants make food.",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
    )
    with pytest.raises(ModelResponseError):
        record_attempt(
            store=store,
            resource_id=resource.id,
            question=QUESTION,
            learner_answer=REPLY,
            answer=HIDDEN_ANSWER,
            excerpt=EXCERPT,
            complete=complete,
        )
    assert store.list_attempts(resource.id) == []


def test_saved_answer_stays_out_of_the_study_text():
    outcome = StudyOutcome(
        ok=True,
        message="",
        title="Photosynthesis",
        checks=(HiddenCheck(QUESTION, HIDDEN_ANSWER, EXCERPT),),
        resource_id=1,
    )
    assert HIDDEN_ANSWER not in "\n".join(text for _, text in display_blocks(outcome))


def test_page_shows_the_score_and_then_the_stored_answer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    resource = store.save_resource(
        url="https://example.com/plants",
        title="Photosynthesis",
        status="ok",
        extracted_text="Plants make food from sunlight, water, and carbon dioxide.",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
    )
    store.replace_lesson_checks(resource.id, [(QUESTION, HIDDEN_ANSWER, EXCERPT)])
    calls: list[str] = []

    def fake_record(**kwargs: object) -> object:
        reply = str(kwargs["learner_answer"])
        calls.append(reply)
        return store.save_attempt(
            resource_id=int(kwargs["resource_id"]),
            question=str(kwargs["question"]),
            learner_answer=reply,
            score="partial",
            hint=HINT,
        )

    monkeypatch.setattr("studymaster.ui.home.record_attempt", fake_record)
    outcome = StudyOutcome(
        ok=True,
        message="",
        title="Photosynthesis",
        hidden_answers=(HIDDEN_ANSWER,),
        checks=(HiddenCheck(QUESTION, HIDDEN_ANSWER, EXCERPT),),
        resource_id=resource.id,
    )
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["study_outcome"] = outcome
    app.run()
    before = _page_text(app)
    assert QUESTION in before
    assert HIDDEN_ANSWER not in before

    next(box for box in app.text_area if box.label == "Your answer").set_value(REPLY)
    next(button for button in app.button if button.label == "Check my answer").click()
    app.run()
    after = _page_text(app)
    assert "Partial" in after
    assert HINT in after
    assert f"Answer: {HIDDEN_ANSWER}" in after
    assert calls == [REPLY]

    app.run()
    assert calls == [REPLY]


def _page_text(app: object) -> str:
    parts: list[str] = []
    for collection in ("markdown", "subheader", "header", "caption", "error"):
        for block in getattr(app, collection):
            parts.append(str(getattr(block, "value", "")))
    return "\n".join(parts)
