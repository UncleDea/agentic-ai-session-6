# Build 25 — Repair one sentence

The picture is [25-repair-sentence-diagram.png](25-repair-sentence-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The three checks stay. A failed sentence gets one more try.

## What this build does

After a section is written, each sentence is checked the same way as before. If every sentence passes, the model is not called again. If any sentence fails, that section gets one repair call. The call includes the failed sentences, their quotes, and the page.

A replacement that passes the three checks is shown, with its Quote line. A replacement that fails stays off the page. The learner sees **The source does not cover this.**

The hidden lesson answer uses the same checks. If the answer still fails after that one repair, the question is not graded and the answer stays off the page.

## Left alone

The three checks, the catalog, Find a study, Start over, Delete, and the saved studies stay unchanged. The title stays **StudyMaster AI**.
