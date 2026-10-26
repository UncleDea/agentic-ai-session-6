# Build 40 — Find the minutes

The picture is [40-find-minutes-diagram.png](40-find-minutes-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Find a study** already checks the title, the goal, and the pieces line. This build also checks the minutes line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, or minutes**. Typing **15** keeps a pack whose line says **15 minutes**. Typing **20** keeps a pack whose line says **20 minutes**. Typing **5** keeps **5 minutes** and leaves **15 minutes** off that search.

The title, the goal, and the pieces line still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
