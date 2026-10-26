# Build 53 — Open fills the article

The picture is [53-open-article-diagram.png](53-open-article-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). **Open study** already fills the form for a public page. This build fills **Article text** when the pack was pasted.

## What this build does

Pressing **Open study** on a pasted lesson puts the saved words in **Article text**. **Page link** stays as it is.

A public page leaves **Article text** empty. A filled box is the lesson, so those words would replace the page link.

Opening a saved study reads this computer and does not call OpenAI. **Start over** still clears **Article text**.

## Left alone

The reader, agents, three sentence checks, catalog, finder, pack size, and `.env` stay unchanged. The title stays **StudyMaster AI**.
