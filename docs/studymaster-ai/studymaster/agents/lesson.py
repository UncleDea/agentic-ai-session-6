"""Write a guided lesson and keep the check answers hidden in the text."""

from dataclasses import dataclass

from studymaster.agents.client import Completer
from studymaster.agents.parsing import complete_json, object_list
from studymaster.agents.repair import RepairItem, repair_texts
from studymaster.agents.quotes import (
    COVER,
    CheckedQuote,
    check_quote,
    quote_line,
    sentence_is_supported,
    shown_sentence,
)
from studymaster.agents.request import StudyRequest
from studymaster.prompts.lesson import EMPTY_LESSON_LINE, lesson_instructions, lesson_prompt


@dataclass(frozen=True)
class LessonSection:
    """One lesson section. The answer is stored here and left out of the text."""

    title: str
    teach: str
    example: str
    check_question: str
    answer: str
    quote: str
    grounded: bool


@dataclass(frozen=True)
class LessonMaterial:
    """A guided lesson in source order."""

    sections: list[LessonSection]
    checks: list[CheckedQuote]
    markdown: str


def write_lesson(request: StudyRequest, outline: str, complete: Completer) -> LessonMaterial:
    """Write the lesson from the shared outline."""
    instructions = lesson_instructions()
    prompt = lesson_prompt(request, outline)
    payload = complete_json(complete, instructions=instructions, prompt=prompt)
    if not object_list(payload, "sections"):
        payload = complete_json(
            complete,
            instructions=instructions,
            prompt=f"{prompt}\n\n{EMPTY_LESSON_LINE}",
        )
    sections: list[LessonSection] = []
    checks: list[CheckedQuote] = []
    for index, item in enumerate(object_list(payload, "sections"), start=1):
        checked = check_quote(f"lesson {index}", str(item.get("quote", "")), request.source_text)
        checks.append(checked)
        sections.append(
            LessonSection(
                title=str(item.get("title", "")).strip(),
                teach=str(item.get("teach", "")).strip(),
                example=str(item.get("example", "")).strip(),
                check_question=str(item.get("check_question", "")).strip(),
                answer=str(item.get("answer", "")).strip(),
                quote=checked.quote,
                grounded=checked.grounded,
            )
        )
    sections = _repaired_sections(sections, request.source_text, complete)
    return LessonMaterial(sections, checks, _markdown(sections, checks, request.source_text))


def _repaired_sections(
    sections: list[LessonSection],
    source_text: str,
    complete: Completer,
) -> list[LessonSection]:
    """Repair failed sentences once, then hide a question whose answer still fails."""
    items: list[RepairItem] = []
    for index, section in enumerate(sections):
        items.extend(
            [
                RepairItem(f"{index}-teach", section.teach, section.quote),
                RepairItem(f"{index}-example", section.example, section.quote),
                RepairItem(f"{index}-question", section.check_question, section.quote),
                RepairItem(f"{index}-answer", section.answer, section.quote),
            ]
        )
    fixed = repair_texts(items, source_text, complete)
    updated: list[LessonSection] = []
    for index, section in enumerate(sections):
        teach = fixed.get(f"{index}-teach", section.teach)
        example = fixed.get(f"{index}-example", section.example)
        question = fixed.get(f"{index}-question", section.check_question)
        answer = fixed.get(f"{index}-answer", section.answer)
        if not _can_grade(question, answer, section.quote, source_text):
            question = ""
        updated.append(
            LessonSection(
                section.title,
                teach,
                example,
                question,
                answer,
                section.quote,
                section.grounded,
            )
        )
    return updated


def _can_grade(question: str, answer: str, quote: str, source_text: str) -> bool:
    """A question is graded only when the question and the hidden answer both pass."""
    if not question.strip() or not answer.strip():
        return False
    return sentence_is_supported(question, quote, source_text) and sentence_is_supported(
        answer, quote, source_text
    )


def _markdown(
    sections: list[LessonSection],
    checks: list[CheckedQuote],
    source_text: str,
) -> str:
    lines = ["## Lesson"]
    if not sections:
        lines.append("The source does not cover a lesson.")
    for section, checked in zip(sections, checks, strict=True):
        question = section.check_question or COVER
        lines.extend(
            [
                f"### {section.title}",
                shown_sentence(section.teach, checked.quote, source_text),
                f"Example: {shown_sentence(section.example, checked.quote, source_text)}",
                f"Check question: {question}",
            ]
        )
        line = quote_line(
            [section.teach, section.example, section.check_question],
            checked.quote,
            source_text,
        )
        if line:
            lines.append(line)
    return "\n".join(lines)
