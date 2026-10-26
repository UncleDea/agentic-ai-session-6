# Build 02 — Safe page reading

This plan covers the first build only. It follows [01-studymaster-agent.md](01-studymaster-agent.md). Confirm this file before any of its code is written.

The home page stays the StudyMaster AI title. This build does not call OpenAI, does not create the database, and does not add a URL box.

## What this build adds

A Python reader that can turn one public web address into article text, or stop with a clear error when the page cannot be read.

The reader lives in `studymaster/extraction/`:

- `url_safety.py` decides whether an address is safe to open.
- `fetch.py` downloads the page and returns the title, headings, and visible text.
- `errors.py` holds the error types the rest of the app can show later.

`studymaster/config.py` and `.env.example` gain the four settings this reader needs:

| Setting | Default | Meaning |
|---|---|---|
| `FETCH_TIMEOUT_SECONDS` | `10` | How long one download attempt may take. |
| `MAX_RESPONSE_BYTES` | `1000000` | Largest decoded page the reader will keep. |
| `MAX_SOURCE_CHARS` | `20000` | Most article text kept for a later study step. |
| `MIN_SOURCE_CHARS` | `400` | Shortest article text that counts as readable. |

`DATABASE_PATH`, `OPENAI_TIMEOUT_SECONDS`, and `OPENAI_TEMPERATURE` wait for the builds that use them.

## Safe addresses

Accept only `http` and `https`.

Reject an address when any of these are true:

- The scheme is something else, such as `file`, `ftp`, or `data`.
- A user name or password is included in the address.
- The host is `localhost`, a loopback address, a private address, a link-local address, or a cloud metadata address such as `169.254.169.254`.
- The host name does not resolve to a public address.

Check the address before connecting. Resolve the host and check every returned address. A public name that points at a private address is rejected.

## Download rules

Follow redirects one hop at a time, with a limit of 5 hops. Run the same safety check on every hop before connecting. A redirect to a private address is rejected.

Use the timeout from settings. Read the body in pieces and stop when `MAX_RESPONSE_BYTES` is reached. The size limit applies to the decoded page, not only to the compressed download.

Accept HTML and plain text. Any other content type is an error.

Send a descriptive User-Agent that names StudyMaster. Send no cookies and no authorization header.

## Article text

From HTML:

- Prefer the `<main>` region, then `<article>`, then the body.
- Remove `script`, `style`, `nav`, `header`, `footer`, `aside`, and form controls.
- Keep headings `h1`, `h2`, and `h3` as a list, in page order.
- Collapse repeated blank space.
- Use the document title, then the first `h1`, as the title.

Plain text is kept as the body. Its title is the host name. It has no headings.

After cleaning:

- If the text is shorter than `MIN_SOURCE_CHARS`, stop with the message `This page did not include readable article text.` Return no article text.
- If the text is longer than `MAX_SOURCE_CHARS`, keep the first allowed characters and set a flag that the source was shortened.

A network error, timeout, unsafe address, oversized page, or unsupported type returns the error and no article text. The reader does not invent replacement text.

## Result shape

A successful read returns one object with:

- `url`: the final address after redirects
- `title`
- `headings`: a list of heading strings
- `text`
- `shortened`: true when the text was cut to `MAX_SOURCE_CHARS`

A failed read raises one of the reader errors. The message is safe to show to a learner. The log records the host and the error type. The log does not record query strings, because a query can contain a secret.

## Tests

Add `tests/test_extraction.py` and HTML fixtures under `tests/fixtures/`. Tests use fake responses and local files. They do not call the public internet.

Required cases:

- `http://127.0.0.1/` is rejected.
- `http://169.254.169.254/` is rejected.
- An address with a user name and password is rejected.
- A redirect from a public host to a private address is rejected.
- A body larger than `MAX_RESPONSE_BYTES` is rejected.
- A page whose visible text is shorter than `MIN_SOURCE_CHARS` returns no article text.
- A simple HTML page with a title, one heading, and a paragraph returns that paragraph and that heading.
- Navigation and script text are left out of the article text.
- Text longer than `MAX_SOURCE_CHARS` is shortened and marked shortened.

## How to verify

From the project folder, with the virtual environment active:

```powershell
cd C:\Users\Agwes\agentic-ai-session-6\docs\studymaster-ai
.\.venv\Scripts\Activate.ps1
python -m pytest
```

The run passes when every test above passes. Then run the title page once:

```powershell
streamlit run app.py
```

The page still shows only **StudyMaster AI**. Stop it with Ctrl+C.

## Left for later builds

SQLite, the model client, the outline, the five study agents, the quote checker, the quiz, and the URL box on the home page are outside this build.
