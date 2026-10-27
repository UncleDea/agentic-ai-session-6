"""Tests for the outline picture.

The picture is drawn from the outline lines. These tests do not call OpenAI.
"""

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
