# Build 27 — Pack score

The picture is [27-pack-score-diagram.png](27-pack-score-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The score is counted from the pack already on the screen.

## What this build does

Under the pack title, the page says **Left out N sentences.** and **Questions to check: M.** Left out means the line **The source does not cover this.** Questions means lesson checks that still have a question.

Older saved studies get the same lines. Counting them does not call OpenAI. The same two numbers are written to the log when a new pack is created.

## Left alone

The three checks stay. Level, goal, and minutes stay in the prompt. The grader labels stay correct, partial, and incorrect. The title stays **StudyMaster AI**.
