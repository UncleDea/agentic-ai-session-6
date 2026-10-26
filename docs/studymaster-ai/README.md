# StudyMaster AI

StudyMaster turns one public page into a study pack. This guide opens the page and studies one article from the list.

## Open the page

1. Open PowerShell.
2. Go to the project folder:

```powershell
cd C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai
```

3. Start the page:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If the prompt already shows `(.venv)`, this shorter command is enough:

```powershell
streamlit run app.py
```

Type only the command after the existing `>`. Leave the `PS C:\...>` prompt where it is.

4. Open http://localhost:8501. The title is **StudyMaster AI**.

The PowerShell line `OpenAI key present: True` means the key is ready. If it says `False`, open `.env` in Notepad and put the key on the `OPENAI_API_KEY=` line with no quotes and no spaces. Do not copy `.env.example` over `.env`.

## Study one article

1. In **Starter article**, type `loss prevention`.
2. Choose **Data protection: Learn about data loss prevention**.
3. **Page link** and **Goal** fill in. Leave **Level** at Beginner and **Minutes** at 20.
4. Press **Study this page** once and wait. While the pack is written, the page names the step it is on.
5. Read the sections. Type a reply and press **Check my answer**. The score and hint appear, then the answer.
6. **Saved studies** at the bottom opens that pack again. **Download Markdown** saves the pack. **Download Word** saves the same pack so Microsoft Word can open it. Opening a saved study does not call OpenAI.

A sentence is shown when its quote is on the page, its main words appear on that page, and a negation matches the quote. A sentence that fails is rewritten once. If it still fails, the pack says the source does not cover it. A hidden lesson answer that fails is not graded. A lesson that comes back with no sections is requested once more.

A page cut at the size limit says "This page was shortened to 60,000 characters." Under the title, the pack counts sentences left out and questions you can check. A finished pack keeps the site, the level, the minutes, the goal, the day, and the pieces inside a closed **About this pack** heading. One example is **Read from learn.microsoft.com**, then **For a beginner**, **5 minutes**, **Master the material.**, **Saved October 25, 2026**, and **Study, lesson, lab, project, runbook**. A failed section stays off that pieces line. The first question and its answer box come next, and the lesson is under them. **Download Markdown** and **Download Word** sit side by side under the title, before that question. The download stays the study text. **Download Word** saves that same text as a Word file. Up to 10 minutes, a new pack keeps the outline, study, and lesson. More than 10 minutes also keeps the lab, project, and runbook. A saved pack stays the size it was saved. If the lesson came back empty, the page says to press **Rewrite lesson**. While a new pack is written, each finished section appears on the page.

**What do you want to learn?** searches the starter list. **Find a page** fills **Page link** and **Goal** when one article matches. Several matches ask you to pick one. When the list has no match, one safe public address can be shown. **Use this page** fills **Page link**. **Study this page** is still the button that reads it. This search does not call OpenAI.

Under **Saved studies**, **Find a study** keeps a study when the words you type appear in the title, in the goal line, in the pieces line, in the minutes line, in the site line, in the saved day, in the level line, in the score line, in the check line, or in the progress line, or in the question line, or in the reply line, or in the line for questions still waiting, or in the line that says the lesson came back empty, or in the line that says this page has no procedure, or in the line that says the project is not covered by this page. Typing **beginner** keeps a pack written for a beginner. Typing **advanced** leaves that pack off the search. Typing **5** leaves a 15-minute line off that search, and it also leaves a study saved on the 25th off that search. A pasted lesson has no site line, so it stays off a search for **learn.microsoft.com**. Each saved study shows its goal, its minutes, and one next step. The identity pack says **Left to check: 12.** The Entra pack says **The lesson came back empty.** The 15-minute pack and the 20-minute pack say **The project is not covered by this page.** **This page has no procedure.** stays off that list. The open pack keeps those lines inside a closed **About this pack** heading. The first question is what you see. Opening **About this pack** shows the site, the level, the day, the pieces, the score, the latest check, the progress, the question, the reply day, and how many questions are still waiting. **Find a study** still reads those lines when the list does not show them. Typing **12** keeps the pack whose score says **12**. Typing **5** keeps a pack whose score says **5**, a pack saved for **5 minutes**, and the 20-minute pack, because that pack says **Left to check: 5.** Typing **partial** keeps a pack whose latest check says **Partial**. Typing **correct** leaves a pack that says **Incorrect** off that search. Typing **purpose** keeps the pack whose latest question says **purpose**. Typing **prevention** still keeps both data loss prevention packs, because that word is in the title. Typing **reply** keeps the pack whose reply day says **reply**. Typing **25** still keeps every pack, because that number is in **Saved October 25, 2026.** Typing **left to check** keeps the 15-minute pack, the 20-minute pack, and the identity pack. The Entra pack stays off that search. Typing **empty** keeps only the Entra pack. Typing **procedure** keeps all four packs. Typing **covered** keeps the 15-minute pack and the 20-minute pack. Typing **project** still keeps every pack, because that word is already in **Study, lesson, lab, project, runbook**. Opening a pack that says the page has no procedure leaves **Rewrite runbook** off. **Rewrite study**, **Rewrite lesson**, **Rewrite lab**, and **Rewrite project** stay. Inside **About this pack**, the 15-minute pack and the 20-minute pack show **The project is not covered by this page.** under **Left to check: 5.** **Open study** fills **Level**, **Goal**, and **Minutes** from that pack. It also fills **Page link** when the pack was read from a public page. A pasted lesson leaves **Page link** as it is and fills **Article text** with the saved words. A public page leaves **Article text** empty. While that pack is open, the form says **This pack is already open. A new pack starts when the page, the level, the goal, or the minutes change.** **Delete** asks once, and the next press removes that pack from this computer.

**Start over** clears the open pack, the form, and **What do you want to learn?** The saved studies stay. **Find a study** keeps its words.

To study copied words, paste them into **Article text**.

A line that starts with `https://www.linkedin.com` is only a reference. The Learn address in **Page link** is the page that gets read.

**Study this page**, **Rewrite**, and **Check my answer** are the paid buttons. One new study pack is about one cent.

## Stop the page

In the PowerShell window, press `Ctrl+C`.
