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
6. **Saved studies** at the bottom opens that pack again. **Download Markdown** saves the pack. Opening a saved study does not call OpenAI.

A sentence is shown when its quote is on the page, its main words appear on that page, and a negation matches the quote. A sentence that fails is rewritten once. If it still fails, the pack says the source does not cover it. A hidden lesson answer that fails is not graded. A lesson that comes back with no sections is requested once more.

A page cut at the size limit says "This page was shortened to 60,000 characters." Under the title, the pack counts sentences left out and questions you can check.

Under **Saved studies**, **Find a study** keeps a study when the words you type appear in the title or in the goal line under it. Each saved study also shows the day it was saved. **Delete** asks once, and the next press removes that pack from this computer.

**Start over** clears the open pack and the form. The saved studies stay.

To study copied words, paste them into **Article text**.

A line that starts with `https://www.linkedin.com` is only a reference. The Learn address in **Page link** is the page that gets read.

**Study this page**, **Rewrite**, and **Check my answer** are the paid buttons. One new study pack is about one cent.

## Stop the page

In the PowerShell window, press `Ctrl+C`.
