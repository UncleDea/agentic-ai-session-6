# Build 51 — Open fills the form

The picture is [51-open-fills-form-diagram.png](51-open-fills-form-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The open pack already names the level, the goal, and the minutes. The boxes above can still show different values. This build copies the saved values into those boxes.

## What this build does

Pressing **Open study** fills **Level**, **Goal**, and **Minutes** from that pack. An intermediate pack sets **Level** to **Intermediate**, **Goal** to the saved goal, and **Minutes** to the saved number. **Page link** stays as it is.

Opening a saved study reads this computer and does not call OpenAI. **Start over** still sets the boxes back to **Beginner**, an empty goal, and **20**.

## Left alone

The reader, agents, three sentence checks, catalog, finder, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
