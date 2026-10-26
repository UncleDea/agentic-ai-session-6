# Build 66 — Find the reply day

The picture is [66-find-reply-day-diagram.png](66-find-reply-day-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already names the day of the latest reply. This build lets **Find a study** read that line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, level, score, check, progress, question, or reply**. Typing **reply** keeps the pack that says **Reply day: October 25, 2026.** A pack with no check yet stays off that search. Typing **25** still keeps every pack, because that number is in **Saved October 25, 2026.**

The title, the goal, the pieces, the minutes, the site, the saved day, the level, the score, the check, the progress, and the question still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
