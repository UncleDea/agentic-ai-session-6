# Build 69 — Find the questions still waiting

The picture is [69-find-left-to-check-diagram.png](69-find-left-to-check-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already names how many questions are still waiting. This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, reply, or left**. Typing **left to check** keeps the 15-minute pack, the 20-minute pack, and the identity pack. Each of those says **Left to check:** followed by a number. The Entra pack has no questions, so it stays off that search.

Typing **5** also keeps the 20-minute pack, because that line says **5**. The 15-minute pack and the identity pack stay in that search too. The Entra pack stays off.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, the check, the progress, the question, and the reply day still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**. The open pack still leaves this line off.
