# Build 09 — Connect your OpenAI key

The picture is [09-openai-setup-diagram.png](09-openai-setup-diagram.png). Click that file to see the drawing.

This plan follows [01-studymaster-agent.md](01-studymaster-agent.md). The study agents already call OpenAI. This build is how you turn that on for your own computer.

## Already built

`studymaster/agents/client.py` calls the OpenAI Responses API. The model name in `.env.example` is `gpt-4o-mini`. The key is read from `.env`. The log may say whether a key is present. The log never includes the key. A missing key stops before any paid call.

These buttons are the paid calls: **Study this page**, **Rewrite**, and **Check my answer**. Opening a saved study, downloading Markdown, and showing a stored answer do not call OpenAI.

## What you do before any new code

1. In your OpenAI account, set a monthly spending limit of $5.
2. Create an API key. Keep it on your computer. Do not paste it into chat.
3. From the project folder, copy the template:

```powershell
cd C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai
Copy-Item .env.example .env
notepad .env
```

4. On the `OPENAI_API_KEY=` line, put the key with no quotes and no spaces. Save the file.
5. Stop the running page with `Ctrl+C`, then start it again with `streamlit run app.py`.
6. In the PowerShell window, the new line should say `OpenAI key present: True`.

Then paste one public Microsoft Learn URL and press **Study this page**.

## Small page change after this plan is confirmed

The page will show one plain line: the key is ready, or the key still needs to be added. The line will not show the key. `.env.example` will stop saying that the page does not call OpenAI.

## Left alone

The starter catalog of LinkedIn posts stays for a later plan. A local free model stays optional. The real `.env` file stays out of git.
