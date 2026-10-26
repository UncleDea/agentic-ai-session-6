# Build 36 — Read from the site

The picture is [36-read-from-site-diagram.png](36-read-from-site-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). A finished pack already stores the page address. This build prints the site name under the title.

## What this build does

Under the pack title, a public page says **Read from learn.microsoft.com**. The same line appears when a saved pack is opened. The host comes from the stored address. The page is not read again, and OpenAI is not called.

A pasted lesson has no public site, so that line stays off. The downloaded Markdown stays the study text.

The line names the site the pack was read from. It does not decide whether the page is true.

## Left alone

The reader, agents, three sentence checks, catalog, finder, saved minutes, and `.env` stay unchanged. The title stays **StudyMaster AI**.
