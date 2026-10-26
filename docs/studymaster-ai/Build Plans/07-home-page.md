# Build 07 — Home page

The picture is [07-home-page-diagram.png](07-home-page-diagram.png). Click that file to see the drawing.

This plan is for the page a learner uses on their own computer. It follows [01-studymaster-agent.md](01-studymaster-agent.md). The grader in [06-grader.md](06-grader.md) stays the next build.

## What this build adds

The title stays **StudyMaster AI**. The page adds a link box, a level, a goal, minutes, and a button labeled "Study this page".

On that button, the page reads the link with the existing reader, then runs the coordinator from build 05. It shows the outline and the five sections. A failed section shows its error, and the sections that succeeded stay on the page. The pack is saved in the local SQLite database.

Lesson check answers stay in memory for the grader. They are left off the page.

Streamlit reruns the script on every click. The model runs only when the learner presses the button. Pressing it again for the same unchanged page, level, goal, and minutes shows the saved pack and does not call the model again.

A bad link or an unreadable page shows the existing safe error and stops. The model is not called.

## Left for later

The grader, history, regenerating one section, and Markdown download stay later. The LinkedIn catalog stays a reference list until each technical post has a Microsoft Learn URL.
