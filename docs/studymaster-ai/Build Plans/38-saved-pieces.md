# Build 38 — Saved pieces

The picture is [38-saved-pieces-diagram.png](38-saved-pieces-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already stores its sections. This build names those sections on the list.

## What this build does

Under the minutes, each saved study names the pieces it has. A short pack says **Study, lesson**. A full pack says **Study, lesson, lab, project, runbook**. The names follow the pack order.

A section that failed to save stays off that line. **Find a study** still matches the title and the goal. Showing the pieces reads the database on this computer. It does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, finder, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
