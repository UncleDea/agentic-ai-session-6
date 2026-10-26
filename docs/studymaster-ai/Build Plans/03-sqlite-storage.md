# Build 03 — SQLite storage

This plan covers the storage build only. It follows [01-studymaster-agent.md](01-studymaster-agent.md). The page reader from build 02 stays as it is. This build does not call OpenAI and does not add a URL box.

## What this build adds

A local SQLite database that can save a page, the five study artifacts, and a learner's quiz attempts. Later builds read this database. This build only proves the saving and reading work.

The code lives in `studymaster/storage/database.py`.

`DATABASE_PATH` is added to `studymaster/config.py` and `.env.example`. The default file is `data/studymaster.db`. Tests use a temporary file instead of that default. `*.db` is already ignored by `.gitignore`.

## Tables

`resources` stores one fetched page:

- url, content hash of the extracted text, fetched time
- title, status, error message, extracted text
- learner level, goal, and minutes

A failed fetch is saved with status `error`, the error message, and empty text.

`artifacts` stores one study section for a resource:

- resource id, kind, status, error message
- markdown body, model name, created time

The kind is one of `study`, `lesson`, `lab`, `project`, or `runbook`. Saving the same kind again replaces that section and leaves the other sections in place.

`quiz_attempts` stores one learner reply:

- resource id, question, learner answer, score, hint, created time

The score is `correct`, `partial`, or `incorrect`.

## Lookup

The same unchanged page, with the same level, goal, and minutes, can be found again. The match uses the url and a SHA-256 hash of the extracted text. A failed fetch is not offered as a saved success.

## Tests

`tests/test_storage.py` uses a temporary database. Required cases:

- A saved page can be read back with the same fields.
- A failed fetch is stored with the error and empty text.
- Five artifacts are stored, including one failed section.
- Replacing one artifact leaves the other four in place.
- A quiz attempt is stored and listed with its resource.
- The same page text is found again. Changed text is not found. A failed fetch is not returned as a success.

## How to verify

```powershell
cd C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai
.\.venv\Scripts\Activate.ps1
python -m pytest
```

Every storage test passes, and the page-reader tests from build 02 still pass. The home page still shows only **StudyMaster AI**.

## Left for later builds

The model client, the outline, the five study agents, the quote checker, the quiz grader, and the URL box are outside this build.
