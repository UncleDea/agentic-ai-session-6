# Build 63 — Find the question

The picture is [63-find-question-diagram.png](63-find-question-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already names the latest question. This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, or question**. Typing **purpose** keeps the pack that says **Last question: What is the primary purpose of Data Loss Prevention?** A pack with no check yet stays off that search. Typing **prevention** still keeps both data loss prevention packs, because that word is in the title. An earlier question stays off the search.

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, the check, and the progress still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
