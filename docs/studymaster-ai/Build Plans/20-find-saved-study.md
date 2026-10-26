# Build 20 — Find a saved study

The picture is [20-find-saved-study-diagram.png](20-find-saved-study-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Saved studies are already listed, newest first. This build adds a box that keeps only the titles that match what you type.

## What this build does

Under **Saved studies**, a box labeled **Find a study** sits above the list. The placeholder says **Type part of a title**.

An empty box shows every saved study. Typing keeps a study when those letters appear in its title. Capital letters and extra spaces do not matter. **Entra** keeps **What is Microsoft Entra?**

**Open study** and **Delete** stay on each study that is still listed. The first Delete press still asks **Delete this study?** The second press still removes only that pack. Opening a study still reads the saved pack on this computer.

When nothing matches, the page says **No saved study matches that.** The open pack above the list stays where it is. The box does not call OpenAI.

## Left alone

The reader, agents, catalog, sentence check, progress box, grader, and `.env` stay unchanged. The title stays **StudyMaster AI**.
