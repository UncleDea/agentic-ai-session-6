"""The StudyMaster AI page.

The learner pastes one public link. The study pack is written only after
they press the button, and lesson answers stay off the page.
"""

import logging

import streamlit as st

from studymaster.agents.coordinator import SECTION_KINDS
from studymaster.agents.errors import AgentError
from studymaster.agents.grader import SCORE_LABELS, record_attempt
from studymaster.config import Settings, get_settings
from studymaster.logging_setup import configure_logging
from studymaster.sample_links import (
    NO_READING_GOAL,
    OWN_LINK,
    READING_GOAL_CAPTION,
    article_by_label,
    article_links,
    choice_label,
    goal_by_label,
    reading_goals,
)
from studymaster.storage.database import StudyStore
from studymaster.ui.study_flow import (
    StudyOutcome,
    display_blocks,
    markdown_filename,
    matching_studies,
    open_saved,
    pack_markdown,
    regenerate_section,
    pack_score_line,
    saved_day,
    saved_studies,
    study_page,
)

REWRITE_LABELS = {
    "study": "Rewrite study",
    "lesson": "Rewrite lesson",
    "lab": "Rewrite lab",
    "project": "Rewrite project",
    "runbook": "Rewrite runbook",
}

logger = logging.getLogger(__name__)


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
    st.title("StudyMaster AI")
    st.markdown(
        "Paste one public page. The study pack uses only the words on that page."
    )
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
        submitted = st.form_submit_button("Study this page")

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
            def report(message: str) -> None:
                status.update(label=message)

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
            )
            if outcome.ok:
                status.update(label="Study pack ready.", state="complete")
            else:
                status.update(label=outcome.message, state="error")
            st.session_state["study_outcome"] = outcome

    outcome = st.session_state.get("study_outcome")
    if isinstance(outcome, StudyOutcome):
        _show(outcome, settings)
    _show_history(StudyStore(settings.database_path))


def _reset_screen() -> None:
    """Clear the open pack and the form before the boxes are drawn.

    Saved studies stay in the database. The find box keeps its words.
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
    st.session_state.pop("study_outcome", None)


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


def _show(outcome: StudyOutcome, settings: Settings) -> None:
    """Show the pack. Lesson answers stay hidden until a reply is checked."""
    if outcome.ok and outcome.title:
        st.header(outcome.title)
    if outcome.from_saved:
        st.caption("This study is the saved pack for this page.")
    if outcome.ok and outcome.sections:
        st.caption(pack_score_line(outcome))
    for kind, text in display_blocks(outcome):
        if kind == "error":
            st.error(text)
        else:
            st.markdown(text)
    if outcome.ok and outcome.sections:
        st.download_button(
            "Download Markdown",
            data=pack_markdown(outcome),
            file_name=markdown_filename(outcome.title),
            mime="text/markdown",
        )
    if outcome.resource_id:
        _show_rewrites(outcome, settings)
    if outcome.ok and outcome.resource_id and outcome.checks:
        _show_checks(outcome, settings)


def _show_history(store: StudyStore) -> None:
    """List saved packs. Opening one reads the database only."""
    studies = saved_studies(store)
    if not studies:
        return
    st.subheader("Saved studies")
    query = st.text_input(
        "Find a study",
        key="find_study",
        placeholder="Type part of a title or goal",
    )
    studies = matching_studies(studies, query)
    if not studies:
        st.markdown("No saved study matches that.")
        return
    for resource in studies:
        label = resource.title or resource.url
        st.markdown(f"**{label}**")
        st.caption(resource.goal)
        day = saved_day(resource.fetched_at)
        if day:
            st.caption(day)
        confirm_key = f"confirm-delete-{resource.id}"
        open_col, delete_col = st.columns(2)
        with open_col:
            if st.button("Open study", key=f"open-{resource.id}"):
                st.session_state["study_outcome"] = open_saved(store, resource.id)
                st.rerun()
        with delete_col:
            waiting = bool(st.session_state.get(confirm_key))
            delete_label = "Delete this study?" if waiting else "Delete"
            if st.button(delete_label, key=f"delete-{resource.id}"):
                if not waiting:
                    st.session_state[confirm_key] = True
                    st.rerun()
                store.delete_resource(resource.id)
                st.session_state.pop(confirm_key, None)
                outcome = st.session_state.get("study_outcome")
                if isinstance(outcome, StudyOutcome) and outcome.resource_id == resource.id:
                    st.session_state.pop("study_outcome", None)
                st.rerun()


def _show_rewrites(outcome: StudyOutcome, settings: Settings) -> None:
    """Rewrite one section from the saved page text."""
    for kind in SECTION_KINDS:
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


def _show_checks(outcome: StudyOutcome, settings: Settings) -> None:
    """Ask for a reply, then show the saved score, hint, and answer."""
    store = StudyStore(settings.database_path)
    attempts = store.list_attempts(outcome.resource_id)
    for index, check in enumerate(outcome.checks):
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
