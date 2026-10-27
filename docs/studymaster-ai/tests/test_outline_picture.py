"""Tests for the outline picture.

The picture is drawn from the outline lines. These tests do not call OpenAI.
"""

from pathlib import Path

from studymaster.agents.coordinator import AgentSection
from studymaster.ui.study_flow import (
    StudyOutcome,
    display_blocks,
    outline_picture_html,
    outline_picture_markdown,
    outline_steps,
)


def test_picture_uses_only_the_outline_lines() -> None:
    """Each box is an outline line. A fact from outside the outline stays off."""
    outline = "1. How plants make food\n2. Leaves collect light"
    assert outline_steps(outline) == ["How plants make food", "Leaves collect light"]
    picture = outline_picture_markdown(outline)
    assert picture.splitlines() == [
        "### Picture",
        "",
        "How plants make food",
        "↓",
        "Leaves collect light",
    ]
    assert "roots" not in picture
    drawing = outline_picture_html(picture)
    assert "How plants make food" in drawing
    assert "Leaves collect light" in drawing
    assert "roots" not in drawing


def test_picture_escapes_outline_marks() -> None:
    """A mark in an outline line is shown as text."""
    picture = outline_picture_markdown("1. Use <light> and water")
    drawing = outline_picture_html(picture)
    assert "Use &lt;light&gt; and water" in drawing
    assert "<light>" not in drawing


def test_picture_sits_under_the_outline() -> None:
    """The pack shows the picture after the outline and before the study."""
    outcome = StudyOutcome(
        ok=True,
        message="",
        title="Photosynthesis",
        outline="1. How plants make food",
        sections=(
            AgentSection(
                "study",
                "ok",
                "",
                "## Objectives\nExplain the page.",
                [],
            ),
        ),
    )
    kinds = [kind for kind, _text in display_blocks(outcome)]
    assert kinds[:3] == ["outline", "picture", "study"]


def test_a_saved_pack_shows_the_picture_from_its_outline(tmp_path: Path) -> None:
    """Opening a saved pack draws the picture without another model call."""
    from studymaster.config import Settings
    from studymaster.extraction.fetch import Article
    from studymaster.storage.database import StudyStore
    from studymaster.ui.study_flow import open_saved, study_page
    from tests.test_specialists import SOURCE, RoutingModel, _replies

    database = tmp_path / "study.db"
    model = RoutingModel(_replies())
    store = StudyStore(database)
    settings = Settings(
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        fetch_timeout_seconds=10,
        max_response_bytes=1_000_000,
        max_source_chars=20_000,
        min_source_chars=400,
        database_path=database,
        openai_timeout_seconds=60,
        openai_temperature=0.2,
    )

    def read(url: str, settings: object = None) -> Article:
        return Article(
            url=url,
            title="Photosynthesis",
            headings=["How plants make food"],
            text=SOURCE,
            shortened=False,
        )

    fresh = study_page(
        url="https://example.com/plants",
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
        settings=settings,
        store=store,
        read=read,
        complete=model.complete,
    )
    used = len(model.prompts)
    opened = open_saved(store, fresh.resource_id)
    blocks = display_blocks(opened)
    texts = [text for _kind, text in blocks]
    picture_at = next(index for index, (kind, _text) in enumerate(blocks) if kind == "picture")
    assert "How plants make food" in texts[picture_at - 1]
    assert "### Picture" in texts[picture_at]
    assert texts[picture_at + 1].startswith("## Objectives")
    assert "roots" not in texts[picture_at]
    assert len(model.prompts) == used
