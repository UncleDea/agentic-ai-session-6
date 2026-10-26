"""Score one learner reply against a hidden answer and a source excerpt."""

from dataclasses import dataclass

from studymaster.agents.client import Completer, OpenAIModelClient
from studymaster.agents.errors import EmptyReplyError, ModelResponseError
from studymaster.agents.parsing import read_model_json
from studymaster.config import Settings, get_settings
from studymaster.prompts.grade import grade_instructions, grade_prompt
from studymaster.storage.database import ATTEMPT_SCORES, QuizAttempt, StudyStore

SCORE_LABELS = {
    "correct": "Correct",
    "partial": "Partial",
    "incorrect": "Incorrect",
}


@dataclass(frozen=True)
class Grade:
    """One score and the single hint that goes with it."""

    score: str
    hint: str


def grade_reply(
    *,
    question: str,
    learner_answer: str,
    answer: str,
    excerpt: str,
    complete: Completer | None = None,
    settings: Settings | None = None,
) -> Grade:
    """Grade one reply. A blank reply never calls the model."""
    if not learner_answer.strip():
        raise EmptyReplyError("Write an answer before checking it.")
    caller = complete or OpenAIModelClient(settings or get_settings()).complete
    raw = caller(
        instructions=grade_instructions(),
        prompt=grade_prompt(
            question=question,
            learner_answer=learner_answer.strip(),
            answer=answer,
            excerpt=excerpt,
        ),
    )
    payload = read_model_json(raw)
    score = str(payload.get("score", "")).strip().lower()
    hint = str(payload.get("hint", "")).strip()
    if score not in ATTEMPT_SCORES or not hint:
        raise ModelResponseError("The grade reply was not readable JSON.")
    return Grade(score=score, hint=hint)


def record_attempt(
    *,
    store: StudyStore,
    resource_id: int,
    question: str,
    learner_answer: str,
    answer: str,
    excerpt: str,
    complete: Completer | None = None,
    settings: Settings | None = None,
) -> QuizAttempt:
    """Grade a reply and save the attempt. The answer itself is already stored."""
    grade = grade_reply(
        question=question,
        learner_answer=learner_answer,
        answer=answer,
        excerpt=excerpt,
        complete=complete,
        settings=settings,
    )
    return store.save_attempt(
        resource_id=resource_id,
        question=question,
        learner_answer=learner_answer.strip(),
        score=grade.score,
        hint=grade.hint,
    )
