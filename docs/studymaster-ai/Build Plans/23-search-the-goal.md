# Build 23 — Search the goal line

The picture is [23-search-the-goal-diagram.png](23-search-the-goal-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Find a study** already keeps a title that contains the words you type. This build also checks the goal line under that title.

## What this build does

The placeholder becomes **Type part of a title or goal**. An empty box still shows every saved study. Typing keeps a study when those letters appear in the title or in the goal line. Capital letters and extra spaces do not matter. **master** keeps **Get Started with Identity Architecture Design**, because the line under it says **master the material**.

**Open study** and **Delete** stay on each study that is still listed. When nothing matches, the page still says **No saved study matches that.** The box does not call OpenAI.

## Left alone

The reader, agents, catalog, sentence check, Start over, progress box, grader, and `.env` stay unchanged. The title stays **StudyMaster AI**.
