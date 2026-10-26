# Build 61 — Open progress

The picture is [61-open-progress-diagram.png](61-open-progress-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The saved list already says **Checked 1 of 6.** This build shows that same line on the open pack.

## What this build does

Under the latest check, the open pack names how many questions have a reply. The 20-minute pack says **Checked 1 of 6.** A second reply to that same question still counts as one. A pack with questions and no reply yet still shows the line, such as **Checked 0 of 12.** A pack with no questions leaves the line off.

Opening a saved study reads this computer and does not call OpenAI. The download stays the study text.

## Left alone

The reader, agents, three sentence checks, catalog, finder, and `.env` stay unchanged. The title stays **StudyMaster AI**.
