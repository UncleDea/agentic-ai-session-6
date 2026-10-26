"""Tests for the study agent.

The model client is fake. These tests do not call OpenAI.
"""

import json
import logging

import pytest

from studymaster.agents.client import OpenAIModelClient
from studymaster.agents.errors import EmptySourceError, MissingApiKeyError, ModelResponseError
from studymaster.agents.quotes import quote_is_grounded, shown_sentence
from studymaster.agents.request import StudyRequest
from studymaster.agents.study import write_study
from studymaster.config import Settings

SOURCE = "Plants make food from sunlight, water, and carbon dioxide."
GOOD_QUOTE = "Plants make food from sunlight"
BAD_QUOTE = "Plants eat sunlight with their roots"


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "openai_api_key": None,
        "openai_model": "gpt-4o-mini",
        "fetch_timeout_seconds": 10,
        "max_response_bytes": 1_000_000,
        "max_source_chars": 20_000,
        "min_source_chars": 400,
        "database_path": "data/studymaster.db",
        "openai_timeout_seconds": 60,
        "openai_temperature": 0.2,
    }
    values.update(overrides)
    from pathlib import Path

    values["database_path"] = Path(str(values["database_path"]))
    return Settings(**values)  # type: ignore[arg-type]


def request(source: str = SOURCE) -> StudyRequest:
    return StudyRequest(
        title="Photosynthesis",
        url="https://example.com/plants",
        headings=["How plants make food"],
        source_text=source,
        level="beginner",
        goal="Explain photosynthesis",
        minutes=20,
    )


class FakeModel:
    """Returns scripted replies and records every prompt."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, instructions: str, prompt: str) -> str:
        self.calls.append((instructions, prompt))
        if not self._replies:
            raise AssertionError("the model was called too many times")
        return self._replies.pop(0)


def study_json() -> str:
    return json.dumps(
        {
            "objectives": "Explain how plants make food.",
            "objectives_quote": GOOD_QUOTE,
            "explanation": "Leaves use sunlight, water, and carbon dioxide.",
            "explanation_quote": GOOD_QUOTE,
            "glossary": [
                {
                    "term": "photosynthesis",
                    "plain_definition": "The way plants make food.",
                    "quote": GOOD_QUOTE,
                }
            ],
            "misconceptions": [
                {
                    "wrong": "Plants eat sunlight with their roots.",
                    "right": "Plants use sunlight in their leaves.",
                    "quote": BAD_QUOTE,
                }
            ],
            "recap": "Plants make food from sunlight, water, and carbon dioxide.",
            "recap_quote": GOOD_QUOTE,
        }
    )


def test_prompt_contains_the_source_and_the_source_rule() -> None:
    model = FakeModel(["1. Leaves", study_json(), '{"replacements": []}'])

    write_study(request(), complete=model.complete)

    assert len(model.calls) == 3
    for instructions, prompt in model.calls:
        combined = f"{instructions}\n{prompt}"
        assert SOURCE in combined
        assert "use only this source" in combined.casefold()
    assert "1. Leaves" in model.calls[1][1]


def test_empty_source_never_calls_the_client() -> None:
    model = FakeModel([])

    with pytest.raises(EmptySourceError):
        write_study(request("   "), complete=model.complete)

    assert model.calls == []


def test_missing_api_key_stops_before_any_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OpenAI was constructed")

    monkeypatch.setattr("studymaster.agents.client.OpenAI", fail_if_called)

    with pytest.raises(MissingApiKeyError):
        write_study(request(), settings=settings(openai_api_key=None))


def test_quote_in_the_source_passes() -> None:
    assert quote_is_grounded("Plants   make   food from sunlight", SOURCE)


def test_quote_not_in_the_source_is_not_grounded() -> None:
    model = FakeModel(["1. Leaves", study_json(), '{"replacements": []}'])

    material = write_study(request(), complete=model.complete)

    flagged = [item for item in material.checks if item.label == "misconception 1"]
    assert flagged[0].grounded is False
    assert "The source does not cover this." in material.markdown
    assert "roots" not in material.markdown
    assert "Plants make food from sunlight, water, and carbon dioxide." in material.markdown
    assert "Quote: Plants make food from sunlight" in material.markdown
    assert any(item.grounded for item in material.checks if item.label == "objectives")


def test_a_paraphrase_stays_when_its_extra_word_is_on_the_page() -> None:
    sentence = "Plants make food from sunlight and water."
    assert shown_sentence(sentence, GOOD_QUOTE, SOURCE) == sentence


def test_a_missing_quote_leaves_the_sentence_out() -> None:
    assert (
        shown_sentence("Plants make food from sunlight.", BAD_QUOTE, SOURCE)
        == "The source does not cover this."
    )


def test_a_word_missing_from_the_page_leaves_the_sentence_out() -> None:
    assert (
        shown_sentence("Plants make food with their roots.", GOOD_QUOTE, SOURCE)
        == "The source does not cover this."
    )


def test_adding_or_dropping_not_leaves_the_sentence_out() -> None:
    denied = "Plants do not make food from sunlight."
    assert shown_sentence(denied, GOOD_QUOTE, SOURCE) == "The source does not cover this."
    source = "Plants do not make food from sunlight."
    quote = "Plants do not make food"
    assert shown_sentence(denied, quote, source) == denied
    assert (
        shown_sentence("Plants make food from sunlight.", quote, source)
        == "The source does not cover this."
    )


def test_study_result_has_every_section() -> None:
    model = FakeModel(["1. Leaves", study_json(), '{"replacements": []}'])

    material = write_study(request(), complete=model.complete)

    assert "Explain how plants make food." in material.objectives
    assert "Leaves use sunlight" in material.explanation
    assert material.glossary[0].term == "photosynthesis"
    assert "roots" in material.misconceptions[0].wrong
    assert "carbon dioxide" in material.recap
    for heading in ("## Objectives", "## Explanation", "## Glossary", "## Misconceptions", "## Recap"):
        assert heading in material.markdown


def test_client_uses_timeout_and_temperature_without_logging_the_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "sk-test-secret-value"
    seen: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):
            seen.update(kwargs)

            class Reply:
                output_text = "outline"

            return Reply()

    class FakeOpenAI:
        def __init__(self, *, api_key: str, timeout: float) -> None:
            seen["api_key"] = api_key
            seen["client_timeout"] = timeout
            self.responses = FakeResponses()

    monkeypatch.setattr("studymaster.agents.client.OpenAI", FakeOpenAI)
    client = OpenAIModelClient(
        settings(openai_api_key=secret, openai_temperature=0.2, openai_timeout_seconds=30)
    )

    with caplog.at_level(logging.INFO):
        assert client.complete(instructions="rules", prompt="source") == "outline"

    assert seen["api_key"] == secret
    assert seen["client_timeout"] == 30
    assert seen["temperature"] == 0.2
    assert seen["timeout"] == 30
    assert seen["model"] == "gpt-4o-mini"
    assert secret not in caplog.text
    assert "gpt-4o-mini" in caplog.text


def _grounded_study() -> str:
    sentence = "Plants make food from sunlight."
    return json.dumps(
        {
            "objectives": sentence,
            "objectives_quote": GOOD_QUOTE,
            "explanation": sentence,
            "explanation_quote": GOOD_QUOTE,
            "glossary": [],
            "misconceptions": [],
            "recap": sentence,
            "recap_quote": GOOD_QUOTE,
        }
    )


def test_a_supported_section_is_not_repaired() -> None:
    model = FakeModel([_grounded_study()])

    material = write_study(request(), complete=model.complete, outline="1. Food")

    assert len(model.calls) == 1
    assert "Plants make food from sunlight." in material.markdown


def test_a_failed_sentence_is_rewritten_once() -> None:
    payload = json.loads(study_json())
    payload["objectives"] = "Plants make food with their roots."
    repair = json.dumps(
        {"replacements": [{"id": "objectives", "text": "Plants make food from sunlight."}]}
    )
    model = FakeModel([json.dumps(payload), repair])

    material = write_study(request(), complete=model.complete, outline="1. Food")

    assert material.objectives == "Plants make food from sunlight."
    assert "Plants make food from sunlight." in material.markdown
    assert "roots" not in material.markdown
    assert len(model.calls) == 2
    assert "Repair these sentences" in model.calls[1][0]


def test_a_second_failure_stays_left_out() -> None:
    payload = json.loads(_grounded_study())
    payload["objectives"] = "Plants make food with their roots."
    repair = json.dumps(
        {"replacements": [{"id": "objectives", "text": "Plants grow underground."}]}
    )
    model = FakeModel([json.dumps(payload), repair])

    material = write_study(request(), complete=model.complete, outline="1. Food")

    assert material.objectives == "Plants make food with their roots."
    assert "The source does not cover this." in material.markdown
    assert "underground" not in material.markdown
    assert "roots" not in material.markdown
    assert len(model.calls) == 2


def test_a_non_json_reply_is_tried_once() -> None:
    model = FakeModel(["not json", _grounded_study()])

    material = write_study(request(), complete=model.complete, outline="1. Food")

    assert "Plants make food from sunlight." in material.markdown
    assert len(model.calls) == 2
    assert "JSON object only" in model.calls[1][1]


def test_a_second_non_json_reply_stops_that_section() -> None:
    model = FakeModel(["not json", "still not json"])

    with pytest.raises(ModelResponseError):
        write_study(request(), complete=model.complete, outline="1. Food")

    assert len(model.calls) == 2
