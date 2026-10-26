"""Write a small professional project from the page."""

from dataclasses import dataclass

from studymaster.agents.client import Completer
from studymaster.agents.errors import ModelResponseError
from studymaster.agents.parsing import complete_json
from studymaster.agents.quotes import CheckedQuote, check_quote, quote_line, shown_sentence
from studymaster.agents.repair import RepairItem, repair_texts
from studymaster.agents.request import StudyRequest
from studymaster.prompts.project import project_instructions, project_prompt


@dataclass(frozen=True)
class ProjectMaterial:
    """A project brief grounded in the source."""

    goal: str
    deliverable: str
    milestones: list[str]
    done_when: str
    checks: list[CheckedQuote]
    markdown: str


def write_project(request: StudyRequest, outline: str, complete: Completer) -> ProjectMaterial:
    """Write the project from the shared outline."""
    payload = complete_json(
        complete,
        instructions=project_instructions(),
        prompt=project_prompt(request, outline),
    )
    raw_milestones = payload.get("milestones", [])
    if not isinstance(raw_milestones, list):
        raise ModelResponseError("The model reply was not readable JSON.")
    milestones = [str(item).strip() for item in raw_milestones]
    checked = check_quote("project", str(payload.get("quote", "")), request.source_text)
    goal = str(payload.get("goal", "")).strip()
    deliverable = str(payload.get("deliverable", "")).strip()
    done_when = str(payload.get("done_when", "")).strip()
    fixed = repair_texts(
        [
            RepairItem("goal", goal, checked.quote),
            RepairItem("deliverable", deliverable, checked.quote),
            RepairItem("done", done_when, checked.quote),
            *[
                RepairItem(f"milestone-{index}", milestone, checked.quote)
                for index, milestone in enumerate(milestones)
            ],
        ],
        request.source_text,
        complete,
    )
    material = ProjectMaterial(
        goal=fixed.get("goal", goal),
        deliverable=fixed.get("deliverable", deliverable),
        milestones=[
            fixed.get(f"milestone-{index}", milestone)
            for index, milestone in enumerate(milestones)
        ],
        done_when=fixed.get("done", done_when),
        checks=[checked],
        markdown="",
    )
    return ProjectMaterial(
        material.goal,
        material.deliverable,
        material.milestones,
        material.done_when,
        material.checks,
        _markdown(material, checked, request.source_text),
    )


def _markdown(material: ProjectMaterial, checked: CheckedQuote, source_text: str) -> str:
    quote = checked.quote
    lines = [
        "## Project",
        f"Goal: {shown_sentence(material.goal, quote, source_text)}",
        f"Deliverable: {shown_sentence(material.deliverable, quote, source_text)}",
        "Milestones:",
    ]
    if not material.milestones:
        lines.append("- The source does not cover milestones.")
    for milestone in material.milestones:
        lines.append(f"- {shown_sentence(milestone, quote, source_text)}")
    lines.append(f"Done when: {shown_sentence(material.done_when, quote, source_text)}")
    line = quote_line(
        [material.goal, material.deliverable, *material.milestones, material.done_when],
        quote,
        source_text,
    )
    if line:
        lines.append(line)
    return "\n".join(lines)
