"""Save pages, study artifacts, and quiz attempts in SQLite.

The database file is local. Tests pass their own file path so they do not
write data/studymaster.db.
"""

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ARTIFACT_KINDS = ("study", "lesson", "lab", "project", "runbook")
ATTEMPT_SCORES = ("correct", "partial", "incorrect")
STATUS_OK = "ok"
STATUS_ERROR = "error"
LOCAL_LEARNER_ID = "local"


class StorageError(Exception):
    """The database rejected a save because a value was not allowed."""


@dataclass(frozen=True)
class Resource:
    """One fetched page."""

    id: int
    url: str
    content_hash: str
    fetched_at: str
    title: str
    status: str
    error_message: str
    extracted_text: str
    level: str
    goal: str
    minutes: int
    owner_id: str = LOCAL_LEARNER_ID


@dataclass(frozen=True)
class Artifact:
    """One study section for a page."""

    id: int
    resource_id: int
    kind: str
    status: str
    error_message: str
    markdown: str
    model_name: str
    created_at: str


@dataclass(frozen=True)
class QuizAttempt:
    """One learner reply to a question."""

    id: int
    resource_id: int
    question: str
    learner_answer: str
    score: str
    hint: str
    created_at: str


@dataclass(frozen=True)
class LessonCheck:
    """One hidden lesson question stored with its answer and source excerpt."""

    id: int
    resource_id: int
    position: int
    question: str
    answer: str
    excerpt: str


@dataclass(frozen=True)
class SavedStudy:
    """A successful page plus the sections saved for it."""

    resource: Resource
    artifacts: list[Artifact]


def content_hash(text: str) -> str:
    """Return the SHA-256 hash used to recognize an unchanged page."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StudyStore:
    """Read and write the local study database."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY,
                    url TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    extracted_text TEXT NOT NULL,
                    level TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    minutes INTEGER NOT NULL,
                    owner_id TEXT NOT NULL DEFAULT 'local'
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY,
                    resource_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (resource_id, kind),
                    FOREIGN KEY (resource_id) REFERENCES resources(id)
                );

                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id INTEGER PRIMARY KEY,
                    resource_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    learner_answer TEXT NOT NULL,
                    score TEXT NOT NULL,
                    hint TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (resource_id) REFERENCES resources(id)
                );

                CREATE TABLE IF NOT EXISTS lesson_checks (
                    id INTEGER PRIMARY KEY,
                    resource_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    UNIQUE (resource_id, position),
                    FOREIGN KEY (resource_id) REFERENCES resources(id)
                );

                CREATE TABLE IF NOT EXISTS learners (
                    owner_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL
                );
                """
            )
            self._ensure_owner_column(connection)

    def _ensure_owner_column(self, connection: sqlite3.Connection) -> None:
        """Add the learner id to a database created before this trial."""
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(resources)")
        }
        if "owner_id" in columns:
            return
        connection.execute(
            "ALTER TABLE resources ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local'"
        )

    def save_resource(
        self,
        *,
        url: str,
        title: str,
        status: str,
        error_message: str = "",
        extracted_text: str = "",
        level: str = "",
        goal: str = "",
        minutes: int = 0,
        owner_id: str = LOCAL_LEARNER_ID,
    ) -> Resource:
        """Insert one fetched page and return the saved row."""
        _require_status(status)
        if minutes < 0:
            raise StorageError("Minutes cannot be negative.")
        fetched_at = _now()
        digest = content_hash(extracted_text)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO resources (
                    url, content_hash, fetched_at, title, status,
                    error_message, extracted_text, level, goal, minutes,
                    owner_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    url,
                    digest,
                    fetched_at,
                    title,
                    status,
                    error_message,
                    extracted_text,
                    level,
                    goal,
                    minutes,
                    owner_id,
                ),
            )
            resource_id = int(cursor.lastrowid)
        return self.get_resource(resource_id)

    def create_learner(
        self,
        *,
        name: str,
        password: str,
        owner_id: str = LOCAL_LEARNER_ID,
    ) -> None:
        """Store one learner. The password is saved as a hash."""
        cleaned = name.strip()
        if not cleaned or not password:
            raise StorageError("Enter a name and a password.")
        salt = secrets.token_hex(16)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO learners (owner_id, name, salt, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (owner_id, cleaned, salt, _password_hash(password, salt)),
            )

    def has_learner(self) -> bool:
        """Return whether any login has been saved."""
        with self._connect() as connection:
            row = connection.execute("SELECT 1 FROM learners LIMIT 1").fetchone()
        return row is not None

    def authenticate(self, *, name: str, password: str) -> str | None:
        """Return the learner id when the name and password match."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT owner_id, salt, password_hash FROM learners WHERE name = ?",
                (name.strip(),),
            ).fetchone()
        if row is None:
            return None
        digest = _password_hash(password, str(row["salt"]))
        if not hmac.compare_digest(digest, str(row["password_hash"])):
            return None
        return str(row["owner_id"])

    def get_resource(self, resource_id: int) -> Resource:
        """Return one page by its id."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM resources WHERE id = ?",
                (resource_id,),
            ).fetchone()
        if row is None:
            raise StorageError(f"No saved page has id {resource_id}.")
        return _resource_from_row(row)

    def delete_resource(
        self,
        resource_id: int,
        *,
        owner_id: str = LOCAL_LEARNER_ID,
    ) -> None:
        """Remove one saved page and its sections, checks, and attempts."""
        resource = self.get_resource(resource_id)
        if resource.owner_id != owner_id:
            raise StorageError("This study belongs to another learner.")
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM quiz_attempts WHERE resource_id = ?",
                (resource_id,),
            )
            connection.execute(
                "DELETE FROM lesson_checks WHERE resource_id = ?",
                (resource_id,),
            )
            connection.execute(
                "DELETE FROM artifacts WHERE resource_id = ?",
                (resource_id,),
            )
            connection.execute(
                "DELETE FROM resources WHERE id = ?",
                (resource_id,),
            )

    def list_resources(self, *, owner_id: str | None = None) -> list[Resource]:
        """Return saved pages, newest first. An owner keeps the other learners off the list."""
        with self._connect() as connection:
            if owner_id is None:
                rows = connection.execute(
                    "SELECT * FROM resources ORDER BY fetched_at DESC, id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM resources
                    WHERE owner_id = ?
                    ORDER BY fetched_at DESC, id DESC
                    """,
                    (owner_id,),
                ).fetchall()
        return [_resource_from_row(row) for row in rows]

    def find_success(
        self,
        *,
        url: str,
        extracted_text: str,
        level: str,
        goal: str,
        minutes: int,
        owner_id: str = LOCAL_LEARNER_ID,
    ) -> SavedStudy | None:
        """Return the newest successful save of this same page and learner request."""
        digest = content_hash(extracted_text)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM resources
                WHERE url = ?
                  AND content_hash = ?
                  AND level = ?
                  AND goal = ?
                  AND minutes = ?
                  AND status = ?
                  AND owner_id = ?
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
                """,
                (url, digest, level, goal, minutes, STATUS_OK, owner_id),
            ).fetchone()
        if row is None:
            return None
        resource = _resource_from_row(row)
        return SavedStudy(resource=resource, artifacts=self.list_artifacts(resource.id))

    def save_artifact(
        self,
        *,
        resource_id: int,
        kind: str,
        status: str,
        error_message: str = "",
        markdown: str = "",
        model_name: str = "",
    ) -> Artifact:
        """Insert or replace one study section."""
        if kind not in ARTIFACT_KINDS:
            raise StorageError(f"Unknown study section: {kind}.")
        _require_status(status)
        self.get_resource(resource_id)
        created_at = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO artifacts (
                    resource_id, kind, status, error_message,
                    markdown, model_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (resource_id, kind) DO UPDATE SET
                    status = excluded.status,
                    error_message = excluded.error_message,
                    markdown = excluded.markdown,
                    model_name = excluded.model_name,
                    created_at = excluded.created_at
                """,
                (
                    resource_id,
                    kind,
                    status,
                    error_message,
                    markdown,
                    model_name,
                    created_at,
                ),
            )
            row = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE resource_id = ? AND kind = ?
                """,
                (resource_id, kind),
            ).fetchone()
        return _artifact_from_row(row)

    def list_artifacts(self, resource_id: int) -> list[Artifact]:
        """Return study sections for one page, in a stable kind order."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE resource_id = ?",
                (resource_id,),
            ).fetchall()
        artifacts = [_artifact_from_row(row) for row in rows]
        order = {kind: index for index, kind in enumerate(ARTIFACT_KINDS)}
        return sorted(artifacts, key=lambda artifact: order[artifact.kind])

    def save_attempt(
        self,
        *,
        resource_id: int,
        question: str,
        learner_answer: str,
        score: str,
        hint: str,
    ) -> QuizAttempt:
        """Insert one learner reply."""
        if score not in ATTEMPT_SCORES:
            raise StorageError(f"Unknown score: {score}.")
        self.get_resource(resource_id)
        created_at = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO quiz_attempts (
                    resource_id, question, learner_answer, score, hint, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (resource_id, question, learner_answer, score, hint, created_at),
            )
            attempt_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM quiz_attempts WHERE id = ?",
                (attempt_id,),
            ).fetchone()
        return _attempt_from_row(row)

    def replace_lesson_checks(
        self,
        resource_id: int,
        checks: list[tuple[str, str, str]],
    ) -> list[LessonCheck]:
        """Replace the hidden lesson questions stored for one page."""
        self.get_resource(resource_id)
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM lesson_checks WHERE resource_id = ?",
                (resource_id,),
            )
            for position, (question, answer, excerpt) in enumerate(checks, start=1):
                if not question.strip():
                    continue
                connection.execute(
                    """
                    INSERT INTO lesson_checks (
                        resource_id, position, question, answer, excerpt
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (resource_id, position, question.strip(), answer.strip(), excerpt.strip()),
                )
        return self.list_lesson_checks(resource_id)

    def list_lesson_checks(self, resource_id: int) -> list[LessonCheck]:
        """Return hidden lesson questions for one page, in source order."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM lesson_checks
                WHERE resource_id = ?
                ORDER BY position ASC, id ASC
                """,
                (resource_id,),
            ).fetchall()
        return [_lesson_check_from_row(row) for row in rows]

    def list_attempts(self, resource_id: int) -> list[QuizAttempt]:
        """Return replies for one page, oldest first."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM quiz_attempts
                WHERE resource_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (resource_id,),
            ).fetchall()
        return [_attempt_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _password_hash(password: str, salt: str) -> str:
    """Return the stored hash for one password. The plain password is not kept."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120_000,
    )
    return digest.hex()


def _require_status(status: str) -> None:
    if status not in {STATUS_OK, STATUS_ERROR}:
        raise StorageError(f"Unknown status: {status}.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resource_from_row(row: sqlite3.Row) -> Resource:
    return Resource(
        id=row["id"],
        url=row["url"],
        content_hash=row["content_hash"],
        fetched_at=row["fetched_at"],
        title=row["title"],
        status=row["status"],
        error_message=row["error_message"],
        extracted_text=row["extracted_text"],
        level=row["level"],
        goal=row["goal"],
        minutes=row["minutes"],
        owner_id=row["owner_id"],
    )


def _artifact_from_row(row: sqlite3.Row) -> Artifact:
    return Artifact(
        id=row["id"],
        resource_id=row["resource_id"],
        kind=row["kind"],
        status=row["status"],
        error_message=row["error_message"],
        markdown=row["markdown"],
        model_name=row["model_name"],
        created_at=row["created_at"],
    )


def _lesson_check_from_row(row: sqlite3.Row) -> LessonCheck:
    return LessonCheck(
        id=row["id"],
        resource_id=row["resource_id"],
        position=row["position"],
        question=row["question"],
        answer=row["answer"],
        excerpt=row["excerpt"],
    )


def _attempt_from_row(row: sqlite3.Row) -> QuizAttempt:
    return QuizAttempt(
        id=row["id"],
        resource_id=row["resource_id"],
        question=row["question"],
        learner_answer=row["learner_answer"],
        score=row["score"],
        hint=row["hint"],
        created_at=row["created_at"],
    )
