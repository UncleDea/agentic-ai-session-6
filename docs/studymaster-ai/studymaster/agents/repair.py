"""Ask once for replacements of sentences that failed the three checks."""

import json
from dataclasses import dataclass

from studymaster.agents.client import Completer
from studymaster.agents.errors import AgentError
from studymaster.agents.parsing import complete_json
from studymaster.agents.quotes import sentence_is_supported
from studymaster.prompts.repair import repair_instructions, repair_prompt


@dataclass(frozen=True)
class RepairItem:
    """One sentence and the quote it must stay inside."""

    id: str
    text: str
    quote: str


def repair_texts(
    items: list[RepairItem],
    source_text: str,
    complete: Completer,
) -> dict[str, str]:
    """Return replacements that pass the same three checks.

    A section with no failed sentence makes no extra call. A replacement that
    still fails is left out of the result. A bad reply leaves the first draft.
    """
    by_id = {item.id: item for item in items}
    failed = [
        item
        for item in items
        if item.text.strip() and not sentence_is_supported(item.text, item.quote, source_text)
    ]
    if not failed:
        return {}
    body = json.dumps(
        [{"id": item.id, "text": item.text, "quote": item.quote} for item in failed],
        indent=2,
    )
    try:
        payload = complete_json(
            complete,
            instructions=repair_instructions(),
            prompt=repair_prompt(source_text, body),
        )
    except AgentError:
        return {}
    rows = payload.get("replacements", [])
    if not isinstance(rows, list):
        return {}
    fixed: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = by_id.get(str(row.get("id", "")))
        if item is None:
            continue
        text = str(row.get("text", "")).strip()
        if sentence_is_supported(text, item.quote, source_text):
            fixed[item.id] = text
    return fixed
