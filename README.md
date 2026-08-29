# GlobalMobility EDU

GlobalMobility EDU is a private, local and version-aware institutional-memory auditor for university policies. It retrieves relevant policy sections, evaluates document authority and produces role-specific guidance with traceable evidence.

The prototype was developed for the Microsoft AI Innovators Summer Internship Program using Microsoft Foundry Local.

## Why this is more than a standard RAG chatbot

Semantic similarity alone can rank an obsolete document highly. GlobalMobility EDU therefore combines four signals:

```text
final score =
    0.60 × semantic similarity
  + 0.20 × policy approval status
  + 0.10 × effective-date recency
  + 0.10 × role alignment
```

The application also:

- distinguishes `current_approved`, `superseded`, `legacy` and `legacy_unverified` documents;
- uses `supersedes` and `superseded_by` relationships;
- separates Student, Academic Advisor and Department Administrator responsibilities;
- identifies missing facts instead of inventing deadlines or procedures;
- shows the ranking breakdown for every retrieved evidence section;
- performs document retrieval and model inference locally.

## Answer-quality gate (fail-closed, not just fail-safe)

A local model can still produce a fluent but wrong answer even with the
right evidence in front of it. GlobalMobility EDU does not trust generation
output by default. Every draft answer is checked against the retrieved
evidence before a user ever sees it:

- every numbered action and factual sentence must carry an exact-filename
  citation that is actually present in the retrieved evidence;
- an action in "Actions for the selected role" is rejected if it is
  supported only by legacy, superseded or unverified evidence, or if it
  belongs to a different role;
- a linked current-versus-historical pair must be named a "documented
  procedural conflict/difference" with the current version stated as the
  governing source;
- two documents are never called a version conflict unless their
  metadata actually links them through `supersedes`/`superseded_by` —
  the model cannot invent a conflict, or tell the user a valid
  `current_approved` policy "must not be used", just because two
  unrelated policies happen to use similar wording.

Narrow, evidence-preserving fixes are applied first: dropping a
role-leaked line, adding a missing citation from the same evidence,
replacing a fabricated version-conflict claim with an honest statement.
If the answer still fails after that, the backend returns
**HTTP 422 with no answer at all** rather than show a plausible-looking
but ungrounded response. This is enforced in `src/rag_pipeline.py`
(`validate_answer`, `enforce_answer_contract`) and `backend.py`, and is
covered by more than half of the 44 automated tests.

## Verify the source yourself

Every retrieved policy section links back to two views of its source
document: a readable rendering, and a **byte-for-byte, unedited view of
the file on disk** (including its `[POLICY_METADATA]` block). The point
is that a user should never have to take the model's citation on faith —
the exact file it cites is one click away, unmodified by the app.

## Architecture

```text
Streamlit interface (English / Türkçe)
        |
        v
Local Flask backend (127.0.0.1:8000)
        |
        +--> Qwen3 Embedding --> governance-aware retrieval --> SQLite
        |
        +--> Phi-4 Mini --> draft answer
        |
        +--> answer-quality gate (citations, role scope, version conflict)
        |         |
        |    pass |   fail --> HTTP 422, nothing shown to the user
        |         v
        +--> grounded, cited policy response
```

The Flask separation prevents Streamlit reruns from repeatedly initializing Foundry Local native resources.

## Interface language

The Streamlit sidebar includes an English/Turkish (Türkçe) switch for
interface labels, headings, status messages and score explanations. The
generated policy answer and the underlying policy documents stay in
English, because the local chat model, its grounding prompt and the ten
synthetic documents are English-only; translating generated evidence text
would risk changing its meaning. A short note above the language switch
reminds the user of this when Turkish is selected.

## Demonstration data

The repository contains ten synthetic university-policy documents. They are deliberately constructed to test:

- a current-versus-legacy exchange-recognition conflict;
- a superseded-versus-current Learning Agreement conflict;
- a recurring exchange-program application calendar;
- a partner-institution question with no fabricated list of universities;
- role and decision-authority boundaries;
- missing processing-time and appeal-deadline information.

Every document is marked as synthetic. The project does not contain personal student records or claim that the data represents a real university.

## Setup on Windows

Requirements:

- Windows 11
- Python 3.12
- Microsoft Foundry Local compatible hardware

Create and activate the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If an existing `.venv` points to a Python installation that has moved after a
Microsoft Store update, repair it without deleting installed packages:

```powershell
py -3.12 -m venv --upgrade .venv
```

## Ingest the policy documents

First archive documents from the earlier RAG demonstration:

```powershell
.\prepare_globalmobility.ps1
```

This operation does not delete them. It moves earlier root-level demo documents into `documents/archive_previous_demo`, which the ingestion script does not scan.

Then rebuild the index:

```powershell
python ingest.py
```

This command extracts policy metadata, generates Qwen3 embeddings and rebuilds the local SQLite index.

Re-ingestion is required only after policy documents or their metadata change.
The repository's current local index contains twelve policy sections.

## Serve the application locally

The recommended launcher uses Waitress for the backend, keeps both services
bound to this device and shuts the backend down when the frontend stops:

```powershell
.\serve_globalmobility.ps1
```

Wait until the browser opens at `http://localhost:8501`. Press `Ctrl+C` in the
same PowerShell window to stop both services.

Both the policy API (`127.0.0.1:8000`) and interface (`127.0.0.1:8501`) are
local-only by default. Do not expose this prototype directly to the internet;
institutional authentication, access control and transport security would be
required before handling real university data.

### Manual development mode

From the project root, open the first PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe backend.py
```

Wait for:

```text
GlobalMobility EDU is ready.
Running on http://127.0.0.1:8000
```

Open a second PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`. The sidebar should report a ready local engine,
the two model names and twelve indexed policy sections.

## Tests

Run the fast tests without loading a local language model:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

After ingestion, run the complete local RAG test:

```powershell
.\.venv\Scripts\python.exe test_rag.py
```

With `backend.py` running, execute all five delivery scenarios:

```powershell
.\.venv\Scripts\python.exe acceptance_demo.py
```

The acceptance runner checks response-contract violations, role leakage,
historical-instruction reuse, invented processing durations and governing-source
language. It fails fast when a scenario is not presentation-ready.

## Five-minute presentation and demo

1. **0:00–0:40 — Problem.** A semantically similar policy can be obsolete; a
   normal RAG ranking can therefore return plausible but invalid guidance.
2. **0:40–1:20 — Architecture.** Show Streamlit → local Flask → Qwen3
   embeddings/governance reranking → SQLite → Phi-4 Mini. Emphasize that policy
   documents and inference remain on-device.
3. **1:20–2:25 — Current versus legacy.** Run **Version conflict** as Student.
   Point out v2 as `current_approved`, v1 as linked historical evidence and the
   explicit procedural conflict/difference statement.
4. **2:25–3:20 — Role boundaries.** Run **Role-aware guidance** as Academic
   Advisor. Contrast the Advisor action list with Student, Administrator and
   committee responsibilities.
5. **3:20–4:05 — Missing information.** Run **Missing information**. Show that
   no working-day duration is invented.
6. **4:05–4:40 — Authority beats similarity.** Run **Submission conflict** as
   Department Administrator. Show the signed portal procedure governing over
   the superseded unsigned-email instruction.
7. **4:40–5:00 — Evidence and limits.** Expand one evidence card, open the
   raw source file to show the citation matches the file on disk exactly,
   then state that the policies are synthetic and the prototype does not
   make official academic decisions.

## Limitations

- The included policies are synthetic demonstration data.
- Authority depends on accurate metadata supplied during ingestion.
- The prototype does not replace authorized university decisions.
- Ranking weights are design choices and require evaluation with real users before production use.
- Initial local model loading may take several minutes depending on hardware.
- CPU generation is deliberately capped (`max_tokens`), but response time
  still varies with system load: a few seconds for the deterministic
  application-calendar path, and roughly 1–4 minutes for a fully
  generated, quality-gated answer on the tested machine.
- On rare occasions Phi-4 Mini locks into a repetition loop instead of a
  real answer. The pipeline detects this and retries once with adjusted
  sampling; if the retry is also unusable, the fail-closed gate returns
  HTTP 422 rather than show the broken draft.
- The controlled quality layer is conservative: when role ownership is not
  explicit, it may omit an action instead of inferring authority.
- The raw-source-file view only renders for `.txt` documents; a `.pdf` or
  `.docx` source (both are supported for ingestion) does not show a raw
  preview in the current interface.
- Phi-4 Mini is small enough that it can still state a specific,
  plausible-sounding detail (a signature format, a contact office, a
  next step) that is not actually present in the retrieved evidence,
  instead of saying the detail is not specified. Citation enforcement
  and role-boundary enforcement catch a wide range of failures, but they
  cannot verify that every individual factual claim is entailed by the
  cited text — that would need a dedicated fact-checking pass, which
  this prototype does not implement. Always verify a specific procedural
  detail against the linked source file before relying on it.

## Engineering rigor

- 44 automated tests (`tests/`) cover governance scoring, citation
  enforcement, role-boundary enforcement, sibling-chunk retrieval and the
  Streamlit contract — no local model required, runs in about a second.
- 5 end-to-end acceptance scenarios (`acceptance_demo.py`) exercise the
  real local model against the fail-closed backend and are re-run after
  every change to the prompt, the document pipeline or the retrieval
  logic.
- Generation defaults to deterministic settings (`temperature=0`, fixed
  `random_seed`) for reproducibility. In the rare case the local model
  locks into a repetition loop instead of a real answer, the pipeline
  detects the degenerate output and retries once with adjusted sampling
  before handing off to the fail-closed quality gate (`src/rag_pipeline.py`,
  `is_degenerate_completion`).
- No data leaves the device at any point: embeddings, generation and
  storage all run through Foundry Local and SQLite on localhost.

## Technology

- Microsoft Foundry Local
- Phi-4 Mini
- Qwen3 Embedding 0.6B
- Python
- SQLite
- Flask
- Streamlit
