"""Tests for the home-page study flow.

The page download and the model are fakes. These tests do not call
the public internet or OpenAI.
"""

from pathlib import Path

import pytest

from studymaster.agents.client import OpenAIModelClient
from studymaster.agents.coordinator import AgentSection, HiddenCheck
from studymaster.agents.errors import MissingApiKeyError
from studymaster.agents.quotes import COVER
from studymaster.config import Settings
from studymaster.extraction.errors import UnreadablePageError
from studymaster.extraction.fetch import Article
from studymaster.storage.database import STATUS_ERROR, STATUS_OK, StudyStore
from studymaster.ui.study_flow import (
    PASTED_TEXT_URL,
    SHORTENED_NOTICE,
    StudyOutcome,
    _outline_text,
    display_blocks,
    open_saved,
    pack_score_line,
    study_page,
)
from tests.test_specialists import HIDDEN_ANSWER, OUTLINE, SOURCE, RoutingModel, _replies


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


def _article(url: str, text: str = SOURCE) -> Article:
    return Article(
        url=url,
        title="Photosynthesis",
        headings=["How plants make food"],
        text=text,
        shortened=False,
    )


def _visible(outcome) -> str:
    return "\n".join(text for _, text in display_blocks(outcome))


def test_empty_link_never_reads_or_calls_the_model(tmp_path: Path):
    def fail_read(*_args, **_kwargs):
        raise AssertionError("the page was read")

    def fail_model(*, instructions: str, prompt: str) -> str:
        raise AssertionError("the model was called")

    outcome = study_page(
        url="  ",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=StudyStore(tmp_path / "study.db"),
        read=fail_read,
        complete=fail_model,
    )
    assert outcome.ok is False
    assert outcome.message == "Paste a public page link."


def test_private_link_stops_before_the_model(tmp_path: Path):
    def fail_model(*, instructions: str, prompt: str) -> str:
        raise AssertionError("the model was called")

    store = StudyStore(tmp_path / "study.db")
    outcome = study_page(
        url="http://127.0.0.1/secret",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=store,
        complete=fail_model,
    )
    assert outcome.ok is False
    assert outcome.message == "This address cannot be opened."
    assert _visible(outcome) == "This address cannot be opened."
    saved = store.list_resources()
    assert saved[0].status == STATUS_ERROR


def test_unreadable_page_stops_before_the_model(tmp_path: Path):
    def unreadable(*_args, **_kwargs):
        raise UnreadablePageError("This page did not include readable article text.")

    def fail_model(*, instructions: str, prompt: str) -> str:
        raise AssertionError("the model was called")

    outcome = study_page(
        url="https://example.com/empty",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=StudyStore(tmp_path / "study.db"),
        read=unreadable,
        complete=fail_model,
    )
    assert outcome.message == "This page did not include readable article text."


def test_study_pack_hides_the_answer_and_saves_five_sections(tmp_path: Path):
    model = RoutingModel(_replies())

    def read(url: str, settings=None) -> Article:
        return _article(url)

    store = StudyStore(tmp_path / "study.db")
    outcome = study_page(
        url="https://example.com/plants",
        level="Beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=store,
        read=read,
        complete=model.complete,
    )
    visible = _visible(outcome)
    assert outcome.ok is True
    assert outcome.title == "Photosynthesis"
    assert [section.kind for section in outcome.sections] == [
        "study",
        "lesson",
        "lab",
        "project",
        "runbook",
    ]
    assert OUTLINE in visible
    assert HIDDEN_ANSWER in outcome.hidden_answers
    assert HIDDEN_ANSWER not in visible
    assert len(store.list_artifacts(store.list_resources()[0].id)) == 5
    assert len([prompt for prompt in model.prompts if "Repair these sentences" not in prompt]) == 6


def test_same_page_uses_the_saved_pack(tmp_path: Path):
    model = RoutingModel(_replies())

    def read(url: str, settings=None) -> Article:
        return _article(url)

    store = StudyStore(tmp_path / "study.db")
    page = dict(
        url="https://example.com/plants",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=store,
        read=read,
        complete=model.complete,
    )
    first = study_page(**page)
    second = study_page(
        **page,
        remembered_answers=first.hidden_answers,
        remembered_hash=first.content_hash,
    )
    assert second.from_saved is True
    assert second.hidden_answers == (HIDDEN_ANSWER,)
    assert HIDDEN_ANSWER not in _visible(second)
    assert OUTLINE in _visible(second)
    assert len([prompt for prompt in model.prompts if "Repair these sentences" not in prompt]) == 6


def test_one_failed_section_keeps_the_others(tmp_path: Path):
    model = RoutingModel(_replies(lesson="this is not json"))

    def read(url: str, settings=None) -> Article:
        return _article(url)

    outcome = study_page(
        url="https://example.com/plants",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=StudyStore(tmp_path / "study.db"),
        read=read,
        complete=model.complete,
    )
    visible = _visible(outcome)
    by_kind = {section.kind: section for section in outcome.sections}
    assert by_kind["lesson"].status == "error"
    assert by_kind["lesson"].error_message in visible
    assert "## Lab" in visible
    assert outcome.hidden_answers == ()


def test_missing_api_key_stops_before_openai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OpenAI was constructed")

    def read(url: str, settings=None) -> Article:
        return _article(url)

    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_if_called)
    with pytest.raises(MissingApiKeyError):
        OpenAIModelClient(settings(tmp_path / "study.db"))
    outcome = study_page(
        url="https://example.com/plants",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=StudyStore(tmp_path / "study.db"),
        read=read,
    )
    assert "OPENAI_API_KEY" in outcome.message
    assert outcome.ok is False


def test_catalog_choice_fills_the_learn_url_without_calling_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    from studymaster.sample_links import (
        NO_READING_GOAL,
        READING_GOAL_CAPTION,
        article_links,
        choice_label,
        reading_goals,
    )

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "study.db"))
    monkeypatch.setenv("OPENAI_API_KEY", "")

    def fail_study(*_args, **_kwargs):
        raise AssertionError("the model was called")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    labels = [box.label for box in app.selectbox]
    assert "Starter article" in labels
    assert "Reading goal" in labels
    assert "Article text" in [box.label for box in app.text_area]

    article = article_links()[0]
    starter = next(box for box in app.selectbox if box.label == "Starter article")
    starter.set_value(choice_label(article))
    app.run()
    page_link = next(box for box in app.text_input if box.label == "Page link")
    goal = next(box for box in app.text_input if box.label == "Goal")
    assert page_link.value == article.learn_url
    assert goal.value == article.goal

    reading = reading_goals()[0]
    goal_box = next(box for box in app.selectbox if box.label == "Reading goal")
    assert goal_box.value == NO_READING_GOAL
    goal_box.set_value(choice_label(reading))
    app.run()
    page_link = next(box for box in app.text_input if box.label == "Page link")
    goal = next(box for box in app.text_input if box.label == "Goal")
    assert page_link.value == article.learn_url
    assert goal.value == reading.goal
    assert any(READING_GOAL_CAPTION in str(block.value) for block in app.caption)


def _pasted_lesson(first_line: str = "How plants make food") -> str:
    body = " ".join([SOURCE] * 12)
    return f"{first_line}\n{body}"


def test_pasted_lesson_skips_the_reader_and_a_private_link(tmp_path: Path):
    model = RoutingModel(_replies())

    def fail_read(*_args, **_kwargs):
        raise AssertionError("the page was read")

    store = StudyStore(tmp_path / "study.db")
    outcome = study_page(
        url="http://127.0.0.1/secret",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=store,
        read=fail_read,
        complete=model.complete,
        article_text=_pasted_lesson("A" * 90),
    )
    assert outcome.ok is True
    assert outcome.title == "A" * 80
    saved = store.list_resources()
    assert saved[0].url == PASTED_TEXT_URL
    assert len(store.list_artifacts(saved[0].id)) == 5
    assert len([prompt for prompt in model.prompts if "Repair these sentences" not in prompt]) == 6


def test_same_paste_uses_the_saved_pack(tmp_path: Path):
    model = RoutingModel(_replies())

    def fail_read(*_args, **_kwargs):
        raise AssertionError("the page was read")

    store = StudyStore(tmp_path / "study.db")
    page = dict(
        url="",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=store,
        read=fail_read,
        complete=model.complete,
        article_text=_pasted_lesson(),
    )
    first = study_page(**page)
    second = study_page(
        **page,
        remembered_answers=first.hidden_answers,
        remembered_hash=first.content_hash,
    )
    assert second.from_saved is True
    assert second.title == "How plants make food"
    assert len([prompt for prompt in model.prompts if "Repair these sentences" not in prompt]) == 6


def test_short_paste_never_reads_or_calls_the_model(tmp_path: Path):
    def fail_read(*_args, **_kwargs):
        raise AssertionError("the page was read")

    def fail_model(*, instructions: str, prompt: str) -> str:
        raise AssertionError("the model was called")

    store = StudyStore(tmp_path / "study.db")
    outcome = study_page(
        url="http://127.0.0.1/secret",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "study.db"),
        store=store,
        read=fail_read,
        complete=fail_model,
        article_text="A few words",
    )
    assert outcome.ok is False
    assert outcome.message == "This page did not include readable article text."
    assert store.list_resources() == []


def test_progress_names_each_step(tmp_path: Path):
    steps: list[str] = []
    model = RoutingModel(_replies())
    store = StudyStore(tmp_path / "study.db")
    page_settings = settings(tmp_path / "study.db")
    writing = [
        "Writing the outline.",
        "Writing the study.",
        "Writing the lesson.",
        "Writing the lab.",
        "Writing the project.",
        "Writing the runbook.",
    ]

    def read(url: str, settings=None) -> Article:
        return _article(url)

    study_page(
        url="https://example.com/plants",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=page_settings,
        store=store,
        read=read,
        complete=model.complete,
        on_progress=steps.append,
    )
    assert steps == ["Checking the link.", "Reading the page.", *writing]

    steps.clear()
    second = study_page(
        url="https://example.com/plants",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=page_settings,
        store=store,
        read=read,
        complete=model.complete,
        on_progress=steps.append,
    )
    assert second.from_saved is True
    assert steps == [
        "Checking the link.",
        "Reading the page.",
        "Opening the saved pack.",
    ]
    assert "Writing the outline." not in steps

    steps.clear()

    def fail_read(*_args, **_kwargs):
        raise AssertionError("the page was read")

    study_page(
        url="",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=page_settings,
        store=store,
        read=fail_read,
        complete=model.complete,
        article_text=_pasted_lesson(),
        on_progress=steps.append,
    )
    assert steps == ["Checking the link.", "Using the pasted lesson.", *writing]
    assert "Reading the page." not in steps


def test_pack_score_counts_left_out_sentences_and_questions():
    outcome = StudyOutcome(
        ok=True,
        message="",
        sections=(
            AgentSection("lab", STATUS_OK, "", f"{COVER}\nStill here.\n{COVER}", []),
        ),
        checks=(HiddenCheck("What do plants use?", "sunlight", SOURCE),),
    )
    assert pack_score_line(outcome) == "Left out 2 sentences. Questions to check: 1."


def test_a_shortened_page_keeps_the_notice(tmp_path: Path):
    model = RoutingModel(_replies())

    def read(url: str, settings=None) -> Article:
        return Article(
            url=url,
            title="Photosynthesis",
            headings=["How plants make food"],
            text=SOURCE,
            shortened=True,
        )

    store = StudyStore(tmp_path / "short.db")
    outcome = study_page(
        url="https://example.com/plants",
        level="Beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "short.db"),
        store=store,
        read=read,
        complete=model.complete,
    )
    assert SHORTENED_NOTICE in _visible(outcome)
    opened = open_saved(store, outcome.resource_id)
    assert SHORTENED_NOTICE in _visible(opened)
    assert _outline_text(outcome.sections[0].markdown) == OUTLINE


def test_a_full_page_does_not_say_it_was_shortened(tmp_path: Path):
    model = RoutingModel(_replies())

    def read(url: str, settings=None) -> Article:
        return _article(url)

    outcome = study_page(
        url="https://example.com/plants",
        level="Beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings(tmp_path / "full.db"),
        store=StudyStore(tmp_path / "full.db"),
        read=read,
        complete=model.complete,
    )
    assert SHORTENED_NOTICE not in _visible(outcome)


def test_the_pack_score_is_written_to_the_log(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    model = RoutingModel(_replies())

    def read(url: str, settings=None) -> Article:
        return _article(url)

    with caplog.at_level("INFO"):
        study_page(
            url="https://example.com/plants",
            level="Beginner",
            goal="Explain photosynthesis",
            minutes=20,
            settings=settings(tmp_path / "log.db"),
            store=StudyStore(tmp_path / "log.db"),
            read=read,
            complete=model.complete,
        )
    assert "Left out " in caplog.text
    assert "Questions to check:" in caplog.text
