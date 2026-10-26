# Build 60 — Find the progress

The picture is [60-find-progress-diagram.png](60-find-progress-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already names how many questions have a reply. This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, score, check, or progress**. Typing **checked** keeps every pack that shows that line. A pack with no questions stays off that search. Typing **1 of 6** keeps the pack that says **Checked 1 of 6.** Typing **1** leaves **Checked 0 of 12** off the search. Typing **12** keeps that pack.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, and the check still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
