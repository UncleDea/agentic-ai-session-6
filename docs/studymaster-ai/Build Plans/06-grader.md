# Build 06 — Grader

The picture is [06-grader-diagram.png](06-grader-diagram.png). Click that file to see the drawing.

This plan is for the grader. No code for this build is written yet. It follows [01-studymaster-agent.md](01-studymaster-agent.md).

## What this build will add

The learner sees a lesson question with the answer hidden. After they submit a reply, the grader compares it with the hidden answer and the source excerpt. The score is correct, partial, or incorrect, plus one hint. The attempt is saved in SQLite.

Opening a saved page, showing an answer, or downloading the pack reads SQLite and does not call the model.
