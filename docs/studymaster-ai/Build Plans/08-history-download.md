# Build 08 — History, rewrite, and download

The picture is [08-history-download-diagram.png](08-history-download-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The home page and the grader are already built.

## What this build adds

Saved studies appear in a list, newest first. Opening one reads SQLite and shows that pack. It does not download the page again and it does not call the model.

Each section has a button that rewrites only that section from the saved page text. The other sections stay as they are. A failed rewrite marks that section and leaves the rest in place.

The learner can download the pack as one Markdown file. The file is the text already on the page. Lesson answers stay out of the file. The download does not call the model.

## Left for later

The 37 LinkedIn posts stay a reference list until each technical post has a Microsoft Learn URL.
