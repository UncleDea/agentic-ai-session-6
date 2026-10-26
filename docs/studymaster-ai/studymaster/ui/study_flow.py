"""Turn one learner request into a study pack.

The page calls this when the learner presses the button. A second press
for the same unchanged page reads the saved pack and does not call the model.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from studymaster.agents.client import Completer, OpenAIModelClient
from studymaster.agents.coordinator import (
    SECTION_KINDS,
    AgentSection,
    HiddenCheck,
    run_study_pack,
)
from studymaster.agents.errors import AgentError, EmptySourceError
from studymaster.agents.quotes import COVER
from studymaster.agents.lab import write_lab
from studymaster.agents.lesson import write_lesson
from studymaster.agents.outline import write_outline
from studymaster.agents.project import write_project
from studymaster.agents.request import StudyRequest
from studymaster.agents.runbook import write_runbook
from studymaster.agents.study import write_study
from studymaster.config import Settings, get_settings
from studymaster.extraction.errors import ReaderError
from studymaster.extraction.fetch import Article, read_page
from studymaster.storage.database import (
    STATUS_ERROR,
    STATUS_OK,
    Resource,
    StudyStore,
    content_hash,
)

logger = logging.getLogger(__name__)

LEVELS = ("beginner", "intermediate", "advanced")
PASTED_TEXT_URL = "pasted-text"
UNREADABLE_TEXT = "This page did not include readable article text."
SHORTENED_NOTICE = "This page was shortened to 60,000 characters."
PageReader = Callable[..., Article]


@dataclass(frozen=True)
class StudyOutcome:
    """What the home page may show, plus answers that stay off the page."""

    ok: bool
    message: str
    title: str = ""
    outline: str = ""
    sections: tuple[AgentSection, ...] = ()
    hidden_answers: tuple[str, ...] = ()
    checks: tuple[HiddenCheck, ...] = ()
    resource_id: int = 0
    content_hash: str = ""
    from_saved: bool = False


def display_blocks(outcome: StudyOutcome) -> list[tuple[str, str]]:
    """Return the text the page is allowed to show.

    Lesson answers are not included.
    """
    if not outcome.ok:
        return [("error", outcome.message)]
    blocks: list[tuple[str, str]] = []
    if outcome.outline:
        blocks.append(("outline", outcome.outline))
    for section in outcome.sections:
        if section.status != STATUS_OK:
            blocks.append(("error", section.error_message))
        elif section.markdown:
            blocks.append((section.kind, section.markdown))
    return blocks


def pack_score_line(outcome: StudyOutcome) -> str:
    """Count sentences left out and questions that can still be graded."""
    left_out = 0
    for kind, text in display_blocks(outcome):
        if kind == "error":
            continue
        left_out += sum(1 for line in text.splitlines() if COVER in line)
    return f"Left out {left_out} sentences. Questions to check: {len(outcome.checks)}."


def study_page(
    *,
    url: str,
    level: str,
    goal: str,
    minutes: int,
    settings: Settings,
    store: StudyStore,
    read: PageReader = read_page,
    complete: Completer | None = None,
    remembered_answers: tuple[str, ...] = (),
    remembered_hash: str = "",
    article_text: str = "",
    on_progress: Callable[[str], None] | None = None,
) -> StudyOutcome:
    """Read one page, or the pasted lesson, and return its study pack."""
    cleaned_url = url.strip()
    cleaned_goal = goal.strip()
    cleaned_level = level.strip().lower()
    _report(on_progress, "Checking the link.")
    pasted = _collapse_lines(article_text)
    if pasted:
        problem = _learner_problem(cleaned_level, cleaned_goal, minutes)
        if problem:
            return StudyOutcome(ok=False, message=problem)
        if len(pasted) < settings.min_source_chars:
            return StudyOutcome(ok=False, message=UNREADABLE_TEXT)
        _report(on_progress, "Using the pasted lesson.")
        shortened = len(pasted) > settings.max_source_chars
        text = pasted[: settings.max_source_chars] if shortened else pasted
        article = Article(
            url=PASTED_TEXT_URL,
            title=_pasted_title(text),
            headings=[],
            text=text,
            shortened=shortened,
        )
        source_url = PASTED_TEXT_URL
    else:
        problem = _request_problem(cleaned_url, cleaned_level, cleaned_goal, minutes)
        if problem:
            return StudyOutcome(ok=False, message=problem)
        _report(on_progress, "Reading the page.")
        try:
            article = read(cleaned_url, settings=settings)
        except ReaderError as exc:
            store.save_resource(
                url=cleaned_url,
                title="",
                status=STATUS_ERROR,
                error_message=str(exc),
                level=cleaned_level,
                goal=cleaned_goal,
                minutes=minutes,
            )
            return StudyOutcome(ok=False, message=str(exc))
        source_url = cleaned_url

    digest = content_hash(article.text)
    saved = store.find_success(
        url=source_url,
        extracted_text=article.text,
        level=cleaned_level,
        goal=cleaned_goal,
        minutes=minutes,
    )
    if saved is not None:
        _report(on_progress, "Opening the saved pack.")
        stored = tuple(
            HiddenCheck(row.question, row.answer, row.excerpt)
            for row in store.list_lesson_checks(saved.resource.id)
        )
        if stored:
            answers = tuple(item.answer for item in stored)
        elif remembered_hash == digest:
            answers = remembered_answers
        else:
            answers = ()
        sections = tuple(
            AgentSection(
                artifact.kind,
                artifact.status,
                artifact.error_message,
                artifact.markdown,
                [],
            )
            for artifact in saved.artifacts
        )
        return StudyOutcome(
            ok=True,
            message="",
            title=saved.resource.title,
            sections=sections,
            hidden_answers=answers,
            checks=stored,
            resource_id=saved.resource.id,
            content_hash=digest,
            from_saved=True,
        )

    request = StudyRequest(
        title=article.title,
        url=source_url,
        headings=list(article.headings),
        source_text=article.text,
        level=cleaned_level,
        goal=cleaned_goal,
        minutes=minutes,
    )
    try:
        pack = run_study_pack(
            request,
            complete=complete,
            settings=settings,
            on_progress=on_progress,
        )
    except AgentError as exc:
        store.save_resource(
            url=source_url,
            title=article.title,
            status=STATUS_ERROR,
            error_message=str(exc),
            extracted_text=article.text,
            level=cleaned_level,
            goal=cleaned_goal,
            minutes=minutes,
        )
        return StudyOutcome(
            ok=False,
            message=str(exc),
            title=article.title,
            content_hash=digest,
        )

    resource = store.save_resource(
        url=source_url,
        title=article.title,
        status=STATUS_OK,
        extracted_text=article.text,
        level=cleaned_level,
        goal=cleaned_goal,
        minutes=minutes,
    )
    shown = tuple(
        _with_outline(section, pack.outline, shortened=article.shortened)
        for section in pack.sections
    )
    for section in shown:
        store.save_artifact(
            resource_id=resource.id,
            kind=section.kind,
            status=section.status,
            error_message=section.error_message,
            markdown=section.markdown,
            model_name=settings.openai_model,
        )
    lesson = next((section for section in shown if section.kind == "lesson"), None)
    if lesson is not None and lesson.hidden_checks:
        store.replace_lesson_checks(
            resource.id,
            [
                (item.question, item.answer, item.excerpt)
                for item in lesson.hidden_checks
            ],
        )
    answers = next(
        (section.hidden_answers for section in pack.sections if section.kind == "lesson"),
        (),
    )
    checks = lesson.hidden_checks if lesson is not None else ()
    outcome = StudyOutcome(
        ok=True,
        message="",
        title=article.title,
        sections=shown,
        hidden_answers=answers,
        checks=checks,
        resource_id=resource.id,
        content_hash=digest,
    )
    logger.info("%s", pack_score_line(outcome))
    return outcome


def _request_problem(url: str, level: str, goal: str, minutes: int) -> str:
    if not url:
        return "Paste a public page link."
    return _learner_problem(level, goal, minutes)


def _learner_problem(level: str, goal: str, minutes: int) -> str:
    if level not in LEVELS:
        return "Choose beginner, intermediate, or advanced."
    if not goal:
        return "Say what you want to be able to do."
    if minutes < 1:
        return "Enter at least 1 minute."
    return ""


def _report(on_progress: Callable[[str], None] | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)


def _collapse_lines(text: str) -> str:
    """Join extra spaces and drop blank lines."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _pasted_title(text: str) -> str:
    """Use the first line, cut at 80 characters."""
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    if not first:
        return "Pasted article"
    return first[:80]


def _with_outline(
    section: AgentSection,
    outline: str,
    *,
    shortened: bool = False,
) -> AgentSection:
    """Keep the shared outline in the study section so a saved pack still shows it."""
    if section.kind != "study" or not outline.strip():
        return section
    notice = f"{SHORTENED_NOTICE}\n\n" if shortened else ""
    markdown = f"{notice}## Outline\n\n{outline.strip()}\n\n{section.markdown}"
    return AgentSection(
        section.kind,
        section.status,
        section.error_message,
        markdown,
        section.checks,
        section.hidden_answers,
        section.hidden_checks,
    )


def saved_studies(store: StudyStore) -> list[Resource]:
    """Return successful saved packs, newest first."""
    return [resource for resource in store.list_resources() if resource.status == STATUS_OK]


def matching_studies(studies: list[Resource], query: str) -> list[Resource]:
    """Keep studies whose title or goal contains the typed words.

    An empty box keeps the whole list. Capital letters and extra spaces are ignored.
    """
    needle = " ".join(query.casefold().split())
    if not needle:
        return list(studies)
    matched: list[Resource] = []
    for resource in studies:
        title = " ".join((resource.title or resource.url).casefold().split())
        goal = " ".join(resource.goal.casefold().split())
        if needle in title or needle in goal:
            matched.append(resource)
    return matched


_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def saved_day(fetched_at: str) -> str:
    """Return the saved day on this computer, such as Saved October 25, 2026."""
    try:
        parsed = datetime.fromisoformat(fetched_at)
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    local = parsed.astimezone()
    return f"Saved {_MONTHS[local.month - 1]} {local.day}, {local.year}"


def open_saved(store: StudyStore, resource_id: int) -> StudyOutcome:
    """Load one saved pack. This does not fetch the page or call the model."""
    resource = store.get_resource(resource_id)
    if resource.status != STATUS_OK:
        return StudyOutcome(
            ok=False,
            message=resource.error_message or "This page was not saved.",
            title=resource.title,
            resource_id=resource.id,
            content_hash=resource.content_hash,
        )
    stored = tuple(
        HiddenCheck(row.question, row.answer, row.excerpt)
        for row in store.list_lesson_checks(resource.id)
    )
    sections = tuple(
        AgentSection(
            artifact.kind,
            artifact.status,
            artifact.error_message,
            artifact.markdown,
            [],
        )
        for artifact in store.list_artifacts(resource.id)
    )
    return StudyOutcome(
        ok=True,
        message="",
        title=resource.title,
        sections=sections,
        hidden_answers=tuple(item.answer for item in stored),
        checks=stored,
        resource_id=resource.id,
        content_hash=resource.content_hash,
        from_saved=True,
    )


def pack_markdown(outcome: StudyOutcome) -> str:
    """Return the downloadable pack. Lesson answers are omitted."""
    lines = [f"# {outcome.title}".rstrip(), ""]
    for _kind, text in display_blocks(outcome):
        lines.extend([text, ""])
    return "\n".join(lines).strip() + "\n"


def markdown_filename(title: str) -> str:
    """Return a safe file name for a downloaded pack."""
    cleaned = "".join(character if character.isalnum() else "-" for character in title.lower())
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return f"{cleaned or 'study'}.md"


def regenerate_section(
    *,
    store: StudyStore,
    resource_id: int,
    kind: str,
    settings: Settings | None = None,
    complete: Completer | None = None,
) -> StudyOutcome:
    """Rewrite one saved section. The page is not downloaded again."""
    if kind not in SECTION_KINDS:
        raise EmptySourceError("That section cannot be rewritten.")
    resource = store.get_resource(resource_id)
    if resource.status != STATUS_OK or not resource.extracted_text.strip():
        raise EmptySourceError("There is no source text to study.")
    active_settings = settings or get_settings()
    caller = complete or OpenAIModelClient(active_settings).complete
    request = StudyRequest(
        title=resource.title,
        url=resource.url,
        headings=[],
        source_text=resource.extracted_text,
        level=resource.level,
        goal=resource.goal,
        minutes=resource.minutes,
    )
    outline = _saved_outline(store, resource_id)
    if kind != "study" and not outline:
        outline = write_outline(request, caller)
    try:
        section = _one_section(
            kind,
            request,
            outline,
            caller,
            shortened=_was_shortened(store, resource_id),
        )
    except AgentError as exc:
        store.save_artifact(
            resource_id=resource_id,
            kind=kind,
            status=STATUS_ERROR,
            error_message=str(exc),
            markdown="",
            model_name=active_settings.openai_model,
        )
        if kind == "lesson":
            store.replace_lesson_checks(resource_id, [])
        return open_saved(store, resource_id)
    store.save_artifact(
        resource_id=resource_id,
        kind=kind,
        status=STATUS_OK,
        markdown=section.markdown,
        model_name=active_settings.openai_model,
    )
    if kind == "lesson":
        store.replace_lesson_checks(
            resource_id,
            [(item.question, item.answer, item.excerpt) for item in section.hidden_checks],
        )
    return open_saved(store, resource_id)


def _saved_outline(store: StudyStore, resource_id: int) -> str:
    study = next(
        (artifact for artifact in store.list_artifacts(resource_id) if artifact.kind == "study"),
        None,
    )
    if study is None:
        return ""
    return _outline_text(study.markdown)


def _was_shortened(store: StudyStore, resource_id: int) -> bool:
    study = next(
        (artifact for artifact in store.list_artifacts(resource_id) if artifact.kind == "study"),
        None,
    )
    return study is not None and study.markdown.startswith(SHORTENED_NOTICE)


def _outline_text(markdown: str) -> str:
    if markdown.startswith(SHORTENED_NOTICE):
        markdown = markdown[len(SHORTENED_NOTICE) :].lstrip("\n")
    marker = "## Outline\n\n"
    if not markdown.startswith(marker):
        return ""
    rest = markdown[len(marker) :]
    if "\n\n## " in rest:
        return rest.split("\n\n## ", 1)[0].strip()
    return rest.strip()


def _one_section(
    kind: str,
    request: StudyRequest,
    outline: str,
    complete: Completer,
    *,
    shortened: bool = False,
) -> AgentSection:
    if kind == "study":
        result = write_study(request, complete=complete, outline=outline or None)
        return _with_outline(
            AgentSection("study", STATUS_OK, "", result.markdown, list(result.checks)),
            result.outline,
            shortened=shortened,
        )
    if kind == "lesson":
        result = write_lesson(request, outline, complete)
        hidden = tuple(
            HiddenCheck(section.check_question, section.answer, section.quote)
            for section in result.sections
            if section.check_question.strip()
        )
        return AgentSection(
            "lesson",
            STATUS_OK,
            "",
            result.markdown,
            list(result.checks),
            tuple(item.answer for item in hidden),
            hidden,
        )
    if kind == "lab":
        result = write_lab(request, outline, complete)
    elif kind == "project":
        result = write_project(request, outline, complete)
    else:
        result = write_runbook(request, outline, complete)
    return AgentSection(kind, STATUS_OK, "", result.markdown, list(result.checks))
