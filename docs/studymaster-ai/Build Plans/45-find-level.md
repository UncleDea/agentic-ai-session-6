# Build 45 — Find the level

The picture is [45-find-level-diagram.png](45-find-level-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Find a study** already checks the title, the goal, the pieces, the minutes, the site, and the saved day. This build also checks the level line.

## What this build does

The placeholder says **Type part of a title, goal, pieces, minutes, site, day, or level**. Typing **beginner** keeps a pack whose line says **For a beginner**. Typing **intermediate** keeps a pack whose line says **For an intermediate learner**. Typing **advanced** leaves a beginner pack off that search.

The title, the goal, the pieces, the minutes, the site, and the saved day still count. An empty box still shows every saved study. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
