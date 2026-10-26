"""The package of page text and learner details sent to every agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StudyRequest:
    """What an agent is allowed to use for one study run."""

    title: str
    url: str
    headings: list[str]
    source_text: str
    level: str
    goal: str
    minutes: int
