"""Write a practical lab, or say when the page has no procedure."""

from dataclasses import dataclass

from studymaster.agents.client import Completer
from studymaster.agents.parsing import complete_json, object_list
from studymaster.agents.quotes import CheckedQuote, check_quote, quote_line, shown_sentence
from studymaster.agents.repair import RepairItem, repair_texts
from studymaster.agents.request import StudyRequest
from studymaster.prompts.lab import lab_instructions, lab_prompt

NO_PROCEDURE = "This source does not describe a procedure."


@dataclass(frozen=True)
class LabTask:
    """One lab task and the result the learner should see."""

    instruction: str
    expected_result: str
    quote: str
    grounded: bool


@dataclass(frozen=True)
class LabMaterial:
    """A practical lab, or a concept exercise when the page has no procedure."""

    has_procedure: bool
    note: str
    tasks: list[LabTask]
    checks: list[CheckedQuote]
    markdown: str


def write_lab(request: StudyRequest, outline: str, complete: Completer) -> LabMaterial:
    """Write the lab from the shared outline."""
    payload = complete_json(
        complete,
        instructions=lab_instructions(),
        prompt=lab_prompt(request, outline),
    )
    has_procedure = bool(payload.get("has_procedure"))
    note = str(payload.get("note", "")).strip()
    if not has_procedure:
        note = note or NO_PROCEDURE
    tasks: list[LabTask] = []
    checks: list[CheckedQuote] = []
    for index, item in enumerate(object_list(payload, "tasks"), start=1):
        checked = check_quote(f"lab {index}", str(item.get("quote", "")), request.source_text)
        checks.append(checked)
        tasks.append(
            LabTask(
                instruction=str(item.get("instruction", "")).strip(),
                expected_result=str(item.get("expected_result", "")).strip(),
                quote=checked.quote,
                grounded=checked.grounded,
            )
        )
    fixed = repair_texts(
        [
            item
            for index, task in enumerate(tasks)
            for item in (
                RepairItem(f"instruction-{index}", task.instruction, task.quote),
                RepairItem(f"result-{index}", task.expected_result, task.quote),
            )
        ],
        request.source_text,
        complete,
    )
    tasks = [
        LabTask(
            fixed.get(f"instruction-{index}", task.instruction),
            fixed.get(f"result-{index}", task.expected_result),
            task.quote,
            task.grounded,
        )
        for index, task in enumerate(tasks)
    ]
    return LabMaterial(
        has_procedure,
        note,
        tasks,
        checks,
        _markdown(has_procedure, note, tasks, checks, request.source_text),
    )


def _markdown(
    has_procedure: bool,
    note: str,
    tasks: list[LabTask],
    checks: list[CheckedQuote],
    source_text: str,
) -> str:
    lines = ["## Lab"]
    if not has_procedure:
        lines.append(NO_PROCEDURE)
    if note and note != NO_PROCEDURE:
        lines.append(note)
    if not tasks:
        lines.append("The source does not cover a lab task.")
    for task, checked in zip(tasks, checks, strict=True):
        lines.extend(
            [
                f"- {shown_sentence(task.instruction, checked.quote, source_text)}",
                f"  Expected result: {shown_sentence(task.expected_result, checked.quote, source_text)}",
            ]
        )
        line = quote_line(
            [task.instruction, task.expected_result],
            checked.quote,
            source_text,
        )
        if line:
            lines.append(f"  {line}")
    return "\n".join(lines)
