# Build 68 — Left to check

The picture is [68-left-to-check-diagram.png](68-left-to-check-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). A saved study already says how many questions have a reply. This build names how many are still waiting.

## What this build does

Under the reply day, or under the progress line when there is no reply yet, a saved study names the questions still waiting. The 20-minute pack says **Left to check: 5.** The 15-minute pack also says **Left to check: 5.**, because none of its five questions have a reply. The identity pack says **Left to check: 12.** A pack whose questions all have a reply says **Left to check: 0.** A pack with no questions leaves the line off.

Showing the line reads this computer and does not call OpenAI.

## Left alone

**Find a study** still ignores that line. The reader, agents, three sentence checks, catalog, and `.env` stay unchanged. The title stays **StudyMaster AI**.
