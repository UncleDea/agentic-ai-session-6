# Build 58 — Open check

The picture is [58-open-check-diagram.png](58-open-check-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The saved list already says **Last check: Partial**. This build shows that same line on the open pack.

## What this build does

Under the score, the open pack names the latest check. A pack whose newest reply was partial says **Last check: Partial**. An earlier incorrect reply stays off that line. A pack with no check yet leaves the line off.

Opening a saved study reads this computer and does not call OpenAI. The download stays the study text.

## Left alone

The reader, agents, three sentence checks, catalog, finder, and `.env` stay unchanged. The title stays **StudyMaster AI**.
