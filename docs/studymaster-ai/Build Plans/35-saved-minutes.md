# Build 35 — Saved minutes

The picture is [35-saved-minutes-diagram.png](35-saved-minutes-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already stores its minutes. This build shows that number on the list.

## What this build does

Under each saved title, the goal line stays. The next line says **15 minutes** or **20 minutes**. One minute says **1 minute**. The saved day stays on the line under that.

Two studies with the same title and the same day can be told apart by the minutes. **Find a study** still matches the title and the goal. **Open study** and **Delete** stay on each row. Showing the minutes does not call OpenAI.

## Left alone

The reader, agents, catalog, finder, sentence check, and `.env` stay unchanged. The title stays **StudyMaster AI**.
