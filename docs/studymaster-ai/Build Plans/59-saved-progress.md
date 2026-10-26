# Build 59 — Saved progress

The picture is [59-saved-progress-diagram.png](59-saved-progress-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). A saved study already names the latest check. This build names how many questions have a reply.

## What this build does

Under the latest check, each saved study names the progress. A pack with six questions and one reply says **Checked 1 of 6.** A second reply to that same question still counts as one. A pack with twelve questions and no reply says **Checked 0 of 12.** A pack with no questions leaves the line off.

Showing the line reads this computer and does not call OpenAI.

## Left alone

**Find a study** still matches the title, goal, pieces, minutes, site, day, level, score, and check. The reader, agents, three sentence checks, catalog, and `.env` stay unchanged. The title stays **StudyMaster AI**.
