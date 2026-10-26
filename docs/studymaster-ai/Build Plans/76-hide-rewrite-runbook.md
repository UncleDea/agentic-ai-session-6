# Build 76 — Hide Rewrite runbook

The picture is [76-hide-rewrite-runbook-diagram.png](76-hide-rewrite-runbook-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Each saved study already says **This page has no procedure.** That note is the normal result. This build leaves off the button that would ask for the runbook again.

## What this build does

Open any of the four packs. The buttons that remain are **Rewrite study**, **Rewrite lesson**, **Rewrite lab**, and **Rewrite project**. **Rewrite runbook** is not there. A pack whose runbook has steps still shows **Rewrite runbook**.

Opening the pack reads this computer and does not call OpenAI. The hidden button is the one that would call OpenAI.

## Left alone

The reader, agents, three sentence checks, catalog, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
