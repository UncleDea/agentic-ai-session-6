# StudyMaster AI — Standard Operating Procedure

StudyMaster turns one readable public page into a study pack. The pack can contain an outline, a study, a lesson, a lab, a project, and a runbook. The pack uses only the words on that page.

This procedure is for a first visit. Follow the steps in order. Finish the first pack before you try another way to choose a page.

## 1. What you need before you start

You need:

1. Windows PowerShell.
2. This project folder: `C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai`
3. A browser.
4. An OpenAI key already stored in the `.env` file in that folder.

Before the first step, success looks like this: the browser title is **StudyMaster AI**, and the PowerShell window says `OpenAI key present: True`.

## 2. Start the app and leave the window open

1. Open PowerShell.
2. Type only the command after the existing `>`. Leave the `PS C:\...>` prompt where it is.
3. Go to the project folder:

```powershell
cd C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai
```

4. Start the page:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If the prompt already shows `(.venv)`, this shorter command is enough:

```powershell
streamlit run app.py
```

5. Wait until PowerShell shows `Local URL: http://localhost:8501`.
6. Open http://localhost:8501 in the browser.
7. Confirm the title is **StudyMaster AI**.
8. Look at the PowerShell window. The line `OpenAI key present: True` means the key is ready.
9. Leave that PowerShell window open while you study. Closing it stops the page.

If the line says `OpenAI key present: False`:

1. Open `.env` in Notepad.
2. Put the key on the `OPENAI_API_KEY=` line.
3. Use no quotes and no spaces.
4. Save the file, press `Ctrl+C` in PowerShell, and start the page again.

Do not copy `.env.example` over `.env`. That would replace the key.

## 3. Create one pack

The page runs from top to bottom: **What do you want to learn?**, **Starter article**, **Reading goal**, then the study form. On this first run, use the starter list only.

1. Leave **What do you want to learn?** empty.
2. Open **Starter article**. It starts on **Paste my own link**.
3. Type `loss prevention`.
4. Choose **Data protection: Learn about data loss prevention**.
5. Leave **Reading goal** on **No reading goal**. A reading goal fills **Goal** and can show a LinkedIn address. It does not fill **Page link**.
6. Confirm **Page link** shows `https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp`.
7. Confirm **Goal** shows `Explain how data loss prevention protects sensitive information.`
8. Leave **Level** at **Beginner**.
9. Read the line under **Minutes**: "Up to 10 minutes keeps the outline, study, and lesson. More than 10 minutes also keeps the lab, project, and runbook."
10. Leave **Minutes** at **20**.
11. Press **Study this page** once.

**Warning:** **Study this page** is a paid button. One new study pack is about one cent. Press it once, then wait. Do not press it again while the status line is working.

12. Watch the status line. A new pack names each step: **Checking the link.**, **Reading the page.**, **Writing the outline.**, **Writing the study.**, **Writing the lesson.**, **Writing the lab.**, **Writing the project.**, and **Writing the runbook.** Each finished section appears on the page. The line ends with **Study pack ready.**
13. If this same page, level, goal, and minutes are already saved, the line says **Opening the saved pack.** and then **Study pack ready.** That is a successful open. It does not call OpenAI again.

**Warning:** Changing the page, the level, the goal, or the minutes, and then pressing **Study this page** again, writes a new pack and spends about one cent.

**Study this page**, **Rewrite**, and **Check my answer** are the paid buttons. Opening a saved study, downloading, finding, and **Start over** do not call OpenAI.

An empty **Page link** says **Paste a public page link.** A private or localhost address says **This address cannot be opened.**

## 4. Read the pack

After **Study pack ready.**, read the pack in this order:

1. The title.
2. **About this pack**. It stays closed. Open it when you want the details. For this pack you should see **Read from learn.microsoft.com**, **For a beginner**, **20 minutes**, the goal, the saved day, and the pieces. A full pack says **Study, lesson, lab, project, runbook**. A section that failed stays off that line. You may also see the score, the latest check, the progress, the question, the reply day, and how many questions are still waiting.
3. **Download Markdown** and **Download Word**. They sit side by side under the title, before the first question.
4. The first question, then the box labeled **Your answer**.
5. The lesson, the later questions, and then the other sections.
6. The **Rewrite** buttons at the bottom.

Check one answer:

1. Click **Your answer** under the first question.
2. Type your reply in your own words.
3. Press **Check my answer** once.

**Warning:** **Check my answer** is a paid button. Press it once for that question.

4. Read the score. It says **Correct**, **Partial**, or **Incorrect**.
5. Read the hint under the score.
6. Read the line that starts with **Answer:**.

A line that says the source does not cover something is a finished result. The pack is using only the page. A page cut at the size limit says **This page was shortened to 60,000 characters.**

If the lesson came back empty, the page says **The lesson came back empty. Press Rewrite lesson to ask for it again.** If the page has no procedure, **Rewrite runbook** is not shown. **Rewrite study**, **Rewrite lesson**, **Rewrite lab**, and **Rewrite project** stay. Press **Rewrite** only for the one section that should be written again.

**Warning:** Each **Rewrite** button is paid. One press writes that section again.

## 5. Save a copy, find the pack, then clear the form

The download buttons are already under the title.

1. Press **Download Markdown**.
2. Press **Download Word**.
3. Open the Word file in Microsoft Word. Both files contain the study text. They do not contain the lesson answers.

Scroll to **Saved studies**.

4. Find the pack you just studied. The list shows the goal, **20 minutes**, and one next step.
5. Use that next step. It is one of these lines: **The lesson came back empty.**, **The project is not covered by this page.**, or **Left to check:** followed by a number.
6. Click **Find a study** and type `loss prevention`. The pack stays in the list. This box can also match words the list does not show. The box itself names those words.
7. Clear **Find a study** before you continue.
8. Press **Open study** on that pack.
9. Confirm **Page link**, **Level**, **Goal**, and **Minutes** filled in from the pack. **Level** is **Beginner**. **Minutes** is **20**. **Article text** stays empty because this pack came from a public page.
10. Read the line under **Study this page**: **This pack is already open. A new pack starts when the page, the level, the goal, or the minutes change.**

**Start over** sits under the form, above the pack.

11. Press **Start over**.
12. Confirm the pack closes, **Page link** and **Goal** are empty, and **What do you want to learn?** is empty.
13. Confirm the pack is still listed under **Saved studies**.
14. **Find a study** keeps whatever words were in it. Leave that box empty.

## 6. Other ways to choose a page

Use these only after the first pack exists. Each one still needs **Study this page** before a pack is written.

### Search the starter list

1. Click **What do you want to learn?**
2. Type a topic, such as `data loss prevention`.
3. Press **Find a page**.

One match fills **Page link** and **Goal**. Several matches say **Several pages match. Pick one.** Click the page you want. When the list has no match, the page says **The list does not have that topic yet.** It may then show one public address and **One public page is ready. Press Use this page, then Study this page.** Press **Use this page**. That fills **Page link**. If no public page is found, the page says **No public page was found.**

**Find a page** and **Use this page** do not call OpenAI. **Study this page** is still the button that reads the page.

### Choose a reading goal

1. Open **Reading goal**.
2. Choose a goal.
3. Confirm **Goal** changed.
4. Read the line **This is a study goal. Paste a public page or the lesson words before you press Study this page.**
5. Fill **Page link** or **Article text** yourself. A reading goal does not fill **Page link**.

A line that starts with `https://www.linkedin.com` is only a reference. The Learn address in **Page link** is the page that gets read.

### Paste the lesson words

1. Click **Article text**.
2. Paste the lesson words.
3. Read the line under the box: **A filled box is the lesson, so the page link is not opened.**
4. Fill **Goal** and leave **Minutes** at the length you want.
5. Press **Study this page** once.

**Warning:** This press is paid when the pasted words, level, goal, and minutes are not already saved.

## 7. Optional: remove one saved pack

Do this only when a pack should leave this computer. The first pack can stay.

1. Find the pack under **Saved studies**.
2. Press **Delete**.
3. The button changes to **Delete this study?**
4. Press **Delete this study?**

The second press removes that pack from this computer. The other saved studies stay.

## 8. Stop the app

1. Click the PowerShell window that is running the page.
2. Press `Ctrl+C`.
3. Leave the saved studies where they are. They remain on this computer. The next time you start the page, they are still under **Saved studies**.

## 9. How you know it worked

Tick each line:

- The PowerShell window stayed open until you pressed `Ctrl+C`.
- The title is **StudyMaster AI**.
- The key line says `OpenAI key present: True`.
- **Study this page** was pressed once for the first pack.
- The pack shows a first question.
- A checked answer shows **Correct**, **Partial**, or **Incorrect**.
- The pack appears under **Saved studies** with a goal, **20 minutes**, and one next step.
- **Open study** fills **Page link**, **Level**, **Goal**, and **Minutes**.
- The Markdown file and the Word file both open, and they contain the study text.
- **Start over** clears the open pack and leaves the saved studies in place.

## 10. Appendix for the person who maintains the app

A learner does not need this section.

From the project folder, this command walks the study path with a fake page, then runs the tests. It does not spend the API key.

```powershell
.\.venv\Scripts\python.exe scripts\check_app.py
```

This command does the same checks first. After they pass, it reads one public Microsoft Learn page and writes one real pack in a temporary database. That costs about one cent. The studies already on the page stay as they are.

```powershell
.\.venv\Scripts\python.exe scripts\check_app.py --live
```
