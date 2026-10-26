# Build 52 — Open fills the page link

The picture is [52-open-page-link-diagram.png](52-open-page-link-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Open study** already fills **Level**, **Goal**, and **Minutes**. This build also fills **Page link** when the pack was read from a public page.

## What this build does

Pressing **Open study** puts the saved public address in **Page link**. A Microsoft Learn pack fills the Learn address. A pasted lesson leaves **Page link** as it is, because those words were not read from a public address.

Opening a saved study reads this computer and does not call OpenAI. **Start over** still clears the page link.

## Left alone

The reader, agents, three sentence checks, catalog, finder, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
