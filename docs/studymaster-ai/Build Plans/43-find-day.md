# Build 43 — Find the day

The picture is [43-find-day-diagram.png](43-find-day-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Find a study** already checks the title, the goal, the pieces, the minutes, and the site. This build also checks the saved day.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, or day**. Typing **October** keeps a pack whose line says **Saved October 25, 2026**. Typing **25** keeps a pack saved on the 25th. Typing **5** leaves that pack off the search.

The title, the goal, the pieces, the minutes, and the site still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
