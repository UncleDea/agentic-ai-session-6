"""Ask for one outline made only from the page."""

from studymaster.agents.client import Completer
from studymaster.agents.errors import EmptySourceError
from studymaster.agents.request import StudyRequest
from studymaster.prompts.outline import outline_instructions, outline_prompt


def write_outline(request: StudyRequest, complete: Completer) -> str:
    """Return a short outline. An empty source never calls the model."""
    if not request.source_text.strip():
        raise EmptySourceError("There is no source text to study.")
    return complete(
        instructions=outline_instructions(),
        prompt=outline_prompt(request),
    ).strip()
