"""Shared page details included in every agent prompt."""

from studymaster.agents.request import StudyRequest

SOURCE_RULE = (
    "Use only this source. If the source does not cover something, say that "
    "the source does not cover it. Do not add facts from outside the source."
)


def request_context(request: StudyRequest, outline: str) -> str:
    """Return the learner details, outline, and source text."""
    headings = "\n".join(f"- {heading}" for heading in request.headings) or "- none"
    return (
        f"Title: {request.title}\n"
        f"URL: {request.url}\n"
        f"Learner level: {request.level}\n"
        f"Learner goal: {request.goal}\n"
        f"Minutes: {request.minutes}\n"
        f"Headings:\n{headings}\n\n"
        f"Outline:\n{outline}\n\n"
        f"Use only this source.\n\n"
        f"Source:\n{request.source_text}"
    )
