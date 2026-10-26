# Build 55 — Find the score

The picture is [55-find-score-diagram.png](55-find-score-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already names its score. This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, or score**. Typing **left out** keeps every pack that shows that line. Typing **5** keeps a pack whose score says **Questions to check: 5.** A pack saved for **5 minutes** still matches the minutes line. Typing **5** leaves **15 minutes**, **77**, and **12** off that search. Typing **12** keeps the pack whose score says **12**. Typing **77** keeps the pack whose score says **77**.

The title, the goal, the pieces, the minutes, the site, the saved day, and the level still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
