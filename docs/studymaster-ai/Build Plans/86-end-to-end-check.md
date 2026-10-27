# Build 86 — End-to-end check

## What this build adds

One command walks the learner path with a fake page, then runs the test suite. A separate `--live` flag is the only way that command reads a real page and calls OpenAI.

## What the learner sees

Nothing on the study page changes. The check is a command in PowerShell.

## Decisions

- The plain command stays offline. It does not spend the API key.
- `--live` runs only after the offline journey and the full suite pass.
- The live pack is written in a temporary database, so the studies already on the page stay as they are.
- The command prints a short pass or fail line. It does not print the API key or the page text.
- The live path lives in `scripts/check_app.py`, outside `tests/`, so pytest does not collect it.

## Files

- `tests/test_end_to_end.py` holds the offline journey.
- `scripts/check_app.py` is the command.
- `README.md` shows both PowerShell commands.
