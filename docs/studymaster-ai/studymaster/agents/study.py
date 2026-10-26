"""Write study material from a page and check its quotes."""

from dataclasses import dataclass

from studymaster.agents.client import Completer, OpenAIModelClient
from studymaster.agents.errors import EmptySourceError
from studymaster.agents.outline import write_outline
from studymaster.agents.parsing import complete_json
from studymaster.agents.quotes import (
    CheckedQuote,
    check_quote,
    quote_line,
    shown_sentence,
)
from studymaster.agents.repair import RepairItem, repair_texts
from studymaster.agents.request import StudyRequest
from studymaster.config import Settings, get_settings
from studymaster.prompts.study import study_instructions, study_prompt


@dataclass(frozen=True)
class GlossaryEntry:
    """One term explained from the source."""

    term: str
    plain_definition: str
    quote: str
    grounded: bool


@dataclass(frozen=True)
class Misconception:
    """One wrong idea corrected from the source."""

    wrong: str
    right: str
    quote: str
    grounded: bool


@dataclass(frozen=True)
class StudyMaterial:
    """Study material plus the quote check for each section."""

    objectives: str
    explanation: str
    glossary: list[GlossaryEntry]
    misconceptions: list[Misconception]
    recap: str
    checks: list[CheckedQuote]
    markdown: str
    outline: str


def write_study(
    request: StudyRequest,
    *,
    complete: Completer | None = None,
    settings: Settings | None = None,
    outline: str | None = None,
) -> StudyMaterial:
    """Write the study material. An empty source never calls the model."""
    if not request.source_text.strip():
        raise EmptySourceError("There is no source text to study.")
    caller = complete or OpenAIModelClient(settings or get_settings()).complete
    shared_outline = outline if outline is not None else write_outline(request, caller)
    payload = complete_json(
        caller,
        instructions=study_instructions(),
        prompt=study_prompt(request, shared_outline),
    )
    return _material_from_payload(request.source_text, shared_outline, payload, caller)


def _material_from_payload(
    source_text: str,
    outline: str,
    payload: dict,
    complete: Completer,
) -> StudyMaterial:
    objectives = str(payload.get("objectives", "")).strip()
    explanation = str(payload.get("explanation", "")).strip()
    recap = str(payload.get("recap", "")).strip()
    checks = [
        check_quote("objectives", str(payload.get("objectives_quote", "")), source_text),
        check_quote("explanation", str(payload.get("explanation_quote", "")), source_text),
        check_quote("recap", str(payload.get("recap_quote", "")), source_text),
    ]
    glossary = []
    for index, item in enumerate(payload.get("glossary", []), start=1):
        checked = check_quote(
            f"glossary {index}",
            str(item.get("quote", "")),
            source_text,
        )
        checks.append(checked)
        glossary.append(
            GlossaryEntry(
                term=str(item.get("term", "")).strip(),
                plain_definition=str(item.get("plain_definition", "")).strip(),
                quote=checked.quote,
                grounded=checked.grounded,
            )
        )
    misconceptions = []
    for index, item in enumerate(payload.get("misconceptions", []), start=1):
        checked = check_quote(
            f"misconception {index}",
            str(item.get("quote", "")),
            source_text,
        )
        checks.append(checked)
        misconceptions.append(
            Misconception(
                wrong=str(item.get("wrong", "")).strip(),
                right=str(item.get("right", "")).strip(),
                quote=checked.quote,
                grounded=checked.grounded,
            )
        )
    fixed = repair_texts(
        [
            RepairItem("objectives", objectives, checks[0].quote),
            RepairItem("explanation", explanation, checks[1].quote),
            RepairItem("recap", recap, checks[2].quote),
            *[
                RepairItem(f"glossary-{index}", entry.plain_definition, entry.quote)
                for index, entry in enumerate(glossary)
            ],
            *[
                RepairItem(f"wrong-{index}", entry.wrong, entry.quote)
                for index, entry in enumerate(misconceptions)
            ],
            *[
                RepairItem(f"right-{index}", entry.right, entry.quote)
                for index, entry in enumerate(misconceptions)
            ],
        ],
        source_text,
        complete,
    )
    objectives = fixed.get("objectives", objectives)
    explanation = fixed.get("explanation", explanation)
    recap = fixed.get("recap", recap)
    glossary = [
        GlossaryEntry(
            entry.term,
            fixed.get(f"glossary-{index}", entry.plain_definition),
            entry.quote,
            entry.grounded,
        )
        for index, entry in enumerate(glossary)
    ]
    misconceptions = [
        Misconception(
            fixed.get(f"wrong-{index}", entry.wrong),
            fixed.get(f"right-{index}", entry.right),
            entry.quote,
            entry.grounded,
        )
        for index, entry in enumerate(misconceptions)
    ]
    return StudyMaterial(
        objectives=objectives,
        explanation=explanation,
        glossary=glossary,
        misconceptions=misconceptions,
        recap=recap,
        checks=checks,
        markdown=_markdown(
            objectives,
            explanation,
            glossary,
            misconceptions,
            recap,
            checks,
            source_text,
        ),
        outline=outline,
    )


def _markdown(
    objectives: str,
    explanation: str,
    glossary: list[GlossaryEntry],
    misconceptions: list[Misconception],
    recap: str,
    checks: list[CheckedQuote],
    source_text: str,
) -> str:
    by_label = {item.label: item for item in checks}
    lines = ["## Objectives"]
    _append_field(lines, objectives, by_label["objectives"].quote, source_text)
    lines.extend(["", "## Explanation"])
    _append_field(lines, explanation, by_label["explanation"].quote, source_text)
    lines.extend(["", "## Glossary"])
    if not glossary:
        lines.append("The source does not cover a glossary.")
    for entry in glossary:
        quote = by_label[f"glossary {glossary.index(entry) + 1}"].quote
        lines.append(
            f"- **{entry.term}**: {shown_sentence(entry.plain_definition, quote, source_text)}"
        )
        _append_quote(lines, [entry.plain_definition], quote, source_text)
    lines.extend(["", "## Misconceptions"])
    if not misconceptions:
        lines.append("The source does not cover misconceptions.")
    for entry in misconceptions:
        quote = by_label[f"misconception {misconceptions.index(entry) + 1}"].quote
        lines.append(f"- Wrong: {shown_sentence(entry.wrong, quote, source_text)}")
        lines.append(f"  Right: {shown_sentence(entry.right, quote, source_text)}")
        _append_quote(lines, [entry.wrong, entry.right], quote, source_text, indent="  ")
    lines.extend(["", "## Recap"])
    _append_field(lines, recap, by_label["recap"].quote, source_text)
    return "\n".join(lines)


def _append_field(lines: list[str], text: str, quote: str, source_text: str) -> None:
    lines.append(shown_sentence(text, quote, source_text))
    _append_quote(lines, [text], quote, source_text)


def _append_quote(
    lines: list[str],
    sentences: list[str],
    quote: str,
    source_text: str,
    indent: str = "",
) -> None:
    line = quote_line(sentences, quote, source_text)
    if line:
        lines.append(f"{indent}{line}")
