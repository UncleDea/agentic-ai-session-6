"""Write an execution runbook, or say when the page has no procedure."""

from dataclasses import dataclass

from studymaster.agents.client import Completer
from studymaster.agents.lab import NO_PROCEDURE
from studymaster.agents.parsing import complete_json, object_list
from studymaster.agents.quotes import CheckedQuote, check_quote, quote_line, shown_sentence
from studymaster.agents.repair import RepairItem, repair_texts
from studymaster.agents.request import StudyRequest
from studymaster.prompts.runbook import runbook_instructions, runbook_prompt


@dataclass(frozen=True)
class RunbookStep:
    """One numbered step, its check, and what to do if it fails."""

    action: str
    check: str
    if_it_fails: str
    quote: str
    grounded: bool


@dataclass(frozen=True)
class RunbookMaterial:
    """An execution runbook, or a note when the page has no procedure."""

    has_procedure: bool
    note: str
    steps: list[RunbookStep]
    checks: list[CheckedQuote]
    markdown: str


def write_runbook(request: StudyRequest, outline: str, complete: Completer) -> RunbookMaterial:
    """Write the runbook from the shared outline."""
    payload = complete_json(
        complete,
        instructions=runbook_instructions(),
        prompt=runbook_prompt(request, outline),
    )
    has_procedure = bool(payload.get("has_procedure"))
    note = str(payload.get("note", "")).strip()
    if not has_procedure:
        note = note or NO_PROCEDURE
    steps: list[RunbookStep] = []
    checks: list[CheckedQuote] = []
    for index, item in enumerate(object_list(payload, "steps"), start=1):
        checked = check_quote(f"runbook {index}", str(item.get("quote", "")), request.source_text)
        checks.append(checked)
        steps.append(
            RunbookStep(
                action=str(item.get("action", "")).strip(),
                check=str(item.get("check", "")).strip(),
                if_it_fails=str(item.get("if_it_fails", "")).strip(),
                quote=checked.quote,
                grounded=checked.grounded,
            )
        )
    fixed = repair_texts(
        [
            item
            for index, step in enumerate(steps)
            for item in (
                RepairItem(f"action-{index}", step.action, step.quote),
                RepairItem(f"check-{index}", step.check, step.quote),
                RepairItem(f"fails-{index}", step.if_it_fails, step.quote),
            )
        ],
        request.source_text,
        complete,
    )
    steps = [
        RunbookStep(
            fixed.get(f"action-{index}", step.action),
            fixed.get(f"check-{index}", step.check),
            fixed.get(f"fails-{index}", step.if_it_fails),
            step.quote,
            step.grounded,
        )
        for index, step in enumerate(steps)
    ]
    return RunbookMaterial(
        has_procedure,
        note,
        steps,
        checks,
        _markdown(has_procedure, note, steps, checks, request.source_text),
    )


def _markdown(
    has_procedure: bool,
    note: str,
    steps: list[RunbookStep],
    checks: list[CheckedQuote],
    source_text: str,
) -> str:
    lines = ["## Runbook"]
    if not has_procedure:
        lines.append(NO_PROCEDURE)
    if note and note != NO_PROCEDURE:
        lines.append(note)
    if not steps:
        lines.append("The source does not cover a runbook step.")
    for number, (step, checked) in enumerate(zip(steps, checks, strict=True), start=1):
        lines.extend(
            [
                f"{number}. {shown_sentence(step.action, checked.quote, source_text)}",
                f"   Check: {shown_sentence(step.check, checked.quote, source_text)}",
                f"   If it fails: {shown_sentence(step.if_it_fails, checked.quote, source_text)}",
            ]
        )
        line = quote_line(
            [step.action, step.check, step.if_it_fails],
            checked.quote,
            source_text,
        )
        if line:
            lines.append(f"   {line}")
    return "\n".join(lines)
