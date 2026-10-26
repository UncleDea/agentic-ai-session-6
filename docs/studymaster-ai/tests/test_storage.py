"""Tests for the local study database.

Each test uses a temporary database file.
"""

from pathlib import Path

import pytest

from studymaster.storage.database import (
    STATUS_ERROR,
    STATUS_OK,
    StorageError,
    StudyStore,
    content_hash,
)

PAGE = "Plants make food from sunlight, water, and carbon dioxide. " * 8
URL = "https://learn.microsoft.com/entra/identity/conditional-access/overview"


def store(tmp_path: Path) -> StudyStore:
    return StudyStore(tmp_path / "studymaster.db")


def test_saved_page_can_be_read_back(tmp_path: Path) -> None:
    database = store(tmp_path)

    saved = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )

    loaded = database.get_resource(saved.id)
    assert loaded.url == URL
    assert loaded.title == "Conditional Access"
    assert loaded.status == STATUS_OK
    assert loaded.error_message == ""
    assert loaded.extracted_text == PAGE
    assert loaded.content_hash == content_hash(PAGE)
    assert loaded.level == "beginner"
    assert loaded.goal == "Explain Conditional Access"
    assert loaded.minutes == 25
    assert loaded.fetched_at


def test_failed_fetch_is_stored_with_the_error_and_empty_text(tmp_path: Path) -> None:
    database = store(tmp_path)

    saved = database.save_resource(
        url="https://example.com/missing",
        title="",
        status=STATUS_ERROR,
        error_message="This page did not include readable article text.",
        extracted_text="",
    )

    loaded = database.get_resource(saved.id)
    assert loaded.status == STATUS_ERROR
    assert loaded.error_message == "This page did not include readable article text."
    assert loaded.extracted_text == ""


def test_five_artifacts_include_one_failed_section(tmp_path: Path) -> None:
    database = store(tmp_path)
    resource = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
    )
    bodies = {
        "study": "Study notes",
        "lesson": "Lesson notes",
        "lab": "",
        "project": "Project notes",
        "runbook": "Runbook notes",
    }
    for kind, body in bodies.items():
        if kind == "lab":
            database.save_artifact(
                resource_id=resource.id,
                kind=kind,
                status=STATUS_ERROR,
                error_message="The lab could not be written.",
                model_name="gpt-4o-mini",
            )
        else:
            database.save_artifact(
                resource_id=resource.id,
                kind=kind,
                status=STATUS_OK,
                markdown=body,
                model_name="gpt-4o-mini",
            )

    artifacts = database.list_artifacts(resource.id)
    assert [artifact.kind for artifact in artifacts] == [
        "study",
        "lesson",
        "lab",
        "project",
        "runbook",
    ]
    lab = artifacts[2]
    assert lab.status == STATUS_ERROR
    assert lab.error_message == "The lab could not be written."
    assert lab.markdown == ""
    assert artifacts[0].markdown == "Study notes"


def test_replacing_one_artifact_leaves_the_others(tmp_path: Path) -> None:
    database = store(tmp_path)
    resource = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
    )
    database.save_artifact(
        resource_id=resource.id,
        kind="study",
        status=STATUS_OK,
        markdown="First study",
        model_name="gpt-4o-mini",
    )
    database.save_artifact(
        resource_id=resource.id,
        kind="lesson",
        status=STATUS_OK,
        markdown="Lesson stays",
        model_name="gpt-4o-mini",
    )

    replaced = database.save_artifact(
        resource_id=resource.id,
        kind="study",
        status=STATUS_OK,
        markdown="Second study",
        model_name="gpt-4o-mini",
    )

    artifacts = database.list_artifacts(resource.id)
    assert len(artifacts) == 2
    assert replaced.markdown == "Second study"
    assert artifacts[0].markdown == "Second study"
    assert artifacts[1].markdown == "Lesson stays"


def test_quiz_attempt_is_listed_with_its_page(tmp_path: Path) -> None:
    database = store(tmp_path)
    resource = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
    )

    saved = database.save_attempt(
        resource_id=resource.id,
        question="What does Conditional Access check?",
        learner_answer="It checks signals after sign-in.",
        score="partial",
        hint="Name one signal from the page.",
    )

    attempts = database.list_attempts(resource.id)
    assert len(attempts) == 1
    assert attempts[0].id == saved.id
    assert attempts[0].score == "partial"
    assert attempts[0].hint == "Name one signal from the page."
    assert attempts[0].created_at


def test_same_page_text_is_found_again(tmp_path: Path) -> None:
    database = store(tmp_path)
    resource = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )
    database.save_artifact(
        resource_id=resource.id,
        kind="study",
        status=STATUS_OK,
        markdown="Saved study",
        model_name="gpt-4o-mini",
    )

    found = database.find_success(
        url=URL,
        extracted_text=PAGE,
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )

    assert found is not None
    assert found.resource.id == resource.id
    assert found.artifacts[0].markdown == "Saved study"


def test_changed_text_is_not_found(tmp_path: Path) -> None:
    database = store(tmp_path)
    database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )

    found = database.find_success(
        url=URL,
        extracted_text=PAGE + " A new paragraph was added.",
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )

    assert found is None


def test_failed_fetch_is_not_offered_as_a_success(tmp_path: Path) -> None:
    database = store(tmp_path)
    database.save_resource(
        url=URL,
        title="",
        status=STATUS_ERROR,
        error_message="The page could not be downloaded.",
        extracted_text="",
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )

    found = database.find_success(
        url=URL,
        extracted_text="",
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )

    assert found is None


def test_unknown_section_and_score_are_rejected(tmp_path: Path) -> None:
    database = store(tmp_path)
    resource = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
    )

    with pytest.raises(StorageError):
        database.save_artifact(
            resource_id=resource.id,
            kind="quiz",
            status=STATUS_OK,
            markdown="Not a section",
        )
    with pytest.raises(StorageError):
        database.save_attempt(
            resource_id=resource.id,
            question="Question",
            learner_answer="Answer",
            score="maybe",
            hint="",
        )


def test_delete_removes_one_pack_and_leaves_the_other(tmp_path: Path) -> None:
    database = store(tmp_path)
    first = database.save_resource(
        url=URL,
        title="Conditional Access",
        status=STATUS_OK,
        extracted_text=PAGE,
        level="beginner",
        goal="Explain Conditional Access",
        minutes=25,
    )
    database.save_artifact(
        resource_id=first.id,
        kind="study",
        status=STATUS_OK,
        markdown="First study",
    )
    database.replace_lesson_checks(first.id, [("First question", "First answer", "First excerpt")])
    database.save_attempt(
        resource_id=first.id,
        question="First question",
        learner_answer="A reply",
        score="partial",
        hint="Look again",
    )
    second = database.save_resource(
        url="https://learn.microsoft.com/en-us/purview/retention",
        title="Retention",
        status=STATUS_OK,
        extracted_text=PAGE + " retention",
        level="beginner",
        goal="Explain retention",
        minutes=20,
    )
    database.save_artifact(
        resource_id=second.id,
        kind="study",
        status=STATUS_OK,
        markdown="Second study",
    )
    database.replace_lesson_checks(
        second.id,
        [("Second question", "Second answer", "Second excerpt")],
    )
    database.save_attempt(
        resource_id=second.id,
        question="Second question",
        learner_answer="Another reply",
        score="correct",
        hint="That matches",
    )

    database.delete_resource(first.id)

    with pytest.raises(StorageError):
        database.get_resource(first.id)
    with pytest.raises(StorageError):
        database.delete_resource(first.id)
    assert database.get_resource(second.id).title == "Retention"
    assert database.list_artifacts(second.id)[0].markdown == "Second study"
    assert database.list_lesson_checks(second.id)[0].answer == "Second answer"
    assert database.list_attempts(second.id)[0].learner_answer == "Another reply"


def test_default_database_path_is_inside_the_project() -> None:
    from studymaster.config import get_settings

    path = get_settings().database_path
    assert path.name == "studymaster.db"
    assert path.parent.name == "data"
