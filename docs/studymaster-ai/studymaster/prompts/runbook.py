"""Prompt for the runbook agent."""

from studymaster.agents.request import StudyRequest
from studymaster.prompts.common import SOURCE_RULE, request_context


def runbook_instructions() -> str:
    """Return the standing instruction for an execution runbook."""
    return (
        f"{SOURCE_RULE} Write an execution runbook. Return JSON with "
        "has_procedure, note, and steps. steps is a list of objects with "
        "action, check, if_it_fails, and quote. If the source has no "
        "operational procedure, set has_procedure to false, set note to "
        "'This source does not describe a procedure.', and do not invent "
        "commands."
    )


def runbook_prompt(request: StudyRequest, outline: str) -> str:
    """Return the runbook prompt."""
    return f"Write an execution runbook from this page.\n\n{request_context(request, outline)}"
