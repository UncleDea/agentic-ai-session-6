# Build 78 — Find the uncovered project

The picture is [78-find-uncovered-project-diagram.png](78-find-uncovered-project-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The 15-minute pack and the 20-minute pack already say **The project is not covered by this page.** This build lets **Find a study** read that line.

## What this build does

Typing **covered** keeps the 15-minute pack and the 20-minute pack. The Entra pack and the identity pack stay off that search. Typing **project** still keeps every pack, because that word is already in **Study, lesson, lab, project, runbook**.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, the check, the progress, the question, the reply day, the questions still waiting, the empty lesson, and the no-procedure line still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**. The download stays the study text.
