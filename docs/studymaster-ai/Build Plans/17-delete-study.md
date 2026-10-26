# Build 17 — Delete a saved study

The picture is [17-delete-study-diagram.png](17-delete-study-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Saved studies can already be opened. This build adds a way to remove one pack from this computer.

## What this build does

Each saved study has **Open study** and **Delete** on one row. The first press changes the button to **Delete this study?** and leaves the pack in place. The second press removes that pack, including its sections, lesson checks, and quiz attempts.

If that pack is the one open on the page, the page clears it. Another open pack stays. Neither press calls OpenAI.

## Left alone

The reader, agents, catalog, grader, and `.env` stay unchanged. **Open study**, **Rewrite**, and **Download Markdown** stay as they are.
