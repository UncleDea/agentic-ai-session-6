"""Tests for saved studies, rewriting one section, and Markdown download.

The model client is fake. These tests do not call OpenAI or the public internet.
"""

from pathlib import Path

import pytest

from studymaster.agents.errors import EmptySourceError, MissingApiKeyError
from studymaster.config import Settings
from studymaster.storage.database import Resource, StudyStore
from studymaster.ui.study_flow import (
    markdown_filename,
    matching_studies,
    open_saved,
    pack_markdown,
    regenerate_section,
    saved_day,
    saved_studies,
)
from tests.test_specialists import HIDDEN_ANSWER, OUTLINE, SOURCE, RoutingModel, _lesson_json

LAB_MARKDOWN = "## Lab\nName the ingredients."
STUDY_MARKDOWN = f"## Outline\n\n{OUTLINE}\n\n## Objectives\nExplain how plants make food."


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


def _store_pack(path: Path, *, text: str = SOURCE) -> tuple[StudyStore, int]:
    store = StudyStore(path)
    resource = store.save_resource(
        url="https://example.com/plants",
        title="Photosynthesis",
        status="ok",
        extracted_text=text,
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
    )
    store.save_artifact(
        resource_id=resource.id,
        kind="study",
        status="ok",
        markdown=STUDY_MARKDOWN,
        model_name="gpt-4o-mini",
    )
    store.save_artifact(
        resource_id=resource.id,
        kind="lab",
        status="ok",
        markdown=LAB_MARKDOWN,
        model_name="gpt-4o-mini",
    )
    store.replace_lesson_checks(
        resource.id,
        [("What do plants use to make food?", HIDDEN_ANSWER, "Plants make food from sunlight")],
    )
    return store, resource.id


def test_history_skips_failed_fetches_and_opens_without_a_model(tmp_path: Path):
    store, resource_id = _store_pack(tmp_path / "study.db")
    store.save_resource(
        url="http://127.0.0.1/secret",
        title="",
        status="error",
        error_message="This address cannot be opened.",
    )

    studies = saved_studies(store)
    assert [item.id for item in studies] == [resource_id]
    opened = open_saved(store, resource_id)
    assert opened.from_saved is True
    assert opened.title == "Photosynthesis"
    assert LAB_MARKDOWN in pack_markdown(opened)
    assert HIDDEN_ANSWER not in pack_markdown(opened)
    assert HIDDEN_ANSWER in opened.hidden_answers


def test_rewrite_changes_one_section_and_keeps_the_saved_page(tmp_path: Path):
    store, resource_id = _store_pack(tmp_path / "study.db")
    model = RoutingModel({"practical lab": "## not json", "guided lesson": _lesson_json()})

    def complete(*, instructions: str, prompt: str) -> str:
        model.complete(instructions=instructions, prompt=prompt)
        assert SOURCE in prompt
        assert "use only this source" in prompt.casefold()
        assert OUTLINE in prompt
        if "practical lab" in instructions:
            return (
                '{"has_procedure": false, "note": "", "tasks": ['
                '{"instruction": "Plants make food from sunlight.", '
                '"expected_result": "Plants make food from water.", '
                '"quote": "Plants make food from sunlight"}]}'
            )
        return model.replies["guided lesson"]

    updated = regenerate_section(
        store=store,
        resource_id=resource_id,
        kind="lab",
        settings=settings(tmp_path / "study.db"),
        complete=complete,
    )
    by_kind = {section.kind: section.markdown for section in updated.sections}
    assert "Plants make food from water." in by_kind["lab"]
    assert by_kind["study"] == STUDY_MARKDOWN
    assert len(model.prompts) == 1

    broken = regenerate_section(
        store=store,
        resource_id=resource_id,
        kind="lesson",
        settings=settings(tmp_path / "study.db"),
        complete=lambda **_kwargs: "this is not json",
    )
    lesson = next(section for section in broken.sections if section.kind == "lesson")
    lab = next(section for section in broken.sections if section.kind == "lab")
    assert lesson.status == "error"
    assert "Plants make food from water." in lab.markdown
    assert broken.checks == ()


def test_empty_saved_text_never_calls_the_model(tmp_path: Path):
    store, resource_id = _store_pack(tmp_path / "empty.db", text="   ")

    def fail(*, instructions: str, prompt: str) -> str:
        raise AssertionError("the model was called")

    with pytest.raises(EmptySourceError):
        regenerate_section(
            store=store,
            resource_id=resource_id,
            kind="study",
            settings=settings(tmp_path / "empty.db"),
            complete=fail,
        )


def test_missing_key_stops_before_openai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store, resource_id = _store_pack(tmp_path / "study.db")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OpenAI was constructed")

    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_if_called)
    with pytest.raises(MissingApiKeyError):
        regenerate_section(
            store=store,
            resource_id=resource_id,
            kind="lab",
            settings=settings(tmp_path / "study.db"),
        )


def test_download_name_uses_the_title():
    assert markdown_filename("Photosynthesis") == "photosynthesis.md"
    assert markdown_filename("   ") == "study.md"


def test_page_opens_a_saved_study_without_calling_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store, resource_id = _store_pack(database)
    calls: list[str] = []

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    def fake_rewrite(**kwargs: object):
        calls.append(str(kwargs["kind"]))
        store.save_artifact(
            resource_id=resource_id,
            kind="lab",
            status="ok",
            markdown="## Lab\nA rewritten task.",
            model_name="gpt-4o-mini",
        )
        return open_saved(store, resource_id)

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    monkeypatch.setattr("studymaster.ui.home.regenerate_section", fake_rewrite)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    assert "Photosynthesis" in _page_text(app)
    assert HIDDEN_ANSWER not in _page_text(app)
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    opened = _page_text(app)
    assert "Name the ingredients." in opened
    assert HIDDEN_ANSWER not in opened
    assert any(button.label == "Download Markdown" for button in app.download_button)
    next(button for button in app.button if button.label == "Rewrite lab").click()
    app.run()
    assert calls == ["lab"]
    assert "A rewritten task." in _page_text(app)


def test_delete_asks_once_then_removes_only_that_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    _store_pack(database)
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/retention",
        title="Retention policies",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain retention",
        minutes=20,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    text = _page_text(app)
    assert "Photosynthesis" in text
    assert "Retention policies" in text

    next(button for button in app.button if button.label == "Delete").click()
    app.run()
    still_there = _page_text(app)
    assert "Photosynthesis" in still_there
    assert "Retention policies" in still_there

    next(button for button in app.button if button.label == "Delete this study?").click()
    app.run()
    after = _page_text(app)
    assert "Retention policies" not in after
    assert "Photosynthesis" in after


def test_saved_day_uses_the_day_on_this_computer() -> None:
    from datetime import datetime, timedelta, timezone

    first = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
    second = first + timedelta(hours=30)
    first_day = saved_day(first.isoformat())
    second_day = saved_day(second.isoformat())
    assert first_day.startswith("Saved ")
    assert second_day.startswith("Saved ")
    assert first_day != second_day
    assert saved_day("not a time") == ""


def test_saved_list_shows_the_day_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store, resource_id = _store_pack(database)
    saved = store.get_resource(resource_id)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    shown = _page_text(app)
    assert "Explain photosynthesis" in shown
    assert saved_day(saved.fetched_at) in shown


def test_find_keeps_a_title_that_contains_the_typed_words() -> None:
    entra = _named("What is Microsoft Entra?")
    identity = _named("Get Started with Identity Architecture Design")
    assert matching_studies([entra, identity], "") == [entra, identity]
    assert matching_studies([entra, identity], "  ENTRA ") == [entra]
    assert matching_studies([entra, identity], "zzzz") == []


def test_find_keeps_a_study_when_the_goal_line_matches() -> None:
    from dataclasses import replace

    entra = replace(_named("What is Microsoft Entra?"), goal="Explain what Microsoft Entra ID does.")
    identity = replace(
        _named("Get Started with Identity Architecture Design"),
        goal="master the material",
    )
    assert matching_studies([entra, identity], "  MASTER ") == [identity]


def test_find_box_hides_other_titles_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    _store_pack(database)
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/retention",
        title="Retention policies",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain retention",
        minutes=20,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("  retention ")
    app.run()
    shown = _page_text(app)
    assert "Retention policies" in shown
    assert "Photosynthesis" not in shown

    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("zzzz")
    app.run()
    missed = _page_text(app)
    assert "No saved study matches that." in missed
    assert "Retention policies" not in missed
    assert "Photosynthesis" not in missed


def test_find_box_keeps_a_goal_match_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    _store_pack(database)
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/architecture/identity",
        title="Get Started with Identity Architecture Design",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="master the material",
        minutes=20,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    assert finder.placeholder == "Type part of a title or goal"
    finder.set_value("  MASTER ")
    app.run()
    shown = _page_text(app)
    assert "Get Started with Identity Architecture Design" in shown
    assert "master the material" in shown
    assert "Photosynthesis" not in shown


def test_start_over_clears_the_screen_and_keeps_saved_studies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    from studymaster.sample_links import NO_READING_GOAL, OWN_LINK, article_links, choice_label

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    _store_pack(database)
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/retention",
        title="Retention policies",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain retention",
        minutes=20,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    open_buttons = [button for button in app.button if button.label == "Open study"]
    open_buttons[1].click()
    app.run()
    assert "Name the ingredients." in _page_text(app)

    next(box for box in app.text_input if box.label == "Page link").set_value(
        "https://example.com/plants"
    )
    next(box for box in app.text_area if box.label == "Article text").set_value(
        "Lesson words"
    )
    next(box for box in app.text_input if box.label == "Goal").set_value("Explain plants")
    next(box for box in app.selectbox if box.label == "Level").set_value("Advanced")
    next(box for box in app.number_input if box.label == "Minutes").set_value(45)
    next(box for box in app.selectbox if box.label == "Starter article").set_value(
        choice_label(article_links()[0])
    )
    next(box for box in app.text_input if box.label == "Find a study").set_value("Photo")
    app.run()

    next(button for button in app.button if button.label == "Start over").click()
    app.run()
    cleared = _page_text(app)
    assert "Name the ingredients." not in cleared
    assert "Photosynthesis" in cleared
    assert "Retention policies" not in cleared
    assert next(box for box in app.text_input if box.label == "Page link").value == ""
    assert next(box for box in app.text_area if box.label == "Article text").value == ""
    assert next(box for box in app.text_input if box.label == "Goal").value == ""
    assert next(box for box in app.selectbox if box.label == "Level").value == "Beginner"
    assert next(box for box in app.number_input if box.label == "Minutes").value == 20
    assert next(box for box in app.selectbox if box.label == "Starter article").value == OWN_LINK
    assert next(box for box in app.selectbox if box.label == "Reading goal").value == NO_READING_GOAL
    assert next(box for box in app.text_input if box.label == "Find a study").value == "Photo"
    titles = {item.title for item in store.list_resources()}
    assert titles == {"Photosynthesis", "Retention policies"}


def _named(title: str) -> Resource:
    return Resource(
        id=1,
        url="https://example.com",
        content_hash="",
        fetched_at="",
        title=title,
        status="ok",
        error_message="",
        extracted_text="",
        level="beginner",
        goal="",
        minutes=20,
    )


def _page_text(app: object) -> str:
    parts: list[str] = []
    for collection in ("markdown", "subheader", "header", "caption", "error"):
        for block in getattr(app, collection):
            parts.append(str(getattr(block, "value", "")))
    return "\n".join(parts)
