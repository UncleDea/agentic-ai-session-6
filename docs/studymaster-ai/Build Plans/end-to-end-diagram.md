# End-to-end diagram

The picture is [end-to-end-diagram.png](end-to-end-diagram.png). Click that file to see the drawing.

![End-to-end diagram](end-to-end-diagram.png)

This Markdown file is the written copy of the same path. The short flowchart in [01-studymaster-agent.md](01-studymaster-agent.md) is a summary.

## Learner path

```mermaid
flowchart TD
    openPage[Learner opens the Streamlit page]
    openPage --> form["Enters level, goal, minutes, and one address"]
    form --> sourceChoice{Where did the address come from?}
    sourceChoice -->|Catalog| learnPage[Paired Microsoft Learn address]
    learnPage --> linkedinRef[LinkedIn address stays a reference and is not fetched]
    sourceChoice -->|Typed URL| typedPage["Typed http or https address"]
    linkedinRef --> submit[Submit]
    typedPage --> submit
    submit --> session{Result already on screen?}
    session -->|Yes| showAgain[Show that result again]
    showAgain --> noModelScreen[Model is not called]
    session -->|No| safety[Check the address]
    safety --> hops[Check every redirect hop]
    hops --> blocked{Private, local, or metadata target?}
    blocked -->|Yes| stopBlocked[Stop and show the error]
    blocked -->|No| download[Download with a timeout and a size limit]
    download --> article[Extract title, headings, and article text]
    article --> tooShort{Text shorter than the minimum?}
    tooShort -->|Yes| stopShort[Show the error]
    stopShort --> noModelShort[Model is not called]
    tooShort -->|No| saveText[Save the readable text]
    saveText --> outline[Coordinator asks for one shared outline]
    outline --> agents["Study, lesson, lab, project, and runbook agents"]
    agents --> inputs["Each agent receives the source, the outline, and the learner inputs"]
    inputs --> checker[Quote checker tests each section]
    checker --> leftOut[The source does not cover this.]
    checker --> oneFailed[One failed agent leaves the other sections in place]
    leftOut --> store[SQLite stores the source and the artifacts]
    oneFailed --> store
    store --> render[Page renders the artifacts and hides lesson answers]
    render --> quiz[Submitted answer goes to the grader]
    quiz --> attempt[Attempt is saved]
    render --> history[History, answer toggles, and Markdown download]
    history --> noModelLater[Read SQLite and do not call the model]
    render --> regen[Regenerate one section]
    regen --> onlyLater[This is the only later model call]
```

Plain text of the same path:

1. The learner opens the Streamlit page.
2. The learner enters a level, a goal, minutes, and one address.
   - A catalog choice uses the paired Microsoft Learn address.
   - The LinkedIn address stays a reference and is not fetched.
   - A typed address must be `http` or `https`.
3. Submit checks session state.
   - A result already on screen is shown again.
   - The model is not called.
4. A new address is checked, then every redirect hop is checked.
   - A private, local, or metadata target stops the run and shows the error.
5. The reader downloads the page with a timeout and a size limit.
6. The reader extracts the title, headings, and article text.
   - Text shorter than the minimum stops the run and shows the error.
   - The model is not called.
7. Readable text is saved.
8. The coordinator asks for one shared outline.
9. The study, lesson, lab, project, and runbook agents run.
   - Each agent receives the source, the outline, and the learner inputs.
10. The quote checker tests each section.
    - The source does not cover this.
    - One failed agent leaves the other sections in place.
11. SQLite stores the source and the artifacts.
12. The page renders the artifacts and hides lesson answers.
13. A submitted answer goes to the grader, and the attempt is saved.
14. History, answer toggles, and Markdown download read SQLite.
    - The model is not called.
15. Regenerating one section is the only later model call.

## Folder path

```mermaid
flowchart LR
    ui[ui] --> extraction[extraction]
    extraction --> agents[agents]
    extraction --> prompts[prompts]
    agents --> quoteChecker[quote checker]
    prompts --> quoteChecker
    quoteChecker --> storage[storage]
```

Plain text of the same path:

1. `ui` collects the address and the learner inputs.
2. `extraction` checks the address and returns article text, or an error and no text.
3. `agents` runs the coordinator, the outline, the five study agents, and the grader.
4. `prompts` holds the instructions those agents send.
5. The quote checker tests the writing against the extracted text.
6. `storage` saves the source, the artifacts, and the quiz attempts.
