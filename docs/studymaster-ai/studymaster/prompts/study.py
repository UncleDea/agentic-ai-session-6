"""Prompt text for the study agent."""

from studymaster.agents.request import StudyRequest

_RULE = (
    "Use only this source. If the source does not cover something, say that "
    "the source does not cover it. Do not add facts from outside the source."
)


def study_instructions() -> str:
    """Return the standing instruction for the study agent."""
    return (
        f"{_RULE} Return JSON with keys objectives, objectives_quote, "
        "explanation, explanation_quote, glossary, misconceptions, recap, "
        "and recap_quote. glossary is a list of objects with term, "
        "plain_definition, and quote. misconceptions is a list of objects "
        "with wrong, right, and quote. Every quote must be copied from the source."
    )


def study_prompt(request: StudyRequest, outline: str) -> str:
    """Return the study prompt, including the outline and the source text."""
    headings = "\n".join(f"- {heading}" for heading in request.headings) or "- none"
    return (
        f"Title: {request.title}\n"
        f"URL: {request.url}\n"
        f"Learner level: {request.level}\n"
        f"Learner goal: {request.goal}\n"
        f"Minutes: {request.minutes}\n"
        f"Headings:\n{headings}\n\n"
        f"Outline:\n{outline}\n\n"
        "Write study material with learning objectives, a plain-language "
        "explanation, a glossary, misconceptions, and a short recap. "
        "Use only this source.\n\n"
        f"Source:\n{request.source_text}"
    )
