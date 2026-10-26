# Build 04 — Study agent

The picture is [04-study-agent-diagram.png](04-study-agent-diagram.png). Click that file to see the drawing.

This plan covers the first model agent only. It follows [01-studymaster-agent.md](01-studymaster-agent.md). Confirm this file before any of its code is written.

The home page stays the StudyMaster AI title. This build does not add the lesson, lab, project, runbook, grader, or URL box.

## What this build adds

One shared way to call OpenAI, one outline step, one study agent, and a quote checker.

The study agent writes study material from a page that was already read:

- learning objectives
- a plain-language explanation
- a glossary
- misconceptions
- a short recap

Each important section includes a short quote from the source. A Python checker confirms the quote appears in the extracted text. A section with no verified quote is marked "not grounded".

## Files

- `studymaster/agents/client.py` calls `client.responses.create`. It reads `OPENAI_MODEL`, uses a timeout, and uses a low temperature.
- `studymaster/agents/outline.py` asks for one outline made only from the page.
- `studymaster/agents/study.py` writes the study material from that outline and the page.
- `studymaster/prompts/study.py` and `studymaster/prompts/outline.py` hold the prompt text.
- `studymaster/agents/quotes.py` checks quotes against the source text.

`OPENAI_TIMEOUT_SECONDS` and `OPENAI_TEMPERATURE` are added to `studymaster/config.py` and `.env.example`.

## Rules

- Every call receives the title, URL, headings, source text, learner level, goal, and minutes. The study agent also receives the shared outline.
- The prompt includes the source text and this rule: use only the supplied source, and say when the source does not cover something.
- An empty source never calls the model.
- A missing `OPENAI_API_KEY` raises a clear error before any network call.
- The API key is never written into the log.

## Tests

`tests/test_study_agent.py` uses a fake model client. It does not call OpenAI and does not use the public internet.

Required cases:

- The prompt contains the source text and the "use only this source" rule.
- An empty source never calls the client.
- A missing API key stops before any network call.
- A quote that is in the source passes the checker.
- A quote that is not in the source is marked not grounded.
- The study result includes objectives, an explanation, a glossary, misconceptions, and a recap.

## How to verify

```powershell
cd C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai
.\.venv\Scripts\Activate.ps1
python -m pytest
```

The new tests pass, and the page-reader and storage tests still pass. The home page still shows only **StudyMaster AI**.

## Left for later builds

The lesson, lab, project, and runbook agents, the coordinator that runs all five, the quiz grader, and the URL box are outside this build.
