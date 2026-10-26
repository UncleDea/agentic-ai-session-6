# Build 56 — Saved check

The picture is [56-saved-check-diagram.png](56-saved-check-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). An open pack already shows **Correct**, **Partial**, or **Incorrect** after **Check my answer**. This build shows the latest of those words on the saved list.

## What this build does

Under the score, a saved study names the latest check. A pack whose newest reply was partial says **Last check: Partial**. An earlier incorrect reply stays off that line. A pack with no check yet leaves the line off. The hint and the reply stay off the list.

Showing the line reads this computer and does not call OpenAI.

## Left alone

**Find a study** still matches the title, goal, pieces, minutes, site, day, level, and score. The reader, agents, three sentence checks, catalog, and `.env` stay unchanged. The title stays **StudyMaster AI**.
