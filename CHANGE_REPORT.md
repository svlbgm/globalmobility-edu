# Detailed Change Report

## Product positioning

- Renamed the runtime identity from CrisisLens Local to PolicyTrace EDU, and later to GlobalMobility EDU to better reflect the exchange/mobility scope of the demonstration data.
- Reframed the system as a version-aware institutional-memory auditor for university policies.
- Preserved the offline Foundry Local requirement while making policy authority and traceability the primary value proposition.

## Document processing

- Added `.txt`, `.pdf` and `.docx` extraction.
- Added `[POLICY_METADATA]` parsing.
- Added title, version, status, effective date, review date, owner, audience and supersession fields.
- Removed metadata markup from displayed policy content while retaining a metadata summary in the embedding input.
- Added input validation for chunk size and overlap.
- Fixed a sentence-corruption bug: word-based chunking previously joined
  every line with a single space, erasing the boundary between a heading
  and the paragraph that followed it. A short heading word appearing
  elsewhere in a real sentence (for example "Approval") could then split
  that sentence in two. Every source line now gets its own
  sentence-ending punctuation before chunking
  (`_mark_line_breaks_as_sentence_boundaries`), and heading removal in the
  generation pipeline now requires an exact, whole-sentence match instead
  of a substring replace. All documents were re-ingested after this fix.

## SQLite

- Added structured policy metadata columns.
- Added automatic migration for the earlier database schema.
- Preserved JSON serialization for embedding vectors.
- Added database initialization and empty-index protection.

## Retrieval

- Replaced semantic-only sorting with a documented weighted score:
  - 60% semantic similarity
  - 20% policy approval status
  - 10% effective-date recency
  - 10% role alignment
- Added explicit score mappings for current, draft, superseded, legacy and unverified documents.
- Returned the score breakdown to the interface for auditability.
- Fixed a fragmented-context defect: when a document was split across
  multiple chunks, only the single highest-scoring chunk was guaranteed
  to reach generation. For "Can I apply late?", this meant the chunk
  stating there is no late-application process was retrieved while the
  sibling chunk with the actual March/October application windows was
  not, and an unrelated document (an appeals procedure) took its place
  in the context instead. `_include_strongest_linked_versions` now keeps
  every sibling chunk of the top-scoring document together with it,
  ahead of filling remaining slots with the next-best unrelated results.

## Generation

- Replaced the crisis-response prompt with a policy-auditor prompt.
- Added prompt-injection resistance for retrieved document content.
- Added authority, version conflict, role boundary, citation and missing-information rules.
- Added exact repeated-list-item cleanup and numeric citation-marker cleanup.
- Changed the answer structure to Applicable guidance, role-specific meaning, version/conflict check and information gaps.
- Fixed a duplicated-sentence defect: when the model's own conflict
  statement was missing one required element (for example the word
  "governing"), the contract layer appended a full second sentence that
  repeated language the model had already written, including a
  restatement of "must not be used for a new request". The append logic
  now only adds the specific missing clause.
- Fixed a grammar defect introduced by the fix above: the fallback clause
  for an already-stated conflict read "This documented procedural
  difference; the current_approved ... is the governing source" (missing
  "is a"). Rewritten to a complete sentence in both branches.
- Fixed a hallucinated-conflict defect: given two unrelated
  `current_approved` documents that happened to share similar wording
  (for example, both saying they do not specify a deadline), the model
  would sometimes invent a "documented procedural conflict/difference"
  between them and tell the user the first one "must not be used" —
  actively wrong guidance, since neither document is legacy or
  superseded. Rules 8, 18 and 21 of the system prompt now state this
  phrase and "must not be used" apply only when the metadata actually
  links two documents via supersedes/superseded_by. As a second layer,
  `enforce_answer_contract` now detects this pattern when it appears
  without a real link and replaces the section with an honest "no linked
  version conflict was found" statement instead of showing the
  fabrication or rejecting the whole answer.
- Strengthened the "Applicable guidance" instruction to answer the
  user's actual question first in plain terms (yes/no, a date, a fact)
  before naming the governing policy, instead of opening with only the
  policy's name or purpose.
- Extended automatic citation fallback (previously limited to
  "Applicable guidance", "Version and conflict check" and "Information
  gaps") to also cover "Actions for the selected role" and
  "Responsibilities of other roles", after a prompt change shifted the
  model's phrasing of empty-action statements (for example "No actions
  are required from the Student role...") in a way the fallback did not
  yet handle.
- Fixed a citation-cleanup gap: `clean_answer` removed a `[file][1]`
  numeric marker but not a citation the model repeated immediately after
  itself with a period in between (`[file]. [file]`). Both patterns are
  now collapsed to a single citation.
- Fixed a score-leakage defect found by probing 8 paraphrased/edge-case
  questions outside the five demo scenarios: the context block sent to
  the model included a literal "Governance-aware score: 0.8204" line for
  each piece of evidence, and the model occasionally copied that number
  straight into the answer, violating the existing "do not mention
  numeric scores" prompt rule with no validation catching it. Removed
  the score line from the generation context entirely (it is only
  needed for ranking, not for writing the answer) and added a
  `validate_answer` check as a second layer of defense.
- Fixed a repetition-lock defect: Phi-4 Mini occasionally produced a
  draft consisting of a single character repeated hundreds of times
  instead of a real answer, which the quality gate correctly rejected
  but which offered no recovery. Added `is_degenerate_completion` to
  detect a long run of one repeated character and, when detected, the
  pipeline retries generation once with a perturbed temperature and
  random seed before falling through to the fail-closed gate.
- Extended the degenerate-completion retry to also cover a raised
  exception during chat completion (for example a cancelled native
  call), not only a successfully-returned but repetition-locked draft.
  The first attempt's failure is now caught, logged, and treated the
  same as a detected degenerate draft: one retry with perturbed
  sampling before the error is allowed to propagate.
- Split the Streamlit error path so a fail-closed quality-gate
  rejection (HTTP 422) and a technical interruption of the chat call
  (any other backend error) show distinct, honest messages instead of
  collapsing every failure into the same generic text.
- Switched `_complete_text` from the streaming chat API
  (`complete_streaming_chat`) to the non-streaming one (`complete_chat`)
  while diagnosing the repetition-lock defect above; both paths route
  through the same native completion call, so this is a simplification
  (one call instead of a chunk-accumulation loop) rather than a
  behavior change.

## Answer-quality gate

- The backend never returns a draft that fails its own contract. If
  `enforce_answer_contract`'s narrow fixes cannot bring an answer into
  compliance, `/analyze` returns HTTP 422 with the specific
  `validation_issues` and no answer body — verified with role/question
  mismatches during manual testing, where the gate correctly rejected an
  answer that leaked another role's action into the selected role's
  section.
- Confirmed this holds across 5 real-model acceptance scenarios and
  ad-hoc edge cases (empty question, unsupported role, out-of-range
  `top_k`, malformed JSON body).

## Backend

- Added role allow-list validation.
- Added bounded and validated evidence-count input.
- Added governance-ranking information to the health response.
- Kept the Flask process single-threaded to reduce Foundry Local native-runtime instability.

## Interface

- Preserved the academic visual identity and deepened it: added a Google
  Fonts pairing (Fraunces for display headings, Inter for interface
  text), a hand-drawn SVG seal in the hero section, a subtle
  security-paper hairline texture, and a compact, low-contrast sidebar
  styled after real product sidebars (small uppercase section labels,
  an inline status dot instead of a boxed alert, spacing instead of
  divider rules) rather than Streamlit's default look.
- Set `toolbarMode = "viewer"` so the empty Deploy/developer toolbar
  disappears without removing the native sidebar collapse/expand
  control it also contains.
- Added six presentation-ready demonstration scenarios, including a
  partner-institution question answered from a new synthetic document
  (`exchange_partner_institutions_v1_2026.txt`) that demonstrates the
  system declining to fabricate a list of university names and instead
  citing who actually has authority to confirm one.
- Rebranded the hero seal from a laurel-wreath motif to a globe with a
  dashed orbit accent, matching the GlobalMobility EDU identity; added a
  matching subtle radial-gradient glow behind the seal and in the page
  background corners for a less flat first impression.
- Added document status, version, date, owner and audience to the evidence trace.
- Added separate Semantic, Status, Recency and Role score cards.
- Clarified that documents are synthetic and outputs do not replace official decisions.
- Added an English/Turkish interface-language switch. Only interface
  chrome is translated; the generated answer and the policy documents
  stay in English, since translating grounded, cited evidence text would
  risk changing its meaning. The underlying role value sent to the
  backend is unaffected by the display language.
- Added a "View raw source file (unedited)" popover next to the existing
  formatted evidence view. It reads the cited file directly from
  `documents/` and displays it byte-for-byte, including the
  `[POLICY_METADATA]` block, so a user can check a citation against the
  source without trusting the model's summary of it.
- Fixed a formatting regression in the evidence popover caused by the
  document-processing fix above: the synthetic-document notice picked up
  a stray trailing period, and heading text stopped being bolded because
  the matching pattern did not expect a period after the heading.
- Replaced the raw backend exception text shown on a failed analysis
  (for example "Error during chat completion: Operation was cancelled")
  with a single plain-language message explaining that the system could
  not produce a confidently grounded answer for the question/role
  combination, and suggesting the matching role or a rephrased question.
- Clarified the "Version link" note on a linked historical source to
  explicitly state that it is shown next to the current version for
  comparison regardless of its ranking score, since a linked legacy
  document can otherwise appear above a higher-scoring unrelated
  document with no visible explanation.

## Data hygiene

- Re-ingested all 9 documents after a stale index was found containing
  only 8 chunks; `exchange_application_calendar_v1_2026.txt` had never
  been indexed, which silently broke the "When can I apply?" scenario.
- Removed a stray, byte-identical, unused duplicate of `src/retrieval.py`
  from the project root.
- Added `output/` and `tmp/` to `.gitignore` after finding unrelated
  personal files (a CV, transcripts, application-review PDFs) had been
  created inside the project directory by an unrelated, concurrent
  process; the files were moved out of the repository, not deleted.

## Dataset and testing

- Added nine synthetic policy documents with deliberate conflicts and gaps.
- Added a PowerShell preparation script that archives earlier demo documents without deleting them.
- Added five written acceptance scenarios.
- Added fast unit tests for metadata parsing and governance rules.
- Updated the earlier document, embedding and retrieval scripts to use the GlobalMobility dataset.
- Updated the end-to-end RAG test to use an academic-policy conflict.

## Not claimed

- No real-university deployment or official policy validation is claimed.
- No real-user performance result is claimed until an actual pilot is completed.
- No Graph-RAG, cross-encoder reranking or hybrid keyword search is claimed.
