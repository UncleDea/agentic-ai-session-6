"""Prompt for the lesson agent."""

from studymaster.agents.request import StudyRequest
from studymaster.prompts.common import SOURCE_RULE, request_context

EMPTY_LESSON_LINE = "The lesson must include at least one section from the page."


def lesson_instructions() -> str:
    """Return the standing instruction for a guided lesson."""
    return (
        f"{SOURCE_RULE} Write a guided lesson. Return JSON with key sections, "
        "a list of objects with title, teach, example, check_question, answer, "
        "and quote. Copy every quote from the source."
    )


def lesson_prompt(request: StudyRequest, outline: str) -> str:
    """Return the lesson prompt."""
    return (
        "Write a guided lesson in source order. Each section needs one worked "
        "example and one check question. The answer is stored separately so "
        "the page can hide it.\n\n"
        f"{request_context(request, outline)}"
    )
