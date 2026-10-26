"""Tests for saved studies, rewriting one section, and Markdown download.

The model client is fake. These tests do not call OpenAI or the public internet.
"""

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from studymaster.agents.errors import EmptySourceError, MissingApiKeyError
from studymaster.agents.quotes import COVER
from studymaster.config import Settings
from studymaster.storage.database import Resource, StudyStore
from studymaster.ui.study_flow import (
    markdown_filename,
    matching_studies,
    open_saved,
    pack_docx,
    pack_markdown,
    StudyOutcome,
    regenerate_section,
    saved_check,
    saved_day,
    saved_level,
    saved_minutes,
    saved_pieces,
    saved_progress,
    saved_question,
    left_to_check,
    reply_day,
    saved_studies,
    read_from_line,
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
    assert any(button.label == "Download Word" for button in app.download_button)
    next(button for button in app.button if button.label == "Rewrite lab").click()
    app.run()
    assert calls == ["lab"]
    assert "A rewritten task." in _page_text(app)


def test_pack_docx_is_a_word_file_without_hidden_answers() -> None:
    from studymaster.agents.coordinator import AgentSection

    outcome = StudyOutcome(
        ok=True,
        message="",
        title="Photosynthesis",
        sections=(
            AgentSection("study", "ok", "", "## Study\nPlants make food.", []),
            AgentSection(
                "runbook",
                "ok",
                "",
                "## Runbook\n1. Open the portal.\n- Bring a notebook.",
                [],
            ),
        ),
        hidden_answers=("secret answer",),
    )
    data = pack_docx(outcome)
    assert data[:2] == b"PK"
    xml = ZipFile(BytesIO(data)).read("word/document.xml").decode("utf-8")
    assert "Photosynthesis" in xml
    assert "Study" in xml
    assert "Open the portal." in xml
    assert "Bring a notebook." in xml
    assert "secret answer" not in xml
    assert "Left to check" not in xml


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


def test_saved_minutes_uses_one_or_many() -> None:
    assert saved_minutes(1) == "1 minute"
    assert saved_minutes(15) == "15 minutes"
    assert saved_minutes(0) == ""


def test_saved_level_names_who_the_pack_is_for() -> None:
    assert saved_level("beginner") == "For a beginner"
    assert saved_level(" Intermediate ") == "For an intermediate learner"
    assert saved_level("advanced") == "For an advanced learner"
    assert saved_level("") == ""
    assert saved_level("expert") == ""


def test_saved_pieces_names_the_sections_in_order() -> None:
    assert saved_pieces(("lesson", "study")) == "Study, lesson"
    assert saved_pieces(("runbook", "project", "lab", "lesson", "study")) == (
        "Study, lesson, lab, project, runbook"
    )
    assert saved_pieces(()) == ""
    assert saved_pieces(("outline",)) == ""


def test_read_from_line_names_the_public_host() -> None:
    assert (
        read_from_line("https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp")
        == "Read from learn.microsoft.com"
    )
    assert read_from_line("http://Example.COM/plants") == "Read from example.com"
    assert read_from_line("pasted-text") == ""
    assert read_from_line("") == ""


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
    assert "20 minutes" in shown
    assert "Study, lab" not in shown
    assert saved_day(saved.fetched_at) not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("saved")
    app.run()
    assert "Explain photosynthesis" in _page_text(app)


def test_saved_list_shows_different_minutes_for_the_same_title(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    for minutes in (15, 20):
        store.save_resource(
            url=f"https://learn.microsoft.com/dlp-{minutes}",
            title="Learn about data loss prevention | Microsoft Learn",
            status="ok",
            extracted_text=SOURCE,
            level="beginner",
            goal="Explain how data loss prevention protects sensitive information.",
            minutes=minutes,
        )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    shown = _page_text(app)
    assert "15 minutes" in shown
    assert "20 minutes" in shown


def test_saved_list_names_the_level_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        title="Learn about data loss prevention",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain how data loss prevention protects sensitive information.",
        minutes=15,
    )
    store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="advanced",
        goal="Master the material.",
        minutes=5,
    )
    store.save_resource(
        url="pasted-text",
        title="Plain page",
        status="ok",
        extracted_text=SOURCE,
        level="",
        goal="Explain the pasted lesson.",
        minutes=10,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "For a beginner" not in lines
    assert "For an advanced learner" not in lines
    assert "Plain page" in shown
    assert "For an intermediate learner" not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("beginner")
    app.run()
    kept = _page_text(app)
    assert "Learn about data loss prevention" in kept
    assert "Get started with identity architecture" not in kept


def test_saved_list_names_the_site_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        title="Learn about data loss prevention",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain how data loss prevention protects sensitive information.",
        minutes=15,
    )
    store.save_resource(
        url="pasted-text",
        title="Pasted lesson",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the pasted lesson.",
        minutes=10,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "Read from learn.microsoft.com" not in lines
    assert "Pasted lesson" in shown
    assert "Read from pasted-text" not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("learn.microsoft.com")
    app.run()
    kept = _page_text(app)
    assert "Learn about data loss prevention" in kept
    assert "Pasted lesson" not in kept


def test_saved_list_names_the_pieces_each_pack_has(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    short = store.save_resource(
        url="https://learn.microsoft.com/short",
        title="Learn about data loss prevention | Microsoft Learn",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain how data loss prevention protects sensitive information.",
        minutes=5,
    )
    full = store.save_resource(
        url="https://learn.microsoft.com/full",
        title="Learn about data loss prevention | Microsoft Learn",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain how data loss prevention protects sensitive information.",
        minutes=20,
    )
    for kind in ("study", "lesson"):
        store.save_artifact(
            resource_id=short.id,
            kind=kind,
            status="ok",
            markdown=f"## {kind}",
            model_name="gpt-4o-mini",
        )
    store.save_artifact(
        resource_id=short.id,
        kind="lab",
        status="error",
        error_message="The lab failed.",
        model_name="gpt-4o-mini",
    )
    for kind in ("study", "lesson", "lab", "project", "runbook"):
        store.save_artifact(
            resource_id=full.id,
            kind=kind,
            status="ok",
            markdown=f"## {kind}",
            model_name="gpt-4o-mini",
        )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "Study, lesson" not in lines
    assert "Study, lesson, lab, project, runbook" not in lines
    assert "The lab failed." not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("runbook")
    app.run()
    kept = _page_text(app)
    assert "20 minutes" in kept
    assert "5 minutes" not in kept


def test_saved_list_names_the_score_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    flagged = store.save_resource(
        url="https://learn.microsoft.com/flagged",
        title="Flagged page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the flagged page.",
        minutes=20,
    )
    quiet = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=15,
    )
    store.save_artifact(
        resource_id=flagged.id,
        kind="study",
        status="ok",
        markdown=f"## Study\n{COVER}\nStill here.",
        model_name="gpt-4o-mini",
    )
    store.save_artifact(
        resource_id=flagged.id,
        kind="lab",
        status="error",
        error_message=COVER,
        model_name="gpt-4o-mini",
    )
    store.replace_lesson_checks(
        flagged.id,
        [("What do plants use?", "sunlight", SOURCE)],
    )
    store.save_artifact(
        resource_id=quiet.id,
        kind="study",
        status="ok",
        markdown="## Study\nPlants make food.",
        model_name="gpt-4o-mini",
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    quiet_score = "Left out 0 sentences. Questions to check: 0."
    flagged_score = "Left out 1 sentences. Questions to check: 1."
    assert quiet_score not in captions
    assert flagged_score not in captions
    shown = _page_text(app)
    assert "Quiet page" in shown
    assert "Flagged page" in shown
    assert COVER not in shown
    assert "Still here." not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    assert finder.placeholder == (
        "Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, reply, left, or empty"
    )
    finder.set_value("Left out")
    app.run()
    kept = _page_text(app)
    assert "Quiet page" in kept
    assert "Flagged page" in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("1")
    app.run()
    filtered = _page_text(app)
    assert "Flagged page" in filtered
    assert "Quiet page" not in filtered


def test_saved_check_names_the_latest_label() -> None:
    assert saved_check("partial") == "Last check: Partial"
    assert saved_check("CORRECT") == "Last check: Correct"
    assert saved_check("incorrect") == "Last check: Incorrect"
    assert saved_check("") == ""
    assert saved_check("great") == ""


def test_saved_list_names_the_latest_check_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    quiet = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=15,
    )
    checked = store.save_resource(
        url="https://learn.microsoft.com/checked",
        title="Checked page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the checked page.",
        minutes=20,
    )
    for resource_id in (quiet.id, checked.id):
        store.save_artifact(
            resource_id=resource_id,
            kind="study",
            status="ok",
            markdown="## Study\nPlants make food.",
            model_name="gpt-4o-mini",
        )
    store.save_attempt(
        resource_id=checked.id,
        question="What do plants use?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays off the list.",
    )
    store.save_attempt(
        resource_id=checked.id,
        question="What do plants use?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays off the list.",
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    score = "Left out 0 sentences. Questions to check: 0."
    assert score not in captions
    assert "Last check: Partial" not in captions
    assert "Last check: Incorrect" not in captions
    assert "Last check: Correct" not in captions
    shown = _page_text(app)
    assert "Checked page" in shown
    assert "Quiet page" in shown
    assert "Hidden hint stays off the list." not in shown
    assert "Later reply" not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    assert finder.placeholder == (
        "Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, reply, left, or empty"
    )
    finder.set_value("Partial")
    app.run()
    filtered = _page_text(app)
    assert "Checked page" in filtered
    assert "Quiet page" not in filtered
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("correct")
    app.run()
    missed = _page_text(app)
    assert "No saved study matches that." in missed
    assert "Checked page" not in missed


def test_saved_progress_counts_questions_with_a_reply() -> None:
    assert saved_progress(1, 6) == "Checked 1 of 6."
    assert saved_progress(0, 12) == "Checked 0 of 12."
    assert saved_progress(0, 0) == ""
    assert saved_progress(3, 2) == "Checked 2 of 2."


def test_left_to_check_counts_questions_still_waiting() -> None:
    assert left_to_check(1, 6) == "Left to check: 5."
    assert left_to_check(0, 5) == "Left to check: 5."
    assert left_to_check(0, 12) == "Left to check: 12."
    assert left_to_check(2, 2) == "Left to check: 0."
    assert left_to_check(0, 0) == ""
    assert left_to_check(3, 2) == "Left to check: 0."


def test_saved_list_names_how_many_questions_are_still_waiting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    blank = store.save_resource(
        url="https://learn.microsoft.com/blank",
        title="Blank page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the blank page.",
        minutes=20,
    )
    waiting = store.save_resource(
        url="https://learn.microsoft.com/waiting",
        title="Waiting page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the waiting page.",
        minutes=5,
    )
    started = store.save_resource(
        url="https://learn.microsoft.com/started",
        title="Started page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the started page.",
        minutes=20,
    )
    for resource_id in (blank.id, waiting.id, started.id):
        store.save_artifact(
            resource_id=resource_id,
            kind="study",
            status="ok",
            markdown="## Study\nPlants make food.",
            model_name="gpt-4o-mini",
        )
    store.replace_lesson_checks(
        waiting.id,
        [(f"Question {number}?", "answer", SOURCE) for number in range(12)],
    )
    store.replace_lesson_checks(
        started.id,
        [(f"Started {number}?", "answer", SOURCE) for number in range(6)],
    )
    store.save_attempt(
        resource_id=started.id,
        question="Started 0?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays off the list.",
    )
    latest = reply_day(store.list_attempts(started.id)[-1].created_at)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    assert "Left to check: 12." in captions
    assert "Left to check: 5." in captions
    assert "Checked 0 of 12." not in captions
    assert latest not in captions
    assert captions.count("Left to check: 5.") == 1
    assert "Left to check: 0." not in captions
    shown = _page_text(app)
    assert "Blank page" in shown
    assert "Later reply" not in shown
    assert "Hidden hint stays off the list." not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("left to check")
    app.run()
    kept = _page_text(app)
    assert "Started page" in kept
    assert "Waiting page" in kept
    assert "Blank page" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("5")
    app.run()
    numbered = _page_text(app)
    assert "Started page" in numbered
    assert "Waiting page" in numbered
    assert "Blank page" not in numbered


def test_saved_list_names_an_empty_lesson_and_find_reads_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    written = store.save_resource(
        url="https://learn.microsoft.com/written",
        title="Written page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the written page.",
        minutes=20,
    )
    empty = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=20,
    )
    store.save_artifact(
        resource_id=written.id,
        kind="lesson",
        status="ok",
        markdown="## Lesson\nPlants make food.",
        model_name="gpt-4o-mini",
    )
    store.save_artifact(
        resource_id=empty.id,
        kind="lesson",
        status="ok",
        markdown="## Lesson\nThe source does not cover a lesson.",
        model_name="gpt-4o-mini",
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    score = "Left out 0 sentences. Questions to check: 0."
    assert score not in captions
    assert "The lesson came back empty." in captions
    assert captions.count("The lesson came back empty.") == 1
    shown = _page_text(app)
    assert "Written page" in shown
    assert "Press Rewrite lesson" not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("empty")
    app.run()
    kept = _page_text(app)
    assert "Quiet page" in kept
    assert "Written page" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("lesson")
    app.run()
    both = _page_text(app)
    assert "Quiet page" in both
    assert "Written page" in both


def test_saved_list_names_an_empty_runbook_and_find_reads_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    written = store.save_resource(
        url="https://learn.microsoft.com/written",
        title="Written page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the written page.",
        minutes=20,
    )
    waiting = store.save_resource(
        url="https://learn.microsoft.com/waiting",
        title="Waiting page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the waiting page.",
        minutes=20,
    )
    quiet = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=20,
    )
    empty_runbook = (
        "## Runbook\n"
        "This source does not describe a procedure.\n"
        "The source does not cover a runbook step."
    )
    for resource_id, lesson, runbook in (
        (written.id, "## Lesson\nPlants make food.", "## Runbook\n1. Open the portal."),
        (waiting.id, "## Lesson\nPlants make food.", empty_runbook),
        (quiet.id, "## Lesson\nThe source does not cover a lesson.", empty_runbook),
    ):
        store.save_artifact(
            resource_id=resource_id,
            kind="lesson",
            status="ok",
            markdown=lesson,
            model_name="gpt-4o-mini",
        )
        store.save_artifact(
            resource_id=resource_id,
            kind="runbook",
            status="ok",
            markdown=runbook,
            model_name="gpt-4o-mini",
        )
    store.replace_lesson_checks(
        waiting.id,
        [(f"Question {number}?", "answer", SOURCE) for number in range(3)],
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    note = "This page has no procedure."
    assert note not in captions
    assert "The lesson came back empty." in captions
    assert "Left to check: 3." in captions
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("empty")
    app.run()
    lesson_only = _page_text(app)
    assert "Quiet page" in lesson_only
    assert "Waiting page" not in lesson_only
    assert "Written page" not in lesson_only
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("procedure")
    app.run()
    kept = _page_text(app)
    assert "Quiet page" in kept
    assert "Waiting page" in kept
    assert "Written page" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("runbook")
    app.run()
    every = _page_text(app)
    assert "Quiet page" in every
    assert "Waiting page" in every
    assert "Written page" in every


def test_open_pack_hides_rewrite_runbook_when_the_page_has_no_procedure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    written = store.save_resource(
        url="https://learn.microsoft.com/written",
        title="Written page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the written page.",
        minutes=20,
    )
    quiet = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=20,
    )
    empty_runbook = (
        "## Runbook\n"
        "This source does not describe a procedure.\n"
        "The source does not cover a runbook step."
    )
    sections = {
        "study": "## Study\nPlants make food.",
        "lesson": "## Lesson\nPlants make food.",
        "lab": "## Lab\n1. Name the ingredients.",
        "project": "## Project\nGoal: Explain the page.",
    }
    for resource_id, runbook in (
        (written.id, "## Runbook\n1. Open the portal."),
        (quiet.id, empty_runbook),
    ):
        for kind, markdown in sections.items():
            store.save_artifact(
                resource_id=resource_id,
                kind=kind,
                status="ok",
                markdown=markdown,
                model_name="gpt-4o-mini",
            )
        store.save_artifact(
            resource_id=resource_id,
            kind="runbook",
            status="ok",
            markdown=runbook,
            model_name="gpt-4o-mini",
        )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    def fail_rewrite(*_args, **_kwargs):
        raise AssertionError("a section was rewritten")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    monkeypatch.setattr("studymaster.ui.home.regenerate_section", fail_rewrite)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    opens = [button for button in app.button if button.label == "Open study"]
    opens[0].click()
    app.run()
    labels = [button.label for button in app.button]
    assert "Quiet page" in _page_text(app)
    assert "Rewrite study" in labels
    assert "Rewrite lesson" in labels
    assert "Rewrite lab" in labels
    assert "Rewrite project" in labels
    assert "Rewrite runbook" not in labels
    opens = [button for button in app.button if button.label == "Open study"]
    opens[1].click()
    app.run()
    labels = [button.label for button in app.button]
    assert "Written page" in _page_text(app)
    assert "Rewrite runbook" in labels


def test_saved_list_names_an_uncovered_project_and_find_reads_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    fifteen = store.save_resource(
        url="https://learn.microsoft.com/fifteen",
        title="Fifteen page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the fifteen page.",
        minutes=15,
    )
    twenty = store.save_resource(
        url="https://learn.microsoft.com/twenty",
        title="Twenty page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the twenty page.",
        minutes=20,
    )
    identity = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Identity page",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Explain the identity page.",
        minutes=5,
    )
    uncovered = (
        "## Project\n"
        f"Goal: {COVER}\n"
        f"Deliverable: {COVER}\n"
        "Milestones:\n"
        f"- {COVER}\n"
        f"Done when: {COVER}"
    )
    written = (
        "## Project\n"
        "Goal: Explain the identity page.\n"
        "Deliverable: A short overview.\n"
        "Milestones:\n"
        f"- {COVER}\n"
        "Done when: The overview is written."
    )
    empty_runbook = (
        "## Runbook\n"
        "This source does not describe a procedure.\n"
        "The source does not cover a runbook step."
    )
    for resource_id, project in (
        (fifteen.id, uncovered),
        (twenty.id, uncovered),
        (identity.id, written),
    ):
        for kind, markdown in (
            ("study", "## Study\nPlants make food."),
            ("lesson", "## Lesson\nPlants make food."),
            ("lab", "## Lab\n1. Name the ingredients."),
            ("project", project),
            ("runbook", empty_runbook),
        ):
            store.save_artifact(
                resource_id=resource_id,
                kind=kind,
                status="ok",
                markdown=markdown,
                model_name="gpt-4o-mini",
            )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    note = "The project is not covered by this page."
    procedure = "This page has no procedure."
    assert procedure not in captions
    assert captions.count(note) == 2
    assert note not in pack_markdown(open_saved(store, fifteen.id))
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("covered")
    app.run()
    kept = _page_text(app)
    assert "Fifteen page" in kept
    assert "Twenty page" in kept
    assert "Identity page" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("project")
    app.run()
    every = _page_text(app)
    assert "Fifteen page" in every
    assert "Twenty page" in every
    assert "Identity page" in every


def test_saved_list_names_how_many_questions_have_a_reply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    blank = store.save_resource(
        url="https://learn.microsoft.com/blank",
        title="Blank page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the blank page.",
        minutes=20,
    )
    fresh = store.save_resource(
        url="https://learn.microsoft.com/fresh",
        title="Fresh page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the fresh page.",
        minutes=15,
    )
    started = store.save_resource(
        url="https://learn.microsoft.com/started",
        title="Started page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the started page.",
        minutes=20,
    )
    for resource_id in (blank.id, fresh.id, started.id):
        store.save_artifact(
            resource_id=resource_id,
            kind="study",
            status="ok",
            markdown="## Study\nPlants make food.",
            model_name="gpt-4o-mini",
        )
    store.replace_lesson_checks(
        fresh.id,
        [
            ("One question?", "one", SOURCE),
            ("Two question?", "two", SOURCE),
            ("Three question?", "three", SOURCE),
        ],
    )
    store.replace_lesson_checks(
        started.id,
        [
            ("What do plants use?", "sunlight", SOURCE),
            ("Where does the food go?", "leaves", SOURCE),
        ],
    )
    store.save_attempt(
        resource_id=started.id,
        question="What do plants use?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays off the list.",
    )
    store.save_attempt(
        resource_id=started.id,
        question="What do plants use?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays off the list.",
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    assert "Last check: Partial" not in captions
    assert "Checked 1 of 2." not in captions
    assert "Checked 0 of 3." not in captions
    assert "Checked 2 of 2." not in captions
    assert "Checked 0 of 0." not in captions
    assert "Left to check: 1." in captions
    shown = _page_text(app)
    assert "Blank page" in shown
    assert "Later reply" not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("Checked")
    app.run()
    kept = _page_text(app)
    assert "Started page" in kept
    assert "Fresh page" in kept
    assert "Blank page" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("1 of 2")
    app.run()
    narrowed = _page_text(app)
    assert "Started page" in narrowed
    assert "Fresh page" not in narrowed
    assert "Blank page" not in narrowed


def test_saved_question_names_the_latest_question() -> None:
    assert (
        saved_question("What does the service do?")
        == "Last question: What does the service do?"
    )
    assert saved_question("  Where   does\nthe food go? ") == "Last question: Where does the food go?"
    assert saved_question("   ") == ""


def test_saved_list_names_the_latest_question_and_find_reads_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    quiet = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=20,
    )
    started = store.save_resource(
        url="https://learn.microsoft.com/started",
        title="Started page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the started page.",
        minutes=20,
    )
    for resource_id in (quiet.id, started.id):
        store.save_artifact(
            resource_id=resource_id,
            kind="study",
            status="ok",
            markdown="## Study\nPlants make food.",
            model_name="gpt-4o-mini",
        )
    store.replace_lesson_checks(
        started.id,
        [
            ("What do plants use?", "sunlight", SOURCE),
            ("Where does the food go?", "leaves", SOURCE),
        ],
    )
    store.save_attempt(
        resource_id=started.id,
        question="What do plants use?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays off the list.",
    )
    store.save_attempt(
        resource_id=started.id,
        question="Where does the food go?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays off the list.",
    )
    opened = open_saved(store, started.id)
    assert "Last question:" not in pack_markdown(opened)
    assert "Later reply" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    assert "Checked 2 of 2." not in captions
    assert "Last question: Where does the food go?" not in captions
    assert "Last question: What do plants use?" not in captions
    shown = _page_text(app)
    assert "Quiet page" in shown
    assert "Later reply" not in shown
    assert "Hidden hint stays off the list." not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("food")
    app.run()
    kept = _page_text(app)
    assert "Started page" in kept
    assert "Quiet page" not in kept
    assert "Later reply" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("plants")
    app.run()
    missed = _page_text(app)
    assert "No saved study matches that." in missed
    assert "Started page" not in missed
    assert "Quiet page" not in missed


def test_reply_day_names_the_latest_reply_day() -> None:
    assert reply_day("2026-10-25T16:00:00+00:00") == "Reply day: October 25, 2026."
    assert reply_day("not-a-day") == ""
    assert reply_day("") == ""


def test_saved_list_names_the_reply_day_and_find_reads_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    quiet = store.save_resource(
        url="https://learn.microsoft.com/quiet",
        title="Quiet page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the quiet page.",
        minutes=20,
    )
    started = store.save_resource(
        url="https://learn.microsoft.com/started",
        title="Started page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the started page.",
        minutes=20,
    )
    for resource_id in (quiet.id, started.id):
        store.save_artifact(
            resource_id=resource_id,
            kind="study",
            status="ok",
            markdown="## Study\nPlants make food.",
            model_name="gpt-4o-mini",
        )
    store.replace_lesson_checks(
        started.id,
        [
            ("What do plants use?", "sunlight", SOURCE),
            ("Where does the food go?", "leaves", SOURCE),
        ],
    )
    store.save_attempt(
        resource_id=started.id,
        question="What do plants use?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays off the list.",
    )
    store.save_attempt(
        resource_id=started.id,
        question="Where does the food go?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays off the list.",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE quiz_attempts SET created_at = ? WHERE question = ?",
            ("2026-08-01T16:00:00+00:00", "What do plants use?"),
        )
        connection.execute(
            "UPDATE quiz_attempts SET created_at = ? WHERE question = ?",
            ("2026-09-03T16:00:00+00:00", "Where does the food go?"),
        )
    latest = reply_day("2026-09-03T16:00:00+00:00")
    opened = open_saved(store, started.id)
    assert "Reply day:" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    captions = [str(block.value) for block in app.caption]
    question = "Last question: Where does the food go?"
    assert question not in captions
    assert latest not in captions
    assert reply_day("2026-08-01T16:00:00+00:00") not in captions
    shown = _page_text(app)
    assert "Quiet page" in shown
    assert "Later reply" not in shown
    assert "Hidden hint stays off the list." not in shown
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("September")
    app.run()
    kept = _page_text(app)
    assert "Started page" in kept
    assert "Quiet page" not in kept
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("August")
    app.run()
    missed = _page_text(app)
    assert "No saved study matches that." in missed
    assert "Started page" not in missed
    assert "Quiet page" not in missed


def test_open_study_fills_the_level_goal_and_minutes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["page_link"] = "https://example.com/keep"
    app.session_state["article_text"] = "Old lesson words"
    app.run()
    assert next(box for box in app.text_input if box.label == "Page link").value == (
        "https://example.com/keep"
    )
    assert next(box for box in app.text_area if box.label == "Article text").value == (
        "Old lesson words"
    )
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    assert next(box for box in app.selectbox if box.label == "Level").value == "Intermediate"
    assert next(box for box in app.text_input if box.label == "Goal").value == (
        "Master the material."
    )
    assert int(next(box for box in app.number_input if box.label == "Minutes").value) == 5
    assert next(box for box in app.text_input if box.label == "Page link").value == (
        "https://learn.microsoft.com/identity"
    )
    assert next(box for box in app.text_area if box.label == "Article text").value == ""

    next(button for button in app.button if button.label == "Start over").click()
    app.run()
    assert next(box for box in app.selectbox if box.label == "Level").value == "Beginner"
    assert next(box for box in app.text_input if box.label == "Goal").value == ""
    assert int(next(box for box in app.number_input if box.label == "Minutes").value) == 20
    assert next(box for box in app.text_input if box.label == "Page link").value == ""


def test_open_pasted_lesson_leaves_the_page_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="pasted-text",
        title="Pasted lesson",
        status="ok",
        extracted_text=SOURCE,
        level="advanced",
        goal="Explain the pasted lesson.",
        minutes=10,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["page_link"] = "https://example.com/keep"
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    assert next(box for box in app.text_input if box.label == "Page link").value == (
        "https://example.com/keep"
    )
    assert "pasted-text" not in next(
        box for box in app.text_input if box.label == "Page link"
    ).value
    assert next(box for box in app.selectbox if box.label == "Level").value == "Advanced"
    assert next(box for box in app.text_input if box.label == "Goal").value == (
        "Explain the pasted lesson."
    )
    assert int(next(box for box in app.number_input if box.label == "Minutes").value) == 10
    assert next(box for box in app.text_area if box.label == "Article text").value == SOURCE

    next(button for button in app.button if button.label == "Start over").click()
    app.run()
    assert next(box for box in app.text_area if box.label == "Article text").value == ""


def test_open_saved_names_the_pieces_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    for kind in ("study", "lesson"):
        store.save_artifact(
            resource_id=saved.id,
            kind=kind,
            status="ok",
            markdown=f"## {kind}\nName the identity service.",
            model_name="gpt-4o-mini",
        )
    store.save_artifact(
        resource_id=saved.id,
        kind="lab",
        status="error",
        error_message="The lab failed.",
        model_name="gpt-4o-mini",
    )
    opened = open_saved(store, saved.id)
    assert saved_pieces(
        section.kind for section in opened.sections if section.status == "ok"
    ) == "Study, lesson"
    assert "Study, lesson" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "Study, lesson" in lines
    assert "Study, lesson, lab, project, runbook" not in lines
    assert shown.index("Master the material.") < shown.index("Study, lesson")


def test_open_saved_names_the_latest_check_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    store.save_attempt(
        resource_id=saved.id,
        question="What does the service do?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays in the question.",
    )
    store.save_attempt(
        resource_id=saved.id,
        question="What does the service do?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays in the question.",
    )
    opened = open_saved(store, saved.id)
    assert "Last check: Partial" not in pack_markdown(opened)
    assert "Later reply" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    score = "Left out 0 sentences. Questions to check: 0."
    first_score = captions.index(score)
    assert captions[first_score + 1] == "Last check: Partial"
    assert "Last check: Incorrect" not in captions
    assert "Later reply" not in captions


def test_open_pack_keeps_the_details_under_about_this_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="lesson",
        status="ok",
        markdown="## Lesson\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    store.replace_lesson_checks(
        saved.id,
        [("Where does the food go?", "leaves", SOURCE)],
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    assert len(app.expander) == 0
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    assert len(app.expander) == 1
    assert app.expander[0].label == "About this pack"
    assert app.expander[0].proto.expanded is False
    captions = [str(block.value) for block in app.caption]
    assert "Read from learn.microsoft.com" in captions
    assert "For an intermediate learner" in captions
    assert "5 minutes" in captions
    assert "Master the material." in captions
    questions = [str(block.value) for block in app.subheader]
    assert questions[0] == "Where does the food go?"
    order = _page_order(app)
    assert order.index("Download Word") < order.index("Where does the food go?")
    rows = [
        box
        for box in app.container
        if {
            str(getattr(child, "label", ""))
            for child in box.children.values()
        }
        >= {"Download Markdown", "Download Word"}
    ]
    assert len(rows) == 1
    assert rows[0].proto.flex_container.direction == 2
    assert "About this pack" not in pack_markdown(open_saved(store, saved.id))


def test_open_pack_says_it_is_already_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    from studymaster.agents.coordinator import pack_size_line

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    note = (
        "This pack is already open. A new pack starts when the page, the level, "
        "the goal, or the minutes change."
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    closed = [str(block.value) for block in app.caption]
    assert note not in closed
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    assert captions[captions.index(pack_size_line()) + 1] == note
    assert captions.count(note) == 1
    assert note not in pack_markdown(open_saved(store, saved.id))
    next(button for button in app.button if button.label == "Start over").click()
    app.run()
    cleared = [str(block.value) for block in app.caption]
    assert note not in cleared


def test_open_saved_names_the_progress_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    store.replace_lesson_checks(
        saved.id,
        [
            ("What does the service do?", "It signs people in.", SOURCE),
            ("Where is the tenant?", "In the directory.", SOURCE),
        ],
    )
    store.save_attempt(
        resource_id=saved.id,
        question="What does the service do?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays in the question.",
    )
    store.save_attempt(
        resource_id=saved.id,
        question="What does the service do?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays in the question.",
    )
    opened = open_saved(store, saved.id)
    assert "Checked 1 of 2." not in pack_markdown(opened)
    assert "Later reply" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    score = "Left out 0 sentences. Questions to check: 2."
    first_score = captions.index(score)
    assert captions[first_score + 1] == "Last check: Partial"
    assert captions[first_score + 2] == "Checked 1 of 2."
    assert captions.count("Checked 1 of 2.") == 1
    assert "Checked 2 of 2." not in captions
    assert "Later reply" not in captions


def test_open_saved_names_the_latest_question_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    store.replace_lesson_checks(
        saved.id,
        [
            ("What do plants use?", "sunlight", SOURCE),
            ("Where does the food go?", "leaves", SOURCE),
        ],
    )
    store.save_attempt(
        resource_id=saved.id,
        question="What do plants use?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays in the question.",
    )
    store.save_attempt(
        resource_id=saved.id,
        question="Where does the food go?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays in the question.",
    )
    opened = open_saved(store, saved.id)
    assert "Last question:" not in pack_markdown(opened)
    assert "Later reply" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    progress = "Checked 2 of 2."
    first_progress = captions.index(progress)
    assert captions[first_progress + 1] == "Last question: Where does the food go?"
    assert captions.count("Last question: Where does the food go?") == 1
    assert "Last question: What do plants use?" not in captions
    assert "Later reply" not in captions
    assert "Hidden hint stays in the question." not in captions


def test_open_saved_names_the_reply_day_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    store.replace_lesson_checks(
        saved.id,
        [
            ("What do plants use?", "sunlight", SOURCE),
            ("Where does the food go?", "leaves", SOURCE),
        ],
    )
    store.save_attempt(
        resource_id=saved.id,
        question="What do plants use?",
        learner_answer="Earlier reply",
        score="incorrect",
        hint="Hidden hint stays in the question.",
    )
    store.save_attempt(
        resource_id=saved.id,
        question="Where does the food go?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays in the question.",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE quiz_attempts SET created_at = ? WHERE question = ?",
            ("2026-08-01T16:00:00+00:00", "What do plants use?"),
        )
        connection.execute(
            "UPDATE quiz_attempts SET created_at = ? WHERE question = ?",
            ("2026-09-03T16:00:00+00:00", "Where does the food go?"),
        )
    latest = reply_day("2026-09-03T16:00:00+00:00")
    opened = open_saved(store, saved.id)
    assert "Reply day:" not in pack_markdown(opened)
    assert "Later reply" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    question = "Last question: Where does the food go?"
    first_question = captions.index(question)
    assert captions[first_question + 1] == latest
    assert captions.count(latest) == 1
    assert reply_day("2026-08-01T16:00:00+00:00") not in captions
    assert "Later reply" not in captions
    assert "Hidden hint stays in the question." not in captions


def test_open_saved_names_how_many_questions_are_still_waiting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    waiting = store.save_resource(
        url="https://learn.microsoft.com/waiting",
        title="Waiting page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the waiting page.",
        minutes=15,
    )
    started = store.save_resource(
        url="https://learn.microsoft.com/started",
        title="Started page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the started page.",
        minutes=20,
    )
    for resource_id in (waiting.id, started.id):
        store.save_artifact(
            resource_id=resource_id,
            kind="study",
            status="ok",
            markdown="## Study\nPlants make food.",
            model_name="gpt-4o-mini",
        )
    store.replace_lesson_checks(
        waiting.id,
        [(f"Question {number}?", "answer", SOURCE) for number in range(3)],
    )
    store.replace_lesson_checks(
        started.id,
        [(f"Started {number}?", "answer", SOURCE) for number in range(6)],
    )
    store.save_attempt(
        resource_id=started.id,
        question="Started 0?",
        learner_answer="Later reply",
        score="partial",
        hint="Hidden hint stays in the question.",
    )
    latest = reply_day(store.list_attempts(started.id)[-1].created_at)
    assert "Left to check:" not in pack_markdown(open_saved(store, started.id))
    assert "Left to check:" not in pack_markdown(open_saved(store, waiting.id))

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    assert captions[captions.index(latest) + 1] == "Left to check: 5."
    assert captions.count("Left to check: 5.") == 2
    assert "Later reply" not in captions
    assert "Hidden hint stays in the question." not in captions
    waiting_button = [button for button in app.button if button.label == "Open study"][1]
    waiting_button.click()
    app.run()
    opened = [str(block.value) for block in app.caption]
    assert opened[opened.index("Checked 0 of 3.") + 1] == "Left to check: 3."
    assert opened.count("Left to check: 3.") == 2


def test_open_saved_names_an_uncovered_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    identity = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Identity page",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Explain the identity page.",
        minutes=5,
    )
    fifteen = store.save_resource(
        url="https://learn.microsoft.com/fifteen",
        title="Fifteen page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the fifteen page.",
        minutes=15,
    )
    uncovered = (
        "## Project\n"
        f"Goal: {COVER}\n"
        f"Deliverable: {COVER}\n"
        "Milestones:\n"
        f"- {COVER}"
    )
    written = (
        "## Project\n"
        "Goal: Explain the identity page.\n"
        "Deliverable: A short overview."
    )
    for resource_id, project, total in (
        (identity.id, written, 12),
        (fifteen.id, uncovered, 5),
    ):
        store.save_artifact(
            resource_id=resource_id,
            kind="project",
            status="ok",
            markdown=project,
            model_name="gpt-4o-mini",
        )
        store.replace_lesson_checks(
            resource_id,
            [(f"Question {number}?", "answer", SOURCE) for number in range(total)],
        )
    note = "The project is not covered by this page."
    assert note not in pack_markdown(open_saved(store, fifteen.id))

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    captions = [str(block.value) for block in app.caption]
    assert captions[captions.index("Left to check: 5.") + 1] == note
    assert captions.count(note) == 2
    identity_button = [button for button in app.button if button.label == "Open study"][1]
    identity_button.click()
    app.run()
    opened = [str(block.value) for block in app.caption]
    assert opened[opened.index("Left to check: 12.") + 1] != note
    assert opened.count(note) == 1


def test_open_saved_names_the_day_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE resources SET fetched_at = ? WHERE id = ?",
            ("2026-10-25T16:00:00+00:00", saved.id),
        )
    opened = open_saved(store, saved.id)
    assert saved_day(opened.saved_on) == "Saved October 25, 2026"
    assert "Saved October 25, 2026" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "Saved October 25, 2026" in lines
    assert shown.index("Master the material.") < shown.index("Saved October 25, 2026")


def test_open_saved_names_the_goal_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    opened = open_saved(store, saved.id)
    assert opened.goal == "Master the material."
    assert "Master the material." not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "Master the material." in lines
    assert shown.index("5 minutes") < shown.index("Master the material.")


def test_open_saved_names_the_minutes_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    opened = open_saved(store, saved.id)
    assert opened.minutes == 5
    assert "5 minutes" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    shown = _page_text(app)
    lines = shown.splitlines()
    assert "5 minutes" in lines
    assert shown.index("For an intermediate learner") < shown.index("5 minutes")


def test_open_saved_names_the_level_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    saved = store.save_resource(
        url="https://learn.microsoft.com/identity",
        title="Get started with identity architecture",
        status="ok",
        extracted_text=SOURCE,
        level="intermediate",
        goal="Master the material.",
        minutes=5,
    )
    store.save_artifact(
        resource_id=saved.id,
        kind="study",
        status="ok",
        markdown="## Study\nName the identity service.",
        model_name="gpt-4o-mini",
    )
    opened = open_saved(store, saved.id)
    assert opened.level == "intermediate"
    assert "For an intermediate learner" not in pack_markdown(opened)

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    shown = _page_text(app)
    assert "For an intermediate learner" in shown.splitlines()
    assert shown.index("Get started with identity architecture") < shown.index(
        "For an intermediate learner"
    )


def test_open_saved_names_the_site_and_does_not_call_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        title="Learn about data loss prevention",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain how data loss prevention protects sensitive information.",
        minutes=15,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()
    shown = _page_text(app)
    assert "Read from learn.microsoft.com" in shown
    assert shown.index("Learn about data loss prevention") < shown.index(
        "Read from learn.microsoft.com"
    )


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


def test_find_keeps_a_full_pack_when_the_pieces_line_matches() -> None:
    from dataclasses import replace

    short = replace(_named("Short pack"), id=1)
    full = replace(_named("Full pack"), id=2)
    pieces = {
        short.id: "Study, lesson",
        full.id: "Study, lesson, lab, project, runbook",
    }
    assert matching_studies([short, full], "  RUNBOOK ", pieces) == [full]
    assert matching_studies([short, full], "lesson", pieces) == [short, full]
    assert matching_studies([short, full], "short pack", pieces) == [short]


def test_find_keeps_the_minute_count_as_a_whole_number() -> None:
    from dataclasses import replace

    five = replace(_named("Five"), id=1, minutes=5)
    fifteen = replace(_named("Fifteen"), id=2, minutes=15)
    twenty = replace(_named("Twenty"), id=3, minutes=20)
    lengths = {
        item.id: saved_minutes(item.minutes) for item in (five, fifteen, twenty)
    }
    assert matching_studies([five, fifteen, twenty], "15", lengths=lengths) == [fifteen]
    assert matching_studies([five, fifteen, twenty], "5", lengths=lengths) == [five]
    assert matching_studies([five, fifteen, twenty], "20", lengths=lengths) == [twenty]
    assert matching_studies([five, fifteen, twenty], "minutes", lengths=lengths) == [
        five,
        fifteen,
        twenty,
    ]


def test_find_keeps_a_pack_when_the_level_line_matches() -> None:
    from dataclasses import replace

    beginner = replace(_named("First page"), id=1, level="beginner")
    intermediate = replace(_named("Second page"), id=2, level="intermediate")
    advanced = replace(_named("Third page"), id=3, level="advanced")
    blank = replace(_named("Fourth page"), id=4, level="")
    rows = [beginner, intermediate, advanced, blank]
    levels = {item.id: saved_level(item.level) for item in rows}
    assert matching_studies(rows, "beginner", levels=levels) == [beginner]
    assert matching_studies(rows, "INTERMEDIATE", levels=levels) == [intermediate]
    assert matching_studies(rows, "advanced", levels=levels) == [advanced]
    assert matching_studies(rows, "learner", levels=levels) == [intermediate, advanced]


def test_find_keeps_a_pack_when_the_score_line_matches() -> None:
    from dataclasses import replace

    five = replace(_named("First page"), id=1, minutes=15)
    twelve = replace(_named("Second page"), id=2, minutes=5)
    seventy = replace(_named("Third page"), id=3, minutes=20)
    plain = replace(_named("Fourth page"), id=4, minutes=15)
    rows = [five, twelve, seventy, plain]
    scores = {
        five.id: "Left out 77 sentences. Questions to check: 5.",
        twelve.id: "Left out 0 sentences. Questions to check: 12.",
        seventy.id: "Left out 74 sentences. Questions to check: 6.",
        plain.id: "Left out 0 sentences. Questions to check: 0.",
    }
    lengths = {item.id: saved_minutes(item.minutes) for item in rows}
    assert matching_studies(rows, "5", lengths=lengths, scores=scores) == [five, twelve]
    assert matching_studies(rows, "12", lengths=lengths, scores=scores) == [twelve]
    assert matching_studies(rows, "77", lengths=lengths, scores=scores) == [five]
    assert matching_studies(rows, "15", lengths=lengths, scores=scores) == [five, plain]
    assert matching_studies(rows, "left out", scores=scores) == rows


def test_find_keeps_a_pack_when_the_check_line_matches() -> None:
    from dataclasses import replace

    partial = replace(_named("First page"), id=1)
    incorrect = replace(_named("Second page"), id=2)
    plain = replace(_named("Third page"), id=3)
    rows = [partial, incorrect, plain]
    checks = {
        partial.id: "Last check: Partial",
        incorrect.id: "Last check: Incorrect",
        plain.id: "",
    }
    assert matching_studies(rows, "partial", checks=checks) == [partial]
    assert matching_studies(rows, "  PARTIAL ", checks=checks) == [partial]
    assert matching_studies(rows, "incorrect", checks=checks) == [incorrect]
    assert matching_studies(rows, "correct", checks=checks) == []
    assert matching_studies(rows, "check", checks=checks) == [partial, incorrect]


def test_find_keeps_a_pack_when_the_progress_line_matches() -> None:
    from dataclasses import replace

    one = replace(_named("First page"), id=1, minutes=20)
    twelve = replace(_named("Second page"), id=2, minutes=20)
    five = replace(_named("Third page"), id=3, minutes=15)
    plain = replace(_named("Fourth page"), id=4, minutes=20)
    rows = [one, twelve, five, plain]
    progress = {
        one.id: "Checked 1 of 6.",
        twelve.id: "Checked 0 of 12.",
        five.id: "Checked 0 of 5.",
        plain.id: "",
    }
    lengths = {item.id: saved_minutes(item.minutes) for item in rows}
    assert matching_studies(rows, "checked", progress=progress) == [one, twelve, five]
    assert matching_studies(rows, "  CHECKED ", progress=progress) == [one, twelve, five]
    assert matching_studies(rows, "1 of 6", lengths=lengths, progress=progress) == [one]
    assert matching_studies(rows, "1", lengths=lengths, progress=progress) == [one]
    assert matching_studies(rows, "12", lengths=lengths, progress=progress) == [twelve]
    assert matching_studies(rows, "5", lengths=lengths, progress=progress) == [five]


def test_find_keeps_a_pack_when_the_question_line_matches() -> None:
    from dataclasses import replace

    asked = replace(_named("First page"), id=1)
    titled = replace(_named("Learn about data loss prevention"), id=2)
    quiet = replace(_named("Third page"), id=3)
    questions = {
        asked.id: "Last question: What is the primary purpose of Data Loss Prevention?",
        titled.id: "",
        quiet.id: "",
    }
    rows = [asked, titled, quiet]
    assert matching_studies(rows, "purpose", questions=questions) == [asked]
    assert matching_studies(rows, "  PURPOSE ", questions=questions) == [asked]
    assert matching_studies(rows, "primary purpose", questions=questions) == [asked]
    assert matching_studies(rows, "plants", questions=questions) == []
    assert matching_studies(rows, "prevention", questions=questions) == [asked, titled]


def test_find_keeps_a_pack_when_questions_are_still_waiting() -> None:
    from dataclasses import replace

    twenty = replace(_named("Twenty page"), id=1, minutes=20)
    fifteen = replace(_named("Fifteen page"), id=2, minutes=15)
    identity = replace(_named("Identity page"), id=3, minutes=5)
    entra = replace(_named("Entra page"), id=4, minutes=20)
    rows = [twenty, fifteen, identity, entra]
    lengths = {item.id: saved_minutes(item.minutes) for item in rows}
    progress = {
        twenty.id: "Checked 1 of 6.",
        fifteen.id: "Checked 0 of 5.",
        identity.id: "Checked 0 of 12.",
    }
    scores = {
        twenty.id: "Left out 74 sentences. Questions to check: 6.",
        fifteen.id: "Left out 77 sentences. Questions to check: 5.",
        identity.id: "Left out 0 sentences. Questions to check: 12.",
        entra.id: "Left out 0 sentences. Questions to check: 0.",
    }
    remaining = {
        twenty.id: "Left to check: 5.",
        fifteen.id: "Left to check: 5.",
        identity.id: "Left to check: 12.",
    }
    kept = [twenty, fifteen, identity]
    assert matching_studies(
        rows, "left to check", lengths=lengths, scores=scores, progress=progress, remaining=remaining
    ) == kept
    assert matching_studies(
        rows, "  LEFT TO CHECK ", lengths=lengths, scores=scores, progress=progress, remaining=remaining
    ) == kept
    assert matching_studies(
        rows, "5", lengths=lengths, scores=scores, progress=progress, remaining=remaining
    ) == kept
    assert matching_studies(
        rows, "5", lengths=lengths, scores=scores, progress=progress
    ) == [fifteen, identity]
    assert matching_studies(rows, "waiting", remaining=remaining) == []


def test_find_keeps_a_pack_when_the_lesson_came_back_empty() -> None:
    from dataclasses import replace

    entra = replace(_named("What is Microsoft Entra?"), id=1)
    fifteen = replace(_named("Fifteen page"), id=2)
    twenty = replace(_named("Twenty page"), id=3)
    identity = replace(_named("Identity page"), id=4)
    rows = [entra, fifteen, twenty, identity]
    pieces = {item.id: "Study, lesson, lab, project, runbook" for item in rows}
    empty = {entra.id: "The lesson came back empty."}
    assert matching_studies(rows, "empty", pieces=pieces, empty=empty) == [entra]
    assert matching_studies(rows, "  EMPTY ", pieces=pieces, empty=empty) == [entra]
    assert matching_studies(rows, "came back", pieces=pieces, empty=empty) == [entra]
    assert matching_studies(rows, "lesson", pieces=pieces, empty=empty) == rows
    assert matching_studies(rows, "empty", pieces=pieces) == []
    assert matching_studies(rows, "plants", pieces=pieces, empty=empty) == []


def test_find_keeps_a_pack_when_the_page_has_no_procedure() -> None:
    from dataclasses import replace

    entra = replace(_named("What is Microsoft Entra?"), id=1)
    fifteen = replace(_named("Fifteen page"), id=2)
    twenty = replace(_named("Twenty page"), id=3)
    identity = replace(_named("Identity page"), id=4)
    written = replace(_named("Written page"), id=5)
    rows = [entra, fifteen, twenty, identity, written]
    pieces = {item.id: "Study, lesson, lab, project, runbook" for item in rows}
    runbooks = {
        entra.id: "This page has no procedure.",
        fifteen.id: "This page has no procedure.",
        twenty.id: "This page has no procedure.",
        identity.id: "This page has no procedure.",
    }
    empty = {entra.id: "The lesson came back empty."}
    kept = [entra, fifteen, twenty, identity]
    assert matching_studies(rows, "procedure", pieces=pieces, runbooks=runbooks) == kept
    assert matching_studies(rows, "  PROCEDURE ", pieces=pieces, runbooks=runbooks) == kept
    assert matching_studies(rows, "empty", pieces=pieces, empty=empty, runbooks=runbooks) == [entra]
    assert matching_studies(rows, "runbook", pieces=pieces, runbooks=runbooks) == rows
    assert matching_studies(rows, "plants", pieces=pieces, runbooks=runbooks) == []


def test_find_keeps_a_pack_when_the_project_is_not_covered() -> None:
    from dataclasses import replace

    fifteen = replace(_named("Fifteen page"), id=1, minutes=15)
    twenty = replace(_named("Twenty page"), id=2, minutes=20)
    entra = replace(_named("What is Microsoft Entra?"), id=3, minutes=20)
    identity = replace(_named("Identity page"), id=4, minutes=5)
    rows = [fifteen, twenty, entra, identity]
    pieces = {item.id: "Study, lesson, lab, project, runbook" for item in rows}
    projects = {
        fifteen.id: "The project is not covered by this page.",
        twenty.id: "The project is not covered by this page.",
    }
    kept = [fifteen, twenty]
    assert matching_studies(rows, "covered", pieces=pieces, projects=projects) == kept
    assert matching_studies(rows, "  COVERED ", pieces=pieces, projects=projects) == kept
    assert matching_studies(rows, "project", pieces=pieces, projects=projects) == rows
    assert matching_studies(rows, "covered", pieces=pieces) == []
    assert matching_studies(rows, "plants", pieces=pieces, projects=projects) == []


def test_find_keeps_a_pack_when_the_reply_day_matches() -> None:
    from dataclasses import replace

    asked = replace(_named("First page"), id=1)
    saved = replace(_named("Second page"), id=2)
    quiet = replace(_named("Third page"), id=3)
    rows = [asked, saved, quiet]
    days = {item.id: "Saved October 25, 2026" for item in rows}
    replies = {
        asked.id: "Reply day: October 25, 2026.",
        saved.id: "",
        quiet.id: "",
    }
    assert matching_studies(rows, "reply", days=days, replies=replies) == [asked]
    assert matching_studies(rows, "  REPLY ", days=days, replies=replies) == [asked]
    assert matching_studies(rows, "25", days=days, replies=replies) == rows
    assert matching_studies(rows, "September", days=days, replies=replies) == []


def test_find_keeps_a_pack_when_the_site_line_matches() -> None:
    from dataclasses import replace

    learn = replace(
        _named("Data loss prevention"),
        id=1,
        url="https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
    )
    pasted = replace(_named("Pasted lesson"), id=2, url="pasted-text")
    sites = {
        learn.id: "Read from learn.microsoft.com",
        pasted.id: "",
    }
    assert matching_studies([learn, pasted], "learn.microsoft.com", sites=sites) == [learn]
    assert matching_studies([learn, pasted], "PASTED", sites=sites) == [pasted]


def test_find_keeps_a_pack_when_the_saved_day_matches() -> None:
    from dataclasses import replace

    october = replace(_named("First page"), id=1, minutes=20)
    september = replace(_named("Second page"), id=2, minutes=20)
    short = replace(_named("Third page"), id=3, minutes=5)
    lengths = {item.id: saved_minutes(item.minutes) for item in (october, september, short)}
    days = {
        october.id: "Saved October 25, 2026",
        september.id: "Saved September 3, 2026",
        short.id: "Saved October 25, 2026",
    }
    assert matching_studies([october, september, short], "October", days=days) == [
        october,
        short,
    ]
    assert matching_studies([october, september, short], "25", lengths=lengths, days=days) == [
        october,
        short,
    ]
    assert matching_studies([october, september, short], "5", lengths=lengths, days=days) == [
        short
    ]
    assert matching_studies([october, september], "20", lengths=lengths, days=days) == [
        october,
        september,
    ]


def test_find_box_uses_the_saved_day_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import sqlite3

    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    october = store.save_resource(
        url="https://learn.microsoft.com/october",
        title="First page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the first page.",
        minutes=20,
    )
    september = store.save_resource(
        url="https://learn.microsoft.com/september",
        title="Second page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the second page.",
        minutes=20,
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE resources SET fetched_at = ? WHERE id = ?",
            ("2026-10-25T16:00:00+00:00", october.id),
        )
        connection.execute(
            "UPDATE resources SET fetched_at = ? WHERE id = ?",
            ("2026-09-03T16:00:00+00:00", september.id),
        )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("October")
    app.run()
    shown = _page_text(app)
    assert "First page" in shown
    assert "Second page" not in shown

    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("5")
    app.run()
    missed = _page_text(app)
    assert "No saved study matches that." in missed


def test_find_box_uses_the_level_line_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/first",
        title="First page",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the first page.",
        minutes=20,
    )
    store.save_resource(
        url="https://learn.microsoft.com/second",
        title="Second page",
        status="ok",
        extracted_text=SOURCE,
        level="advanced",
        goal="Explain the second page.",
        minutes=20,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("beginner")
    app.run()
    shown = _page_text(app)
    assert "First page" in shown
    assert "Second page" not in shown
    assert "For an advanced learner" not in shown

    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("advanced")
    app.run()
    kept = _page_text(app)
    assert "Second page" in kept
    assert "First page" not in kept
    assert "For a beginner" not in kept


def test_find_box_uses_the_site_line_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        title="Data loss prevention",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the public page.",
        minutes=15,
    )
    store.save_resource(
        url="pasted-text",
        title="Pasted lesson",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the pasted lesson.",
        minutes=10,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("learn.microsoft.com")
    app.run()
    shown = _page_text(app)
    assert "Data loss prevention" in shown
    assert "Pasted lesson" not in shown


def test_find_box_uses_the_minutes_line_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    store.save_resource(
        url="https://learn.microsoft.com/fifteen",
        title="Fifteen minute pack",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the fifteen minute pack.",
        minutes=15,
    )
    store.save_resource(
        url="https://learn.microsoft.com/five",
        title="Five minute pack",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the five minute pack.",
        minutes=5,
    )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("15")
    app.run()
    shown = _page_text(app)
    assert "Fifteen minute pack" in shown
    assert "Five minute pack" not in shown

    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("5")
    app.run()
    narrowed = _page_text(app)
    assert "Five minute pack" in narrowed
    assert "Fifteen minute pack" not in narrowed


def test_find_box_uses_the_pieces_line_and_does_not_start_a_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from streamlit.testing.v1 import AppTest

    database = tmp_path / "study.db"
    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    store = StudyStore(database)
    short = store.save_resource(
        url="https://learn.microsoft.com/short",
        title="Short lesson",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the short lesson.",
        minutes=5,
    )
    full = store.save_resource(
        url="https://learn.microsoft.com/full",
        title="Full pack",
        status="ok",
        extracted_text=SOURCE,
        level="beginner",
        goal="Explain the full pack.",
        minutes=20,
    )
    for kind in ("study", "lesson"):
        store.save_artifact(
            resource_id=short.id,
            kind=kind,
            status="ok",
            markdown=f"## {kind}",
            model_name="gpt-4o-mini",
        )
    for kind in ("study", "lesson", "lab", "project", "runbook"):
        store.save_artifact(
            resource_id=full.id,
            kind=kind,
            status="ok",
            markdown=f"## {kind}",
            model_name="gpt-4o-mini",
        )

    def fail_study(*_args, **_kwargs):
        raise AssertionError("a new study was started")

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    finder = next(box for box in app.text_input if box.label == "Find a study")
    finder.set_value("runbook")
    app.run()
    shown = _page_text(app)
    assert "Full pack" in shown
    assert "Short lesson" not in shown


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
    assert finder.placeholder == (
        "Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, reply, left, or empty"
    )
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
    next(box for box in app.text_input if box.label == "What do you want to learn?").set_value(
        "data loss prevention"
    )
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
    assert next(box for box in app.text_input if box.label == "What do you want to learn?").value == ""
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


def _page_order(app: object) -> list[str]:
    """Return download labels and question titles in the order they are drawn."""
    found: list[str] = []

    def walk(node: object) -> None:
        kind = getattr(node, "type", "")
        if kind == "download_button":
            found.append(str(getattr(node, "label", "")))
        elif kind == "subheader":
            found.append(str(getattr(node, "value", "")))
        children = getattr(node, "children", None)
        if isinstance(children, dict):
            for child in children.values():
                walk(child)

    walk(app.main)
    return found


def _page_text(app: object) -> str:
    parts: list[str] = []
    for collection in ("markdown", "subheader", "header", "caption", "error"):
        for block in getattr(app, collection):
            parts.append(str(getattr(block, "value", "")))
    return "\n".join(parts)
