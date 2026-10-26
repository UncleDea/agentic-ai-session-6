# Build 83 — Word download

The picture is [83-word-download-diagram.png](83-word-download-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The pack downloads as Markdown. This build also saves that same pack as a Word file.

## What this build does

**Download Word** saves the outline, study, lesson, lab, project, and runbook as a `.docx` file. Microsoft Word opens that file. **Download Markdown** stays. Lesson answers stay out of both files.

Saving the Word file reads this computer and does not call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
