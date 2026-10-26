# Build 39 — Find the pieces

The picture is [39-find-pieces-diagram.png](39-find-pieces-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Find a study** already checks the title and the goal. This build also checks the pieces line.

## What this build does

The placeholder says **Type part of a title, goal, or pieces**. Typing **runbook** keeps a pack whose pieces line says **Study, lesson, lab, project, runbook**. A pack that says **Study, lesson** stays off that search.

The title and the goal still count. An empty box still shows every saved study. Capital letters and extra spaces do not matter. The search reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
