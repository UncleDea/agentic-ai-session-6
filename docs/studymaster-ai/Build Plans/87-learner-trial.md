# Build 87 — Learner trial

## What this build adds

A side branch tries four pieces, one at a time. Each piece is tested and confirmed before the next one starts. The local app on master stays the one that is maintained.

## What the learner sees

Nothing on the master page changes. The trial uses a copy of the study database.

## Decisions

- The branch is `trial/learner-account`. The copy is `data/trial-studymaster.db`.
- The real study database and `.env` stay unchanged.
- The order is the copied database, a learner id, a local login, then waiting questions. A public page starts only after a separate yes.
- A wrong password shows no packs. Waiting questions do not call OpenAI.
- The public test can be deleted. A local piece moves to master only when that is requested.

## Files

- `data/trial-studymaster.db` is the copied database. It is not committed.
- Later pieces change the trial branch only.
