# Build 05 — Specialist agents

The picture is [05-specialist-agents-diagram.png](05-specialist-agents-diagram.png). Click that file to see the drawing.

This plan is for the build after the study agent. No code for this build is written yet. It follows [01-studymaster-agent.md](01-studymaster-agent.md).

## What this build will add

A Python coordinator and four new model agents: lesson, lab, project, and runbook. The coordinator also runs the study agent from build 04.

Each agent receives the page text, the shared outline, and the learner's level, goal, and minutes. The quote checker from build 04 runs on every section. One failed agent leaves the other sections in place.

The lab and the runbook say so when the page has no procedure.

## Left for later

The quiz grader and the URL box are outside this build.
