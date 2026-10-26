# Build 31 — Empty lesson hint

The picture is [31-empty-lesson-hint-diagram.png](31-empty-lesson-hint-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). An empty lesson tells the learner which button asks again.

## What this build does

When the lesson text is exactly **The source does not cover a lesson.** and there are no questions to check, the page adds one line under the score: **The lesson came back empty. Press Rewrite lesson to ask for it again.**

That line is only a pointer. Showing it does not call OpenAI. **Rewrite lesson** is still the button that asks again. A lesson that has words, and a pack that already has a question, do not get this line. The downloaded file does not include it.

## Left alone

The empty-lesson retry stays. The three checks stay. The first question still leads a pack that has questions. The title stays **StudyMaster AI**.
