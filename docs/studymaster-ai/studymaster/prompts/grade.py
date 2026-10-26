"""Prompt for the grader."""

from studymaster.prompts.common import SOURCE_RULE


def grade_instructions() -> str:
    """Return the standing instruction for scoring one reply."""
    return (
        f"{SOURCE_RULE} You are grading a learner reply. Return JSON with "
        "keys score and hint. score must be correct, partial, or incorrect. "
        "hint is one sentence that helps the learner try again. Do not copy "
        "the hidden answer into the hint."
    )


def grade_prompt(
    *,
    question: str,
    learner_answer: str,
    answer: str,
    excerpt: str,
) -> str:
    """Return the grading prompt. The excerpt is the only source."""
    return (
        "Compare the learner reply with the hidden answer and the source "
        "excerpt. Use only this source.\n\n"
        f"Question:\n{question}\n\n"
        f"Hidden answer:\n{answer}\n\n"
        f"Source excerpt:\n{excerpt}\n\n"
        f"Learner reply:\n{learner_answer}"
    )
