"""Prompt text for the outline step."""

from studymaster.agents.request import StudyRequest

_RULE = (
    "Use only this source. If the source does not cover something, say that "
    "the source does not cover it. Do not add facts from outside the source."
)


def outline_instructions() -> str:
    """Return the standing instruction for the outline."""
    return _RULE


def outline_prompt(request: StudyRequest) -> str:
    """Return the outline prompt, including the source text."""
    headings = "\n".join(f"- {heading}" for heading in request.headings) or "- none"
    return (
        f"Title: {request.title}\n"
        f"URL: {request.url}\n"
        f"Learner level: {request.level}\n"
        f"Learner goal: {request.goal}\n"
        f"Minutes: {request.minutes}\n"
        f"Headings:\n{headings}\n\n"
        "Write a short outline of this page for the learner. "
        "Use only this source.\n\n"
        f"Source:\n{request.source_text}"
    )
