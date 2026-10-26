# Build 42 — Find the site

The picture is [42-find-site-diagram.png](42-find-site-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Find a study** already checks the title, the goal, the pieces, and the minutes. This build also checks the site line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, or site**. Typing **learn.microsoft.com** keeps a pack whose line says **Read from learn.microsoft.com**. A pasted lesson has no site line, so it stays off that search.

The title, the goal, the pieces, and the minutes still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
