# Build 57 — Find the check

The picture is [57-find-check-diagram.png](57-find-check-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already names the latest check. This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, score, or check**. Typing **partial** keeps a pack that says **Last check: Partial**. Typing **incorrect** keeps a pack that says **Last check: Incorrect**. Typing **correct** leaves that incorrect pack off the search. A pack with no check line stays off a search for **partial**.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, and the score still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
