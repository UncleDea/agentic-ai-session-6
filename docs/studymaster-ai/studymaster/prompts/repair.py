"""Prompt for the one repair call after a section is written."""

from studymaster.prompts.common import SOURCE_RULE

REPAIR_MARK = "Repair these sentences."


def repair_instructions() -> str:
    """Return the standing instruction for a repair."""
    return (
        f"{SOURCE_RULE} {REPAIR_MARK} Return JSON with key replacements, "
        "a list of objects with id and text. Copy nothing from outside the source."
    )


def repair_prompt(source_text: str, failed_json: str) -> str:
    """Return the repair prompt for the sentences that failed the three checks."""
    return (
        f"{REPAIR_MARK} Replace only the failed sentences. Each replacement must "
        "stay inside its quote and the source.\n\n"
        f"Source:\n{source_text}\n\n"
        f"Failed sentences:\n{failed_json}"
    )
