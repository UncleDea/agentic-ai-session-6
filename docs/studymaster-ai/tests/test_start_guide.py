"""Tests for the start guide.

These tests read the guide file. They do not start the page or call OpenAI.
"""

from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def test_start_guide_names_the_command_and_the_button():
    text = README.read_text(encoding="utf-8")
    assert r".\.venv\Scripts\python.exe -m streamlit run app.py" in text
    assert "Study this page" in text
