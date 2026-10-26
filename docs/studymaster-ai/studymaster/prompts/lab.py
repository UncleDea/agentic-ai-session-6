"""Prompt for the lab agent."""

from studymaster.agents.request import StudyRequest
from studymaster.prompts.common import SOURCE_RULE, request_context


def lab_instructions() -> str:
    """Return the standing instruction for a practical lab."""
    return (
        f"{SOURCE_RULE} Write a practical lab. Return JSON with has_procedure, "
        "note, and tasks. tasks is a list of objects with instruction, "
        "expected_result, and quote. If the source has no hands-on procedure, "
        "set has_procedure to false, set note to "
        "'This source does not describe a procedure.', and offer a concept "
        "exercise instead of invented tools or install commands."
    )


def lab_prompt(request: StudyRequest, outline: str) -> str:
    """Return the lab prompt."""
    return f"Write a practical lab from this page.\n\n{request_context(request, outline)}"
