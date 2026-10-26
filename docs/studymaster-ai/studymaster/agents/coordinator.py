"""Run the study agent and the four specialist agents from one outline."""

from collections.abc import Callable
from dataclasses import dataclass

from studymaster.agents.client import Completer, OpenAIModelClient
from studymaster.agents.errors import AgentError, EmptySourceError
from studymaster.agents.lab import write_lab
from studymaster.agents.lesson import write_lesson
from studymaster.agents.outline import write_outline
from studymaster.agents.project import write_project
from studymaster.agents.quotes import CheckedQuote
from studymaster.agents.request import StudyRequest
from studymaster.agents.runbook import write_runbook
from studymaster.agents.study import write_study
from studymaster.config import Settings, get_settings

SECTION_KINDS = ("study", "lesson", "lab", "project", "runbook")
SHORT_STUDY_MINUTES = 10
_STEP_LABELS = {
    "study": "Writing the study.",
    "lesson": "Writing the lesson.",
    "lab": "Writing the lab.",
    "project": "Writing the project.",
    "runbook": "Writing the runbook.",
}
Progress = Callable[[str], None]
Preview = Callable[[str, str], None]


@dataclass(frozen=True)
class HiddenCheck:
    """A lesson question stored for grading. The page does not show the answer."""

    question: str
    answer: str
    excerpt: str


@dataclass(frozen=True)
class AgentSection:
    """One agent's result. A failure keeps an error message and empty text."""

    kind: str
    status: str
    error_message: str
    markdown: str
    checks: list[CheckedQuote]
    hidden_answers: tuple[str, ...] = ()
    hidden_checks: tuple[HiddenCheck, ...] = ()


@dataclass(frozen=True)
class StudyPack:
    """The shared outline and every section the coordinator collected."""

    outline: str
    sections: list[AgentSection]


def sections_for_minutes(minutes: int) -> tuple[str, ...]:
    """Return the sections a new pack writes for this many minutes.

    The outline is always written first. Up to 10 minutes, the pack keeps
    the study and the lesson. More than 10 minutes also keeps the lab,
    project, and runbook.
    """
    if minutes <= SHORT_STUDY_MINUTES:
        return ("study", "lesson")
    return SECTION_KINDS


def pack_size_line() -> str:
    """Return the minutes rule shown under the Minutes box."""
    return (
        "Up to 10 minutes keeps the outline, study, and lesson. "
        "More than 10 minutes also keeps the lab, project, and runbook."
    )


def run_study_pack(
    request: StudyRequest,
    *,
    complete: Completer | None = None,
    settings: Settings | None = None,
    on_progress: Progress | None = None,
    on_preview: Preview | None = None,
) -> StudyPack:
    """Run the outline and the sections that fit the minutes.

    An empty source never calls the model.
    """
    if not request.source_text.strip():
        raise EmptySourceError("There is no source text to study.")
    caller = complete or OpenAIModelClient(settings or get_settings()).complete
    _report(on_progress, "Writing the outline.")
    outline = write_outline(request, caller)
    _preview(on_preview, "outline", outline)
    runners = (
        ("study", lambda: write_study(request, complete=caller, outline=outline)),
        ("lesson", lambda: write_lesson(request, outline, caller)),
        ("lab", lambda: write_lab(request, outline, caller)),
        ("project", lambda: write_project(request, outline, caller)),
        ("runbook", lambda: write_runbook(request, outline, caller)),
    )
    wanted = sections_for_minutes(request.minutes)
    sections = []
    for kind, runner in runners:
        if kind not in wanted:
            continue
        _report(on_progress, _STEP_LABELS[kind])
        try:
            result = runner()
        except AgentError as exc:
            sections.append(AgentSection(kind, "error", str(exc), "", []))
            _preview(on_preview, kind, str(exc))
            continue
        answers = ()
        hidden_checks: tuple[HiddenCheck, ...] = ()
        if kind == "lesson":
            hidden_checks = tuple(
                HiddenCheck(
                    section.check_question,
                    section.answer,
                    section.quote,
                )
                for section in result.sections
                if section.check_question.strip()
            )
            answers = tuple(item.answer for item in hidden_checks)
        sections.append(
            AgentSection(
                kind,
                "ok",
                "",
                result.markdown,
                list(result.checks),
                answers,
                hidden_checks,
            )
        )
        _preview(on_preview, kind, result.markdown)
    return StudyPack(outline=outline, sections=sections)


def _report(on_progress: Progress | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)


def _preview(on_preview: Preview | None, kind: str, text: str) -> None:
    if on_preview is not None and text.strip():
        on_preview(kind, text)
