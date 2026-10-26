# Build 74 — Find the empty runbook

The picture is [74-find-empty-runbook-diagram.png](74-find-empty-runbook-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already says **The runbook came back empty.** This build lets **Find a study** read that line.

## What this build does

The placeholder already ends with **or empty**. Typing **empty** keeps all four packs, because each one says **The runbook came back empty.** A pack whose runbook has steps stays off that search.

Typing **runbook** still keeps every pack, because that word is already in **Study, lesson, lab, project, runbook**.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, the check, the progress, the question, the reply day, the questions still waiting, and the empty lesson still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
