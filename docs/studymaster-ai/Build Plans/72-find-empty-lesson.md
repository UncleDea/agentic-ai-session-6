# Build 72 — Find the empty lesson

The picture is [72-find-empty-lesson-diagram.png](72-find-empty-lesson-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The saved list already says **The lesson came back empty.** This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, reply, left, or empty**. Typing **empty** keeps the Entra pack. The 15-minute pack, the 20-minute pack, and the identity pack stay off that search.

Typing **lesson** still keeps every pack, because that word is in **Study, lesson, lab, project, runbook**.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, the check, the progress, the question, the reply day, and the questions still waiting still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**. The open pack still says to press **Rewrite lesson**.
