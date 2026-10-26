"""Tests for the specialist agents and the coordinator.

The model client is fake. These tests do not call OpenAI.
"""

import json

import pytest

from studymaster.agents.client import OpenAIModelClient
from studymaster.agents.coordinator import (
    SECTION_KINDS,
    pack_size_line,
    run_study_pack,
    sections_for_minutes,
)
from studymaster.agents.errors import EmptySourceError, MissingApiKeyError
from studymaster.agents.lab import NO_PROCEDURE, write_lab
from studymaster.agents.lesson import write_lesson
from studymaster.agents.request import StudyRequest
from studymaster.agents.runbook import write_runbook
from studymaster.config import Settings
from studymaster.prompts.lab import lab_instructions, lab_prompt
from studymaster.prompts.lesson import lesson_instructions, lesson_prompt
from studymaster.prompts.project import project_instructions, project_prompt
from studymaster.prompts.runbook import runbook_instructions, runbook_prompt

SOURCE = "Plants make food from sunlight, water, and carbon dioxide."
GOOD_QUOTE = "Plants make food from sunlight"
BAD_QUOTE = "Plants eat sunlight with their roots"
HIDDEN_ANSWER = "They use sunlight, water, and carbon dioxide."
OUTLINE = "1. How plants make food"


def settings() -> Settings:
    from pathlib import Path

    return Settings(
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        fetch_timeout_seconds=10,
        max_response_bytes=1_000_000,
        max_source_chars=20_000,
        min_source_chars=400,
        database_path=Path("data/studymaster.db"),
        openai_timeout_seconds=60,
        openai_temperature=0.2,
    )


def request(source: str = SOURCE) -> StudyRequest:
    return StudyRequest(
        title="Photosynthesis",
        url="https://example.com/plants",
        headings=["How plants make food"],
        source_text=source,
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
    )


class RoutingModel:
    """Chooses a reply from the instruction text and records every prompt."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = replies
        self.prompts: list[str] = []

    def complete(self, *, instructions: str, prompt: str) -> str:
        self.prompts.append(prompt)
        if "Write a short outline" in prompt:
            return self.replies["outline"]
        for name in ("guided lesson", "practical lab", "professional project", "execution runbook"):
            if name in instructions:
                return self.replies[name]
        return self.replies["study"]


def _study_json() -> str:
    return json.dumps(
        {
            "objectives": "Explain how plants make food.",
            "objectives_quote": GOOD_QUOTE,
            "explanation": "Leaves use sunlight, water, and carbon dioxide.",
            "explanation_quote": GOOD_QUOTE,
            "glossary": [
                {
                    "term": "photosynthesis",
                    "plain_definition": "The way plants make food.",
                    "quote": GOOD_QUOTE,
                }
            ],
            "misconceptions": [
                {
                    "wrong": "Plants eat soil.",
                    "right": "Plants make food from sunlight, water, and carbon dioxide.",
                    "quote": GOOD_QUOTE,
                }
            ],
            "recap": "Plants make their own food.",
            "recap_quote": GOOD_QUOTE,
        }
    )


def _lesson_json(quote: str = GOOD_QUOTE) -> str:
    return json.dumps(
        {
            "sections": [
                {
                    "title": "How plants make food",
                    "teach": "Plants make food from sunlight, water, and carbon dioxide.",
                    "example": "A leaf in sunlight makes food.",
                    "check_question": "What do plants use to make food?",
                    "answer": HIDDEN_ANSWER,
                    "quote": quote,
                }
            ]
        }
    )


def _lab_json(*, has_procedure: bool) -> str:
    return json.dumps(
        {
            "has_procedure": has_procedure,
            "note": "" if has_procedure else NO_PROCEDURE,
            "tasks": [
                {
                    "instruction": "Name the three ingredients plants use.",
                    "expected_result": "Sunlight, water, and carbon dioxide.",
                    "quote": GOOD_QUOTE,
                }
            ],
        }
    )


def _project_json() -> str:
    return json.dumps(
        {
            "goal": "Explain how a plant makes food.",
            "deliverable": "A short explanation.",
            "milestones": ["Read the page", "Write the explanation"],
            "done_when": "The explanation uses only the page.",
            "quote": GOOD_QUOTE,
        }
    )


def _runbook_json(*, has_procedure: bool) -> str:
    return json.dumps(
        {
            "has_procedure": has_procedure,
            "note": "" if has_procedure else NO_PROCEDURE,
            "steps": [
                {
                    "action": "Read how plants make food.",
                    "check": "The three ingredients are named.",
                    "if_it_fails": "Read the sentence again.",
                    "quote": GOOD_QUOTE,
                }
            ],
        }
    )


def _replies(
    *,
    lesson: str | None = None,
    lab_procedure: bool = True,
    runbook_procedure: bool = True,
) -> dict[str, str]:
    return {
        "outline": OUTLINE,
        "study": _study_json(),
        "guided lesson": lesson if lesson is not None else _lesson_json(),
        "practical lab": _lab_json(has_procedure=lab_procedure),
        "professional project": _project_json(),
        "execution runbook": _runbook_json(has_procedure=runbook_procedure),
    }


def test_every_prompt_contains_the_source_and_the_rule():
    page = request()
    prompts = [
        lesson_prompt(page, OUTLINE),
        lab_prompt(page, OUTLINE),
        project_prompt(page, OUTLINE),
        runbook_prompt(page, OUTLINE),
    ]
    instructions = [
        lesson_instructions(),
        lab_instructions(),
        project_instructions(),
        runbook_instructions(),
    ]
    for prompt in prompts:
        assert SOURCE in prompt
        assert "use only this source" in prompt.casefold()
        assert OUTLINE in prompt
        assert "beginner" in prompt
        assert "Explain photosynthesis" in prompt
    for instruction in instructions:
        assert "use only this source" in instruction.casefold()


def test_empty_source_never_calls_the_model():
    model = RoutingModel(_replies())
    with pytest.raises(EmptySourceError):
        run_study_pack(request("   "), complete=model.complete)
    assert model.prompts == []


def test_missing_api_key_stops_before_openai(monkeypatch: pytest.MonkeyPatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OpenAI was constructed")

    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_if_called)
    with pytest.raises(MissingApiKeyError):
        OpenAIModelClient(settings())
    with pytest.raises(MissingApiKeyError):
        run_study_pack(request(), settings=settings())


def test_coordinator_returns_five_sections_from_one_outline():
    model = RoutingModel(_replies())
    pack = run_study_pack(request(), complete=model.complete)
    assert pack.outline == OUTLINE
    assert [section.kind for section in pack.sections] == list(SECTION_KINDS)
    assert all(section.status == "ok" for section in pack.sections)
    agent_prompts = [
        prompt
        for prompt in model.prompts
        if "Write a short outline" not in prompt and "Repair these sentences" not in prompt
    ]
    assert len(agent_prompts) == 5
    assert all(OUTLINE in prompt for prompt in agent_prompts)
    assert sum("Write a short outline" in prompt for prompt in model.prompts) == 1


def test_up_to_ten_minutes_keeps_the_outline_study_and_lesson():
    from dataclasses import replace

    model = RoutingModel(_replies())
    pack = run_study_pack(replace(request(), minutes=5), complete=model.complete)
    assert [section.kind for section in pack.sections] == ["study", "lesson"]
    assert pack.outline == OUTLINE
    assert sections_for_minutes(10) == ("study", "lesson")
    agent_prompts = [
        prompt
        for prompt in model.prompts
        if "Write a short outline" not in prompt and "Repair these sentences" not in prompt
    ]
    assert len(agent_prompts) == 2


def test_more_than_ten_minutes_keeps_the_full_pack():
    from dataclasses import replace

    model = RoutingModel(_replies())
    pack = run_study_pack(replace(request(), minutes=15), complete=model.complete)
    assert [section.kind for section in pack.sections] == list(SECTION_KINDS)
    assert sections_for_minutes(11) == SECTION_KINDS
    assert "lab, project, and runbook" in pack_size_line()


def test_one_failed_agent_keeps_the_other_sections():
    model = RoutingModel(_replies(lesson="this is not json"))
    pack = run_study_pack(request(), complete=model.complete)
    by_kind = {section.kind: section for section in pack.sections}
    assert by_kind["lesson"].status == "error"
    assert by_kind["lesson"].error_message
    assert by_kind["lesson"].markdown == ""
    for kind in ("study", "lab", "project", "runbook"):
        assert by_kind[kind].status == "ok"
        assert by_kind[kind].markdown


def test_lesson_hides_the_answer_and_checks_the_quote():
    def complete(*, instructions: str, prompt: str) -> str:
        return _lesson_json(BAD_QUOTE)

    lesson = write_lesson(request(), OUTLINE, complete)
    assert lesson.sections[0].answer == HIDDEN_ANSWER
    assert HIDDEN_ANSWER not in lesson.markdown
    assert lesson.sections[0].check_question == ""
    assert "What do plants use to make food?" not in lesson.markdown
    assert "The source does not cover this." in lesson.markdown
    assert lesson.sections[0].grounded is False


def test_lab_says_when_the_page_has_no_procedure():
    def complete(*, instructions: str, prompt: str) -> str:
        return _lab_json(has_procedure=False)

    lab = write_lab(request(), OUTLINE, complete)
    assert lab.has_procedure is False
    assert NO_PROCEDURE in lab.markdown
    assert "install" not in lab.markdown.casefold()


def test_runbook_says_when_the_page_has_no_procedure():
    def complete(*, instructions: str, prompt: str) -> str:
        return _runbook_json(has_procedure=False)

    runbook = write_runbook(request(), OUTLINE, complete)
    assert runbook.has_procedure is False
    assert NO_PROCEDURE in runbook.markdown
    assert "If it fails:" in runbook.markdown


def test_a_hidden_answer_that_fails_is_not_graded():
    def complete(*, instructions: str, prompt: str) -> str:
        if "Repair these sentences" in instructions:
            return '{"replacements": []}'
        return json.dumps(
            {
                "sections": [
                    {
                        "title": "How plants make food",
                        "teach": "Plants make food from sunlight.",
                        "example": "Plants make food from sunlight.",
                        "check_question": "What do plants use to make food?",
                        "answer": "Plants grow underground in the dark.",
                        "quote": GOOD_QUOTE,
                    }
                ]
            }
        )

    lesson = write_lesson(request(), OUTLINE, complete)
    assert lesson.sections[0].answer == "Plants grow underground in the dark."
    assert lesson.sections[0].check_question == ""
    assert "What do plants use to make food?" not in lesson.markdown
    assert "underground" not in lesson.markdown


def test_a_repaired_hidden_answer_can_be_graded():
    def complete(*, instructions: str, prompt: str) -> str:
        if "Repair these sentences" in instructions:
            return json.dumps(
                {
                    "replacements": [
                        {"id": "0-answer", "text": "Plants make food from sunlight."}
                    ]
                }
            )
        return json.dumps(
            {
                "sections": [
                    {
                        "title": "How plants make food",
                        "teach": "Plants make food from sunlight.",
                        "example": "Plants make food from sunlight.",
                        "check_question": "What do plants use to make food?",
                        "answer": "Plants grow underground in the dark.",
                        "quote": GOOD_QUOTE,
                    }
                ]
            }
        )

    lesson = write_lesson(request(), OUTLINE, complete)
    assert lesson.sections[0].check_question == "What do plants use to make food?"
    assert lesson.sections[0].answer == "Plants make food from sunlight."
    assert "Check question: What do plants use to make food?" in lesson.markdown
    assert "underground" not in lesson.markdown


def test_an_empty_lesson_is_requested_once():
    prompts: list[str] = []

    def complete(*, instructions: str, prompt: str) -> str:
        prompts.append(prompt)
        if "Repair these sentences" in instructions:
            return '{"replacements": []}'
        if "at least one section" in prompt:
            return _lesson_json()
        return '{"sections": []}'

    lesson = write_lesson(request(), OUTLINE, complete)
    assert [prompt for prompt in prompts if "Write a guided lesson" in prompt].__len__() == 2
    assert "at least one section" in prompts[1]
    assert "How plants make food" in lesson.markdown
    assert "The source does not cover a lesson." not in lesson.markdown


def test_a_second_empty_lesson_stays_empty():
    prompts: list[str] = []

    def complete(*, instructions: str, prompt: str) -> str:
        prompts.append(prompt)
        return '{"sections": []}'

    lesson = write_lesson(request(), OUTLINE, complete)
    assert lesson.sections == []
    assert lesson.markdown == "## Lesson\nThe source does not cover a lesson."
    assert len(prompts) == 2
    assert "at least one section" in prompts[1]


def test_a_lesson_with_sections_is_not_requested_again():
    prompts: list[str] = []

    def complete(*, instructions: str, prompt: str) -> str:
        prompts.append(prompt)
        if "Repair these sentences" in instructions:
            return '{"replacements": []}'
        return _lesson_json()

    write_lesson(request(), OUTLINE, complete)
    lesson_prompts = [prompt for prompt in prompts if "Write a guided lesson" in prompt]
    assert len(lesson_prompts) == 1
