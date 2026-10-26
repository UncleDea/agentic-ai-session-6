# Build 29 — Empty lesson

The picture is [29-empty-lesson-diagram.png](29-empty-lesson-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). A lesson that comes back with no sections gets one more request.

## What this build does

The lesson is written as it is now. When that reply has no sections, the model is asked once more, with the same instructions plus a line that the lesson must include at least one section from the page.

A second reply that has sections is checked with the same three checks, and failed sentences still get the one repair call. A second reply that is still empty stays **The source does not cover a lesson.** A lesson that already has sections is not asked again.

A reply that is not JSON still uses the one JSON retry that is already built.

## Left alone

The three checks stay. The saved 20-minute data loss prevention pack stays, including its six questions. This build does not study that page again. The title stays **StudyMaster AI**.
