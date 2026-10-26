# Build 16 — Paste the article text

The picture is [16-paste-article-diagram.png](16-paste-article-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The start guide is already in [README.md](../README.md). This build adds one box for a lesson you copied.

## What this build does

**Article text** sits under **Page link**. When that box holds a lesson, the study pack is written from those words. **Page link** is not opened, even if a private address is still in the box.

When **Article text** is empty, a catalog article or a typed link works as before. The title stays **StudyMaster AI**.

A lesson shorter than 400 characters stops with the same message as an unreadable page. The model is not called. A longer paste is saved under the marker `pasted-text`, which is never opened. Pressing **Study this page** again for the same words returns that saved pack.

## Left alone

The catalog, the reader rules for real links, the agents, history, the grader, and `.env` stay unchanged.
