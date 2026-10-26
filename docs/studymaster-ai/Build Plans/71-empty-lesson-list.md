# Build 71 — Empty lesson on the saved list

The picture is [71-empty-lesson-list-diagram.png](71-empty-lesson-list-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The open pack already says when a lesson came back empty. This build names that on the saved list.

## What this build does

Under the score, a saved study whose lesson came back empty says **The lesson came back empty.** The Entra pack says that. A pack with a lesson leaves that line off.

Showing the line reads this computer and does not call OpenAI.

## Left alone

**Find a study** still ignores that line. The open pack still says to press **Rewrite lesson**. The reader, agents, three sentence checks, catalog, and `.env` stay unchanged. The title stays **StudyMaster AI**.
