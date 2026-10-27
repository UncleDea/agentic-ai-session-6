"""The StudyMaster AI page.

The learner pastes one public link. The study pack is written only after
they press the button, and lesson answers stay off the page.
"""

import logging

import streamlit as st

from studymaster.agents.coordinator import SECTION_KINDS, pack_size_line
from studymaster.agents.errors import AgentError
from studymaster.agents.grader import SCORE_LABELS, record_attempt
from studymaster.config import Settings, get_settings
from studymaster.extraction.search import NO_PUBLIC_PAGE, USE_PAGE_HINT, find_public_page
from studymaster.logging_setup import configure_logging
from studymaster.sample_links import (
    NO_READING_GOAL,
    OWN_LINK,
    READING_GOAL_CAPTION,
    NO_PAGE_MATCH,
    SampleLink,
    article_by_label,
    article_links,
    choice_label,
    find_articles,
    goal_by_label,
    reading_goals,
)
from studymaster.storage.database import LOCAL_LEARNER_ID, StorageError, StudyStore
from studymaster.ui.study_flow import (
    PASTED_TEXT_URL,
    StudyOutcome,
    display_blocks,
    focus_waiting_question,
    markdown_filename,
    matching_studies,
    open_saved,
    outline_picture_html,
    pack_docx,
    pack_markdown,
    regenerate_section,
    pack_score_line,
    left_to_check,
    saved_check,
    saved_day,
    saved_level,
    saved_minutes,
    saved_pieces,
    saved_progress,
    saved_question,
    word_filename,
    reply_day,
    saved_studies,
    read_from_line,
    study_page,
    waiting_questions,
)

REWRITE_LABELS = {
    "study": "Rewrite study",
    "lesson": "Rewrite lesson",
    "lab": "Rewrite lab",
    "project": "Rewrite project",
    "runbook": "Rewrite runbook",
}
EMPTY_LESSON_MARKDOWN = "## Lesson\nThe source does not cover a lesson."
EMPTY_LESSON_NOTE = "The lesson came back empty."
EMPTY_LESSON_HINT = f"{EMPTY_LESSON_NOTE} Press Rewrite lesson to ask for it again."
EMPTY_RUNBOOK_NOTE = "This page has no procedure."
EMPTY_RUNBOOK_MARKDOWN = (
    "## Runbook\n"
    "This source does not describe a procedure.\n"
    "The source does not cover a runbook step."
)
OPEN_PACK_NOTE = (
    "This pack is already open. A new pack starts when the page, the level, "
    "the goal, or the minutes change."
)
UNCOVERED_PROJECT_SENTENCE = "The source does not cover this."
UNCOVERED_PROJECT_NOTE = "The project is not covered by this page."
LEVEL_LABELS = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}

logger = logging.getLogger(__name__)


def _signed_in(store: StudyStore, *, require_login: bool) -> bool:
    """Ask for the local login before the packs are shown.

    A database with no login yet keeps the local page open so the first
    login can be created. The public page hides every pack until a login
    matches. A wrong name or password also leaves the packs hidden.
    """
    signed_in = st.session_state.get("learner_id")
    if isinstance(signed_in, str) and signed_in:
        return True
    if not store.has_learner():
        _create_login(store)
        return not require_login
    st.subheader("Sign in")
    with st.form("sign-in"):
        name = st.text_input("Name")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        owner_id = store.authenticate(name=name, password=password)
        if owner_id is None:
            st.error("That name or password is not right.")
        else:
            st.session_state["learner_id"] = owner_id
            st.rerun()
    return False


def _create_login(store: StudyStore) -> None:
    """Save the first local login. The password is stored as a hash."""
    with st.form("create-login"):
        st.caption("Create a login for this computer. After it is saved, the packs stay hidden until the name and password match.")
        name = st.text_input("Name", key="create_name")
        password = st.text_input("Password", type="password", key="create_password")
        submitted = st.form_submit_button("Create a login")
    if not submitted:
        return
    try:
        store.create_learner(name=name, password=password)
    except StorageError as exc:
        st.error(str(exc))
        return
    owner_id = store.authenticate(name=name, password=password)
    if owner_id is not None:
        st.session_state["learner_id"] = owner_id
        st.rerun()


def main() -> None:
    """Draw the home page."""
    configure_logging()
    settings = get_settings()
    logger.info(
        "Home page loaded (OpenAI key present: %s, model: %s)",
        settings.openai_api_key is not None,
        settings.openai_model,
    )
    st.set_page_config(page_title="StudyMaster AI", layout="centered")
    _apply_style()
    _reset_screen()
    _apply_opened_pack()
    st.title("StudyMaster AI")
    store = StudyStore(settings.database_path)
    if not _signed_in(store, require_login=settings.require_login):
        return
    owner_id = str(st.session_state.get("learner_id") or LOCAL_LEARNER_ID)
    st.markdown(
        "Paste one public page. The study pack uses only the words on that page."
    )
    _show_finder()
    _show_catalog()

    with st.form("study-request"):
        url = st.text_input(
            "Page link",
            key="page_link",
            placeholder="https://learn.microsoft.com/...",
        )
        article_text = st.text_area(
            "Article text",
            key="article_text",
            placeholder="Paste the lesson words here",
            height=160,
        )
        st.caption("A filled box is the lesson, so the page link is not opened.")
        level = st.selectbox(
            "Level",
            ["Beginner", "Intermediate", "Advanced"],
            key="study_level",
        )
        goal = st.text_input(
            "Goal",
            key="study_goal",
            placeholder="What you want to be able to do",
        )
        minutes = int(
            st.number_input(
                "Minutes",
                min_value=1,
                max_value=240,
                value=20,
                step=5,
                key="study_minutes",
            )
        )
        st.caption(pack_size_line())
        submitted = st.form_submit_button("Study this page")
        open_pack = st.session_state.get("study_outcome")
        if isinstance(open_pack, StudyOutcome) and open_pack.ok:
            st.caption(OPEN_PACK_NOTE)

    if st.button("Start over"):
        st.session_state["_start_over"] = True
        st.rerun()

    if submitted:
        previous = st.session_state.get("study_outcome")
        remembered: tuple[str, ...] = ()
        remembered_hash = ""
        if isinstance(previous, StudyOutcome):
            remembered = previous.hidden_answers
            remembered_hash = previous.content_hash
        with st.status("Checking the link.", expanded=True) as status:
            preview = st.empty()
            finished: list[str] = []

            def report(message: str) -> None:
                status.update(label=message)

            def reveal(text: str) -> None:
                finished.append(text)
                preview.markdown("\n\n".join(finished))

            outcome = study_page(
                url=url,
                level=str(level),
                goal=goal,
                minutes=minutes,
                article_text=article_text,
                settings=settings,
                store=StudyStore(settings.database_path),
                remembered_answers=remembered,
                remembered_hash=remembered_hash,
                on_progress=report,
                on_preview=reveal,
                owner_id=owner_id,
            )
            if outcome.ok:
                status.update(label="Study pack ready.", state="complete")
            else:
                status.update(label=outcome.message, state="error")
            st.session_state["study_outcome"] = outcome

    outcome = st.session_state.get("study_outcome")
    if isinstance(outcome, StudyOutcome):
        _show(outcome, settings)
    _show_waiting(StudyStore(settings.database_path), owner_id=owner_id)
    _show_history(StudyStore(settings.database_path), owner_id=owner_id)


def _reset_screen() -> None:
    """Clear the open pack and the form before the boxes are drawn.

    Saved studies stay in the database. Find a study keeps its words.
    """
    if not st.session_state.pop("_start_over", False):
        return
    st.session_state["starter_article"] = OWN_LINK
    st.session_state["_applied_article"] = OWN_LINK
    st.session_state["reading_goal"] = NO_READING_GOAL
    st.session_state["_applied_goal"] = NO_READING_GOAL
    st.session_state["catalog_reference"] = ""
    st.session_state["page_link"] = ""
    st.session_state["article_text"] = ""
    st.session_state["study_goal"] = ""
    st.session_state["study_level"] = "Beginner"
    st.session_state["study_minutes"] = 20
    version = int(st.session_state.get("find_form_version", 0))
    st.session_state.pop(f"find_page_query_{version}", None)
    st.session_state["find_form_version"] = version + 1
    st.session_state.pop("finder_matches", None)
    st.session_state.pop("finder_message", None)
    st.session_state.pop("finder_web_page", None)
    st.session_state.pop("finder_web_note", None)
    st.session_state.pop("study_outcome", None)
    st.session_state.pop("_opened_pack_fields", None)


def _apply_opened_pack() -> None:
    """Copy a saved pack into the form before those boxes are drawn.

    A public page also fills Page link and leaves Article text empty.
    A pasted lesson fills Article text and leaves Page link as it is.
    The copy is queued by Open study on the previous run.
    """
    fields = st.session_state.pop("_opened_pack_fields", None)
    if not isinstance(fields, dict):
        return
    level = fields.get("level")
    if isinstance(level, str) and level in LEVEL_LABELS.values():
        st.session_state["study_level"] = level
    goal = fields.get("goal")
    if isinstance(goal, str):
        st.session_state["study_goal"] = goal
    minutes = fields.get("minutes")
    if isinstance(minutes, int) and 1 <= minutes <= 240:
        st.session_state["study_minutes"] = minutes
    page_link = fields.get("page_link")
    if isinstance(page_link, str) and read_from_line(page_link):
        st.session_state["page_link"] = page_link
    article_text = fields.get("article_text")
    if isinstance(article_text, str):
        st.session_state["article_text"] = article_text


def _queue_opened_pack(outcome: StudyOutcome, source_text: str = "") -> None:
    """Remember the saved form values for the next draw."""
    if not outcome.ok:
        return
    fields: dict[str, str | int] = {"goal": outcome.goal}
    label = LEVEL_LABELS.get(outcome.level.strip().lower())
    if label:
        fields["level"] = label
    if 1 <= outcome.minutes <= 240:
        fields["minutes"] = outcome.minutes
    page_link = outcome.source_url.strip()
    if page_link == PASTED_TEXT_URL:
        fields["article_text"] = source_text
    elif read_from_line(page_link):
        fields["page_link"] = page_link
        fields["article_text"] = ""
    st.session_state["_opened_pack_fields"] = fields


def _show_finder() -> None:
    """Fill the form from the starter list. This does not open a page or call the model."""
    version = int(st.session_state.get("find_form_version", 0))
    with st.form(f"find-page-{version}"):
        query = st.text_input(
            "What do you want to learn?",
            key=f"find_page_query_{version}",
            placeholder="data loss prevention",
        )
        submitted = st.form_submit_button("Find a page")
    if submitted:
        query = str(query)
        matches = find_articles(query)
        st.session_state.pop("finder_matches", None)
        st.session_state.pop("finder_web_page", None)
        st.session_state.pop("finder_web_note", None)
        if not query.strip():
            st.session_state["finder_message"] = "Type what you want to learn."
        elif len(matches) == 1:
            st.session_state.pop("finder_message", None)
            _choose_article(matches[0])
        elif matches:
            st.session_state.pop("finder_message", None)
            st.session_state["finder_matches"] = [choice_label(item) for item in matches]
        else:
            st.session_state["finder_message"] = NO_PAGE_MATCH
            with st.spinner("Looking for one public page."):
                page = find_public_page(query)
            if page:
                st.session_state["finder_web_page"] = page
            else:
                st.session_state["finder_web_note"] = NO_PUBLIC_PAGE
    labels = list(st.session_state.get("finder_matches") or [])
    if labels:
        st.caption("Several pages match. Pick one.")
        for index, label in enumerate(labels):
            if st.button(label, key=f"finder-match-{index}"):
                _choose_article(article_by_label(label))
                st.session_state.pop("finder_matches", None)
                st.session_state.pop("finder_message", None)
                st.session_state.pop("finder_web_page", None)
                st.session_state.pop("finder_web_note", None)
                st.rerun()
    elif st.session_state.get("finder_message"):
        st.caption(str(st.session_state["finder_message"]))
        _show_public_page()


def _show_public_page() -> None:
    """Show one safe address. Filling the link does not open the page."""
    page = st.session_state.get("finder_web_page")
    if page:
        st.caption(USE_PAGE_HINT)
        st.text(str(page))
        if st.button("Use this page"):
            st.session_state["page_link"] = str(page)
            st.session_state["starter_article"] = OWN_LINK
            st.session_state["_applied_article"] = OWN_LINK
            st.session_state.pop("finder_web_page", None)
            st.session_state.pop("finder_message", None)
            st.session_state.pop("finder_web_note", None)
            st.rerun()
        return
    note = st.session_state.get("finder_web_note")
    if note:
        st.caption(str(note))


def _choose_article(item: SampleLink) -> None:
    """Point the starter chooser at one article so the form fills before it is drawn."""
    st.session_state["starter_article"] = choice_label(item)
    st.session_state.pop("_applied_article", None)


def _show_catalog() -> None:
    """Fill the form from a catalog choice. The choice does not call the model."""
    articles = article_links()
    goals = reading_goals()
    st.selectbox(
        "Starter article",
        [OWN_LINK, *[choice_label(item) for item in articles]],
        key="starter_article",
    )
    _apply_article_choice()
    st.selectbox(
        "Reading goal",
        [NO_READING_GOAL, *[choice_label(item) for item in goals]],
        key="reading_goal",
    )
    _apply_goal_choice()
    if st.session_state.get("reading_goal") != NO_READING_GOAL:
        st.caption(READING_GOAL_CAPTION)
    reference = st.session_state.get("catalog_reference", "")
    if reference:
        st.text(reference)


def _apply_article_choice() -> None:
    """Copy a starter article into the page link and goal."""
    label = st.session_state["starter_article"]
    if label == st.session_state.get("_applied_article"):
        return
    st.session_state["_applied_article"] = label
    if label == OWN_LINK:
        if st.session_state.get("reading_goal", NO_READING_GOAL) == NO_READING_GOAL:
            st.session_state["catalog_reference"] = ""
        return
    item = article_by_label(label)
    st.session_state["page_link"] = item.learn_url
    st.session_state["study_goal"] = item.goal
    st.session_state["catalog_reference"] = item.linkedin_url


def _apply_goal_choice() -> None:
    """Copy a reading goal into the goal field. The page link stays as it is."""
    label = st.session_state["reading_goal"]
    if label == st.session_state.get("_applied_goal"):
        return
    st.session_state["_applied_goal"] = label
    if label == NO_READING_GOAL:
        article = st.session_state.get("starter_article", OWN_LINK)
        if article != OWN_LINK:
            st.session_state["catalog_reference"] = article_by_label(article).linkedin_url
        else:
            st.session_state["catalog_reference"] = ""
        return
    item = goal_by_label(label)
    st.session_state["study_goal"] = item.goal
    st.session_state["catalog_reference"] = item.linkedin_url


def _about_lines(outcome: StudyOutcome, settings: Settings) -> list[str]:
    """Return the lines kept under About this pack.

    The heading stays closed, so the first question is what you see.
    """
    lines: list[str] = []
    if outcome.ok and outcome.title:
        site = read_from_line(outcome.source_url)
        if site:
            lines.append(site)
        level = saved_level(outcome.level)
        if level:
            lines.append(level)
        length = saved_minutes(outcome.minutes)
        if length:
            lines.append(length)
        goal = outcome.goal.strip()
        if goal:
            lines.append(goal)
        day = saved_day(outcome.saved_on)
        if day:
            lines.append(day)
        pieces = saved_pieces(
            section.kind for section in outcome.sections if section.status == "ok"
        )
        if pieces:
            lines.append(pieces)
    if outcome.from_saved:
        lines.append("This study is the saved pack for this page.")
    if outcome.ok and outcome.sections:
        lines.append(pack_score_line(outcome))
        check = _latest_check_line(outcome, settings)
        if check:
            lines.append(check)
        progress = _progress_line(outcome, settings)
        if progress:
            lines.append(progress)
        question = _question_line(outcome, settings)
        if question:
            lines.append(question)
        replied = _reply_line(outcome, settings)
        if replied:
            lines.append(replied)
        remaining = _remaining_line(outcome, settings)
        if remaining:
            lines.append(remaining)
    if _lesson_is_empty(outcome):
        lines.append(EMPTY_LESSON_HINT)
    if _project_is_uncovered(outcome):
        lines.append(UNCOVERED_PROJECT_NOTE)
    return lines


def _show(outcome: StudyOutcome, settings: Settings) -> None:
    """Show the pack. Lesson answers stay hidden until a reply is checked."""
    if outcome.ok and outcome.title:
        st.header(outcome.title)
    about = _about_lines(outcome, settings)
    if about:
        with st.expander("About this pack", expanded=False):
            for line in about:
                st.caption(line)
    if outcome.ok and outcome.sections:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.download_button(
                "Download Markdown",
                data=pack_markdown(outcome),
                file_name=markdown_filename(outcome.title),
                mime="text/markdown",
            )
            st.download_button(
                "Download Word",
                data=pack_docx(outcome),
                file_name=word_filename(outcome.title),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
    blocks = list(display_blocks(outcome))
    if outcome.ok and outcome.resource_id and outcome.checks:
        lesson_blocks = [block for block in blocks if block[0] == "lesson"]
        other_blocks = [block for block in blocks if block[0] != "lesson"]
        _show_checks(outcome, settings, start=0, stop=1)
        _render_blocks(lesson_blocks)
        if len(outcome.checks) > 1:
            _show_checks(outcome, settings, start=1, stop=len(outcome.checks))
        _render_blocks(other_blocks)
    else:
        _render_blocks(blocks)
    if outcome.resource_id:
        _show_rewrites(outcome, settings)


def _show_waiting(store: StudyStore, *, owner_id: str) -> None:
    """List questions that still need a correct reply.

    Opening one reads the saved pack. It does not fetch a page or call the model.
    """
    rows = waiting_questions(store, owner_id=owner_id)
    if not rows:
        return
    st.subheader("Questions still waiting")
    for index, row in enumerate(rows):
        if st.button(row.question, key=f"waiting-{row.resource_id}-{index}"):
            outcome = open_saved(store, row.resource_id, owner_id=owner_id)
            outcome = focus_waiting_question(outcome, row.question)
            st.session_state["study_outcome"] = outcome
            resource = store.get_resource(row.resource_id)
            if resource.owner_id == owner_id:
                _queue_opened_pack(outcome, resource.extracted_text)
            st.rerun()


def _show_history(store: StudyStore, *, owner_id: str = LOCAL_LEARNER_ID) -> None:
    """List saved packs. Opening one reads the database only."""
    studies = saved_studies(store, owner_id=owner_id)
    if not studies:
        return
    st.subheader("Saved studies")
    query = st.text_input(
        "Find a study",
        key="find_study",
        placeholder="Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, reply, left, or empty",
    )
    piece_lines = {
        resource.id: saved_pieces(
            artifact.kind
            for artifact in store.list_artifacts(resource.id)
            if artifact.status == "ok"
        )
        for resource in studies
    }
    length_lines = {resource.id: saved_minutes(resource.minutes) for resource in studies}
    site_lines = {resource.id: read_from_line(resource.url) for resource in studies}
    day_lines = {resource.id: saved_day(resource.fetched_at) for resource in studies}
    level_lines = {resource.id: saved_level(resource.level) for resource in studies}
    score_lines: dict[int, str] = {}
    empty_lines: dict[int, str] = {}
    runbook_lines: dict[int, str] = {}
    project_lines: dict[int, str] = {}
    for resource in studies:
        opened = open_saved(store, resource.id)
        if opened.ok and opened.sections:
            score_lines[resource.id] = pack_score_line(opened)
            if _lesson_is_empty(opened):
                empty_lines[resource.id] = EMPTY_LESSON_NOTE
            if _runbook_is_empty(opened):
                runbook_lines[resource.id] = EMPTY_RUNBOOK_NOTE
            if _project_is_uncovered(opened):
                project_lines[resource.id] = UNCOVERED_PROJECT_NOTE
    check_lines: dict[int, str] = {}
    progress_lines: dict[int, str] = {}
    question_lines: dict[int, str] = {}
    reply_lines: dict[int, str] = {}
    remaining_lines: dict[int, str] = {}
    for resource in studies:
        attempts = store.list_attempts(resource.id)
        questions = store.list_lesson_checks(resource.id)
        if attempts:
            latest = attempts[-1]
            line = saved_check(latest.score)
            if line:
                check_lines[resource.id] = line
                question = saved_question(latest.question)
                if question:
                    question_lines[resource.id] = question
                replied = reply_day(latest.created_at)
                if replied:
                    reply_lines[resource.id] = replied
        answered = {item.question for item in attempts}
        answered_count = sum(1 for item in questions if item.question in answered)
        progress = saved_progress(answered_count, len(questions))
        if progress:
            progress_lines[resource.id] = progress
        remaining = left_to_check(answered_count, len(questions))
        if remaining:
            remaining_lines[resource.id] = remaining
    studies = matching_studies(
        studies,
        query,
        piece_lines,
        length_lines,
        site_lines,
        day_lines,
        level_lines,
        score_lines,
        check_lines,
        progress_lines,
        question_lines,
        reply_lines,
        remaining_lines,
        empty_lines,
        runbook_lines,
        project_lines,
    )
    if not studies:
        st.markdown("No saved study matches that.")
        return
    for resource in studies:
        label = resource.title or resource.url
        st.markdown(f"**{label}**")
        st.caption(resource.goal)
        length = saved_minutes(resource.minutes)
        if length:
            st.caption(length)
        step = _next_step(
            empty_lines.get(resource.id, ""),
            project_lines.get(resource.id, ""),
            remaining_lines.get(resource.id, ""),
        )
        if step:
            st.caption(step)
        confirm_key = f"confirm-delete-{resource.id}"
        open_col, delete_col = st.columns(2)
        with open_col:
            if st.button("Open study", key=f"open-{resource.id}"):
                outcome = open_saved(store, resource.id, owner_id=owner_id)
                st.session_state["study_outcome"] = outcome
                _queue_opened_pack(outcome, resource.extracted_text)
                st.rerun()
        with delete_col:
            waiting = bool(st.session_state.get(confirm_key))
            delete_label = "Delete this study?" if waiting else "Delete"
            if st.button(delete_label, key=f"delete-{resource.id}"):
                if not waiting:
                    st.session_state[confirm_key] = True
                    st.rerun()
                store.delete_resource(resource.id, owner_id=owner_id)
                st.session_state.pop(confirm_key, None)
                outcome = st.session_state.get("study_outcome")
                if isinstance(outcome, StudyOutcome) and outcome.resource_id == resource.id:
                    st.session_state.pop("study_outcome", None)
                st.rerun()


def _next_step(empty: str, project: str, remaining: str) -> str:
    """Return the one line under the minutes on the saved list.

    An empty lesson comes first. An uncovered project comes next.
    Otherwise the line says how many questions are still waiting.
    """
    if empty:
        return empty
    if project:
        return project
    return remaining


def _show_rewrites(outcome: StudyOutcome, settings: Settings) -> None:
    """Rewrite one section from the saved page text.

    A page with no procedure leaves Rewrite runbook off. The other rewrite buttons stay.
    """
    for kind in SECTION_KINDS:
        if kind == "runbook" and _runbook_is_empty(outcome):
            continue
        if not any(section.kind == kind for section in outcome.sections):
            continue
        if st.button(REWRITE_LABELS[kind], key=f"rewrite-{outcome.resource_id}-{kind}"):
            try:
                with st.spinner("Rewriting this section."):
                    st.session_state["study_outcome"] = regenerate_section(
                        store=StudyStore(settings.database_path),
                        resource_id=outcome.resource_id,
                        kind=kind,
                        settings=settings,
                    )
            except AgentError as exc:
                st.error(str(exc))
            else:
                st.rerun()


def _latest_check_line(outcome: StudyOutcome, settings: Settings) -> str:
    """Return the newest saved check, such as Last check: Partial."""
    if not outcome.resource_id:
        return ""
    attempts = StudyStore(settings.database_path).list_attempts(outcome.resource_id)
    if not attempts:
        return ""
    return saved_check(attempts[-1].score)


def _progress_line(outcome: StudyOutcome, settings: Settings) -> str:
    """Return how many questions have a reply, such as Checked 1 of 6.

    A pack with no questions stays blank. A second reply to the same question
    still counts as one question.
    """
    if not outcome.resource_id:
        return ""
    attempts = StudyStore(settings.database_path).list_attempts(outcome.resource_id)
    answered = {item.question for item in attempts}
    return saved_progress(
        sum(1 for item in outcome.checks if item.question in answered),
        len(outcome.checks),
    )


def _question_line(outcome: StudyOutcome, settings: Settings) -> str:
    """Return the newest question, such as Last question: What does the service do?

    A pack with no check stays blank. The hint and the reply stay off this line.
    """
    if not outcome.resource_id:
        return ""
    attempts = StudyStore(settings.database_path).list_attempts(outcome.resource_id)
    if not attempts:
        return ""
    latest = attempts[-1]
    if not saved_check(latest.score):
        return ""
    return saved_question(latest.question)


def _reply_line(outcome: StudyOutcome, settings: Settings) -> str:
    """Return the day of the newest reply, such as Reply day: October 25, 2026.

    A pack with no check stays blank. The hint and the reply stay off this line.
    """
    if not outcome.resource_id:
        return ""
    attempts = StudyStore(settings.database_path).list_attempts(outcome.resource_id)
    if not attempts:
        return ""
    latest = attempts[-1]
    if not saved_check(latest.score):
        return ""
    return reply_day(latest.created_at)


def _remaining_line(outcome: StudyOutcome, settings: Settings) -> str:
    """Return how many questions are still waiting, such as Left to check: 5.

    A pack with no questions stays blank. A finished pack says Left to check: 0.
    A second reply to the same question still counts as one question.
    """
    if not outcome.resource_id:
        return ""
    attempts = StudyStore(settings.database_path).list_attempts(outcome.resource_id)
    answered = {item.question for item in attempts}
    return left_to_check(
        sum(1 for item in outcome.checks if item.question in answered),
        len(outcome.checks),
    )


def _lesson_is_empty(outcome: StudyOutcome) -> bool:
    """An empty lesson has the one-line lesson and no question to check."""
    if not outcome.ok or not outcome.resource_id or outcome.checks:
        return False
    return any(
        kind == "lesson" and text.strip() == EMPTY_LESSON_MARKDOWN
        for kind, text in display_blocks(outcome)
    )


def _runbook_is_empty(outcome: StudyOutcome) -> bool:
    """An empty runbook is the two-sentence runbook and nothing else."""
    if not outcome.ok or not outcome.resource_id:
        return False
    return any(
        kind == "runbook" and text.strip() == EMPTY_RUNBOOK_MARKDOWN
        for kind, text in display_blocks(outcome)
    )


def _project_is_uncovered(outcome: StudyOutcome) -> bool:
    """A project is uncovered when its goal and deliverable are both left out."""
    if not outcome.ok or not outcome.resource_id:
        return False
    goal = f"Goal: {UNCOVERED_PROJECT_SENTENCE}"
    deliverable = f"Deliverable: {UNCOVERED_PROJECT_SENTENCE}"
    return any(
        kind == "project" and goal in text.splitlines() and deliverable in text.splitlines()
        for kind, text in display_blocks(outcome)
    )


def _render_blocks(blocks: list[tuple[str, str]]) -> None:
    """Show section text. An error block stays an error."""
    for kind, text in blocks:
        if kind == "error":
            st.error(text)
        elif kind == "picture":
            _render_picture(text)
        else:
            st.markdown(text)


def _render_picture(picture: str) -> None:
    """Draw the outline as stacked boxes. The words are the outline lines."""
    drawing = outline_picture_html(picture)
    if not drawing:
        return
    st.markdown("### Picture")
    st.html(drawing)


def _show_checks(
    outcome: StudyOutcome,
    settings: Settings,
    *,
    start: int,
    stop: int,
) -> None:
    """Ask for a reply, then show the saved score, hint, and answer."""
    store = StudyStore(settings.database_path)
    attempts = store.list_attempts(outcome.resource_id)
    for index, check in list(enumerate(outcome.checks))[start:stop]:
        st.subheader(check.question)
        latest = next(
            (item for item in reversed(attempts) if item.question == check.question),
            None,
        )
        reveal_key = f"reveal-{outcome.resource_id}-{index}"
        if latest is not None:
            st.markdown(f"**{SCORE_LABELS.get(latest.score, latest.score)}**")
            st.markdown(latest.hint)
            if st.session_state.get(reveal_key):
                stored = next(
                    (
                        row
                        for row in store.list_lesson_checks(outcome.resource_id)
                        if row.question == check.question
                    ),
                    None,
                )
                if stored is not None:
                    st.markdown(f"Answer: {stored.answer}")
        with st.form(f"reply-{outcome.resource_id}-{index}"):
            reply = st.text_area("Your answer", key=f"reply-{outcome.resource_id}-{index}")
            submitted = st.form_submit_button("Check my answer")
        if submitted:
            try:
                record_attempt(
                    store=store,
                    resource_id=outcome.resource_id,
                    question=check.question,
                    learner_answer=reply,
                    answer=check.answer,
                    excerpt=check.excerpt,
                    settings=settings,
                )
            except AgentError as exc:
                st.error(str(exc))
            else:
                st.session_state[reveal_key] = True
                st.rerun()


def _apply_style() -> None:
    """Give the page the look of a study notebook."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;600&family=Fraunces:opsz,wght@9..144,560&display=swap');
        .stApp { background: #e7efe9; color: #14221f; }
        .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea {
          font-family: Figtree, "Segoe UI", sans-serif;
        }
        .stApp h1, .stApp h2, .stApp h3 {
          font-family: Fraunces, Georgia, serif;
          color: #14221f;
          letter-spacing: -0.03em;
        }
        header[data-testid="stHeader"] { background: transparent; }
        [data-testid="stFormSubmitButton"] button {
          background: #1f6b4a;
          color: #f4f7f2;
          border: 0;
          border-radius: 999px;
        }
        [data-testid="stFormSubmitButton"] button:focus-visible {
          outline: 3px solid #14221f;
          outline-offset: 2px;
        }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            animation: none !important;
            transition: none !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
