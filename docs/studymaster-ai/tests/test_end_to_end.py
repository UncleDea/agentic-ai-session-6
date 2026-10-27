"""One offline walk from a link to a saved pack.

The page and the model are fakes. This test does not call the public
internet or OpenAI.
"""

from pathlib import Path
from zipfile import ZipFile
from io import BytesIO

import pytest

from studymaster.agents.client import OpenAIModelClient
from studymaster.agents.coordinator import SECTION_KINDS
from studymaster.agents.errors import MissingApiKeyError
from studymaster.config import Settings
from studymaster.extraction.fetch import Article
from studymaster.storage.database import StudyStore
from studymaster.ui.home import OPEN_PACK_NOTE
from studymaster.ui.study_flow import (
    display_blocks,
    pack_docx,
    pack_markdown,
    study_page,
)
from tests.test_specialists import HIDDEN_ANSWER, OUTLINE, SOURCE, RoutingModel, _replies

PAGE = "https://example.com/plants"
GOAL = "Explain photosynthesis"
QUESTION = "What do plants use to make food?"
REPLY = "Sunlight, water, and carbon dioxide."
HINT = "Name the three ingredients on the page."


def _settings(path: Path) -> Settings:
    return Settings(
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        fetch_timeout_seconds=10,
        max_response_bytes=1_000_000,
        max_source_chars=20_000,
        min_source_chars=400,
        database_path=path,
        openai_timeout_seconds=60,
        openai_temperature=0.2,
    )


def _article(url: str) -> Article:
    return Article(
        url=url,
        title="Photosynthesis",
        headings=["How plants make food"],
        text=SOURCE,
        shortened=False,
    )


def _visible(outcome: object) -> str:
    return "\n".join(text for _, text in display_blocks(outcome))


def _page_order(app: object) -> list[str]:
    found: list[str] = []

    def walk(node: object) -> None:
        kind = getattr(node, "type", "")
        if kind == "download_button":
            found.append(str(getattr(node, "label", "")))
        elif kind == "subheader":
            found.append(str(getattr(node, "value", "")))
        children = getattr(node, "children", None)
        if isinstance(children, dict):
            for child in children.values():
                walk(child)

    walk(app.main)
    return found


def _page_text(app: object) -> str:
    parts: list[str] = []
    for collection in ("markdown", "subheader", "header", "caption", "error"):
        for block in getattr(app, collection):
            parts.append(str(getattr(block, "value", "")))
    return "\n".join(parts)


def _flat(node: object) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    def walk(current: object) -> None:
        kind = getattr(current, "type", "")
        if kind in {"markdown", "caption"}:
            found.append((kind, str(getattr(current, "value", ""))))
        elif kind == "button":
            found.append((kind, str(getattr(current, "label", ""))))
        children = getattr(current, "children", None)
        if isinstance(children, dict):
            for child in children.values():
                walk(child)

    walk(node)
    return found


def _saved_row(app: object) -> list[str]:
    rows = _flat(app.main)
    start = next(index for index, item in enumerate(rows) if "Photosynthesis" in item[1])
    stop = next(
        index for index, item in enumerate(rows) if index > start and item == ("button", "Open study")
    )
    return [text for _, text in rows[start:stop]]


def test_learner_path_from_link_to_saved_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Walk the learner path with a fake page and a fake model."""
    downloads: list[str] = []

    def fail_download(*_args: object, **_kwargs: object) -> None:
        downloads.append("downloaded")
        raise AssertionError("a page was downloaded")

    def fail_openai(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an OpenAI client was built")

    monkeypatch.setattr("studymaster.extraction.fetch.requests.get", fail_download)
    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_openai)

    database = tmp_path / "study.db"
    store = StudyStore(database)
    refused = study_page(
        url="http://127.0.0.1/secret",
        level="Beginner",
        goal=GOAL,
        minutes=20,
        settings=_settings(database),
        store=store,
        complete=fail_openai,
    )
    assert refused.ok is False
    assert refused.message == "This address cannot be opened."
    assert downloads == []

    with pytest.raises(MissingApiKeyError):
        OpenAIModelClient(_settings(database))

    model = RoutingModel(_replies())

    def read(url: str, settings: object = None) -> Article:
        return _article(url)

    page = dict(
        url=PAGE,
        level="Beginner",
        goal=GOAL,
        minutes=20,
        settings=_settings(database),
        store=store,
        read=read,
        complete=model.complete,
    )
    first = study_page(**page)
    visible = _visible(first)
    assert first.ok is True
    assert [section.kind for section in first.sections] == list(SECTION_KINDS)
    assert OUTLINE in visible
    assert HIDDEN_ANSWER not in visible
    assert HIDDEN_ANSWER not in pack_markdown(first)
    word = pack_docx(first)
    assert word.startswith(b"PK")
    with ZipFile(BytesIO(word)) as package:
        document = package.read("word/document.xml").decode("utf-8")
    assert HIDDEN_ANSWER not in document

    used = len(model.prompts)
    second = study_page(
        **page,
        remembered_answers=first.hidden_answers,
        remembered_hash=first.content_hash,
    )
    assert second.from_saved is True
    assert len(model.prompts) == used

    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DATABASE_PATH", str(database))
    monkeypatch.setenv("OPENAI_API_KEY", "")

    def fail_study(**_kwargs: object) -> None:
        raise AssertionError("the page was studied again")

    def fake_record(**kwargs: object) -> object:
        return store.save_attempt(
            resource_id=int(kwargs["resource_id"]),
            question=str(kwargs["question"]),
            learner_answer=str(kwargs["learner_answer"]),
            score="partial",
            hint=HINT,
        )

    monkeypatch.setattr("studymaster.ui.home.study_page", fail_study)
    monkeypatch.setattr("studymaster.ui.home.record_attempt", fake_record)

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Open study").click()
    app.run()

    order = _page_order(app)
    assert QUESTION in order
    assert order.index("Download Word") < order.index(QUESTION)
    rows = [
        box
        for box in app.container
        if {
            str(getattr(child, "label", ""))
            for child in box.children.values()
        }
        >= {"Download Markdown", "Download Word"}
    ]
    assert len(rows) == 1
    assert rows[0].proto.flex_container.direction == 2
    about = next(item for item in app.expander if item.label == "About this pack")
    assert about.proto.expanded is False
    assert HIDDEN_ANSWER not in _page_text(app)

    saved = _saved_row(app)
    assert saved == [
        "**Photosynthesis**",
        GOAL,
        "20 minutes",
        "The project is not covered by this page.",
    ]

    assert next(box for box in app.text_input if box.label == "Page link").value == PAGE
    assert next(box for box in app.text_input if box.label == "Goal").value == GOAL
    assert next(box for box in app.selectbox if box.label == "Level").value == "Beginner"
    assert next(box for box in app.number_input if box.label == "Minutes").value == 20
    assert OPEN_PACK_NOTE in _page_text(app)

    next(box for box in app.text_area if box.label == "Your answer").set_value(REPLY)
    next(button for button in app.button if button.label == "Check my answer").click()
    app.run()
    assert "Partial" in _page_text(app)

    next(button for button in app.button if button.label == "Start over").click()
    app.run()
    assert OPEN_PACK_NOTE not in _page_text(app)
