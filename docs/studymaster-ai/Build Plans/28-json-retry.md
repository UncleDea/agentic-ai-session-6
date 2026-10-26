# Build 28 — JSON retry

The picture is [28-json-retry-diagram.png](28-json-retry-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). A section that replies with ordinary text gets one more chance to reply with JSON.

## What this build does

When a section reply is not JSON, the model is called once more with the same instructions plus a line that the reply must be JSON only. A readable second reply is used. A second bad reply marks only that section as an error. The other sections stay.

## Left alone

The repair call, the shortened-page line, the pack score, and the three checks stay as they are. The title stays **StudyMaster AI**.
