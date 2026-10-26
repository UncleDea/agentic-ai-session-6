# Build 37 — Pack size

The picture is [37-pack-size-diagram.png](37-pack-size-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). Minutes are already saved and sent to the model. This build lets those minutes choose how many sections a new pack writes.

## What this build does

Up to 10 minutes, a new pack keeps the outline, the study, and the lesson. More than 10 minutes also keeps the lab, the project, and the runbook. The line under **Minutes** says that rule.

A saved pack stays the size it was saved. Opening it does not write new sections. **Study this page** is still the button that reads a page.

## Left alone

The reader, three sentence checks, catalog, finder, saved minutes, site name, and `.env` stay unchanged. The title stays **StudyMaster AI**.
