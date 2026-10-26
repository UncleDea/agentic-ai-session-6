"""Prompt for the project agent."""

from studymaster.agents.request import StudyRequest
from studymaster.prompts.common import SOURCE_RULE, request_context


def project_instructions() -> str:
    """Return the standing instruction for a professional project."""
    return (
        f"{SOURCE_RULE} Write a small professional project. Return JSON with "
        "goal, deliverable, milestones, done_when, and quote. milestones is a "
        "list of strings. Copy quote from the source."
    )


def project_prompt(request: StudyRequest, outline: str) -> str:
    """Return the project prompt."""
    return (
        "Write a project brief with a goal, a deliverable, milestones, and "
        "what done means.\n\n"
        f"{request_context(request, outline)}"
    )
