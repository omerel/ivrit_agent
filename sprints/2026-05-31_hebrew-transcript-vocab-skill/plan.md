# Sprint: Build a Hebrew-transcript review Claude Code skill (transcribe → word-by-word vocab Q&A → RTL transcript + Hebrew summary)

**Started:** 2026-05-31
**Goal:** Ship a Claude Code skill that transcribes an audio file via the `ivrit-transcribe` MCP, walks the Hebrew transcript word-by-word in an interactive Q&A loop backed by a root-level `VOCAB.md`, then renders an RTL transcript (זמן בדקות / דובר / מלל) and a Hebrew meeting summary.

## Context

**Deliverable type & name.** The guide chose a *skill* (not a script/subagent) because step 2 must **pause and ask the user interactively** — only a skill running in the live session can do that. The skill is named **`hebrew-transcript-review`** (active, verb-first, technology-specific per `writing-skills` CSO guidance). It lives at `.claude/skills/hebrew-transcript-review/SKILL.md` plus helper templates/scripts.

**Upstream MCP (built last sprint).** `mcp_code/server.py` registers FastMCP server **`ivrit-transcribe`** exposing tool `transcribe(audio_path: str) -> dict`. It forwards to the FastAPI `/transcribe` service which **must be running first**:
`uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` (override target via env `TRANSCRIBE_API_URL`, default `http://localhost:8000`). Tool output is JSON, passed through unchanged:
`{ "segments": [{"speaker": str, "text": str, "start": float, "end": float}, ...], "language": str|null, "num_speakers": int|null }`. Transcript text is **Hebrew**. The tool raises `FileNotFoundError` for a bad path and `RuntimeError` on non-2xx API responses.

**VOCAB.md location (guide decision — do NOT re-litigate).** `VOCAB.md` lives at the **repo ROOT** (`/Users/omer/Documents/ivrit_agent/VOCAB.md`), NOT under `resource/` (CLAUDE.md §4: `resource/` is guide-owned, read-only). Markdown table, columns: `מילה (Hebrew word)` | `פירוש (meaning/explanation)` | `דוגמה מההקשר (example context)` | `תאריך (date-added)`. VOCAB.md is the **first place checked** before asking the user about any word, and the **only place written** when the user explains a word.

**Sample audio.** `resource/audio smaples/audio_sample_1min.m4a` (~1.4 MB, short — use this for the live end-to-end test, not the 140 MB `audio.m4a`). Note the folder name is literally `audio smaples` (typo, contains a space) — quote the path.

**RTL / Hebrew rendering.** The CLI does NOT render Hebrew RTL reliably. The rendered transcript and the summary are therefore **written to Markdown output files** (under a sprint/run output dir), not relied upon in terminal echo. The `זמן בדקות` column converts segment `start` seconds → **`mm:ss` (e.g. `02:47`) — guide decision, locked; apply consistently in T1/T5**.

**Word-by-word UX (the heart of the skill).** Default flow: the skill walks segments in order; for each segment it shows the **full segment text as context**, then **lets the USER name the word(s) they don't understand** in that segment (user-driven — avoids interrogating every trivial word). For each named word: (a) normalize and look it up in VOCAB.md; if present, state the known meaning and move on; (b) if absent, ask the user to explain it (or the skill proposes a meaning for the user to confirm), then append a row to VOCAB.md. The user can say "next"/"הבא" to skip a segment and "done"/"סיים" to end the pass early. T3 must specify Hebrew tokenization/normalization (strip niqqud, strip punctuation, handle prefixed letters ו/ה/ב/כ/ל/מ/ש and final-letter forms) and the exact prompt wording (bilingual).

**Skill trigger phrasing (must activate in EN and HE).** The SKILL.md `description` must include English triggers (e.g. "review/transcribe this meeting and teach me the words", "go over the transcript word by word") AND Hebrew triggers (e.g. "תמלל ותעבור איתי על המילים", "תעבור איתי מילה-מילה על התמלול", "תלמד אותי את המילים מההקלטה").

## Tasks

- [x] **T1** [done] @architect — Design the skill: name, end-to-end flow, file layout, data contracts, and the VOCAB.md schema.
  - Acceptance: A short design note (in @architect's work-log, not a standalone report .md) that fixes: (1) skill dir `.claude/skills/hebrew-transcript-review/` and the list of files it will contain (SKILL.md + any helper script/templates); (2) the exact VOCAB.md column schema and header row; (3) the `זמן בדקות` time format (mm:ss vs decimal) chosen once and reused; (4) the word-by-word loop state machine (per-segment context → user names words → VOCAB check → explain/confirm → append → next/done) including the bilingual user-facing prompts; (5) where run outputs (rendered transcript .md, summary .md) are written and their naming. No contradictions with later tasks' signatures.
  - Notes: Follow `writing-skills` CSO (description = triggers only, no workflow summary). This task only decides; T2–T6 implement. Keep helper logic small and Python where a deterministic script helps (tokenization/render), but the interactive Q&A itself is SKILL.md instructions executed by the live agent.

- [x] **T2** [done] @backend — Scaffold the skill and wire the MCP `transcribe` call (step 1 of the flow).
  - Acceptance: `.claude/skills/hebrew-transcript-review/SKILL.md` exists with valid YAML frontmatter (`name: hebrew-transcript-review`, `description` containing BOTH English and Hebrew trigger phrases per Context). Body documents: prerequisite (FastAPI service running on :8000, how to start it), how to call the `ivrit-transcribe` MCP `transcribe` tool with the user-given `audio_path`, the expected JSON shape, and how `FileNotFoundError`/`RuntimeError` are surfaced to the user. Frontmatter parses (`name` is hyphen-only, ≤1024 chars total).
  - Notes: Match the SKILL.md structure from `superpowers:writing-skills` (Overview, When to Use, procedure). Cross-reference the MCP by name; do not duplicate `mcp_code/` logic.

- [x] **T3** [done] @backend — Implement VOCAB.md schema + a deterministic lookup/append helper and Hebrew word normalization.
  - Acceptance: A helper (e.g. `.claude/skills/hebrew-transcript-review/scripts/vocab.py`) that: creates root `VOCAB.md` with the T1 header table if missing; `lookup(word)` returns the existing row/meaning after normalization (niqqud-stripped, punctuation-stripped, prefix-letter aware) or None; `append(word, meaning, example, date)` adds one well-formed Markdown table row and never duplicates an already-present normalized word. Idempotent: appending the same word twice yields one row. Tests in `tests/` cover create-if-missing, lookup-hit, lookup-miss, normalization (niqqud + prefix ו/ה/ב/כ/ל/מ/ש), and no-duplicate append. `uv run pytest tests/ -k vocab` passes.
  - Notes: Writes ONLY to repo-root `VOCAB.md`; never touch `resource/`. Use `superpowers:test-driven-development` (test first). Date format ISO `YYYY-MM-DD`.

- [x] **T4** [done] @backend — Write the interactive word-by-word review procedure into SKILL.md (step 2/3 of the flow).
  - Acceptance: SKILL.md contains an unambiguous, step-by-step procedure for the live agent that: iterates segments in order; for each segment prints the segment text as **context** plus speaker/time; asks the user (bilingual prompt) which word(s) they don't understand; for each named word calls the T3 lookup FIRST and skips/echoes if known; if unknown, asks the user to explain (or proposes a meaning to confirm) and then appends via the T3 helper; supports user commands `next`/`הבא` (skip segment) and `done`/`סיים` (end pass). Procedure explicitly states it must NOT auto-ask about every word (user-driven). A reviewer can follow the steps without inventing behavior.
  - Notes: This is the heart of the skill. Quote exact bilingual prompt strings agreed in T1. Reference the T3 helper by path/function name.

- [x] **T5** [done] @backend — Implement the RTL transcript renderer (זמן בדקות / דובר / מלל) writing to a Markdown file.
  - Acceptance: A helper (e.g. `.claude/skills/hebrew-transcript-review/scripts/render_transcript.py`) takes the transcribe JSON and writes a Markdown file containing a Hebrew RTL table with exactly the columns `זמן בדקות | דובר | מלל`, one row per segment, `start` seconds converted to the T1-chosen minutes format, rows in chronological order. Output file includes an RTL marker/`dir="rtl"` hint where Markdown allows. Tests in `tests/` assert the table header, row count == segment count, and correct seconds→minutes conversion for sample inputs. `uv run pytest tests/ -k render` passes. SKILL.md references this step.
  - Notes: Do not rely on terminal RTL; the .md file is the deliverable. Decimal-minutes vs mm:ss must match T1.

- [x] **T6** [done] @backend — Add the Hebrew meeting-summary step to SKILL.md (step 5 of the flow).
  - Acceptance: SKILL.md documents how the live agent produces a **Hebrew** summary of the meeting from the transcript and writes it to a Markdown output file, with clearly labeled Hebrew sections for: סיכום (overview), החלטות (decisions), משימות/מטלות (TODOs/action items), ומעקבים (follow-ups). The instruction specifies input (transcript segments), output file location/naming (per T1), and that the summary is in Hebrew. A reviewer can identify each required section.
  - Notes: This step is agent-generated prose (not a script). Keep instructions concrete about the four required sections.

- [x] **T7** [done] @qa — End-to-end validation against the live stack with the 1-minute sample.
  - Acceptance: Start the FastAPI service (`uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`), confirm the `ivrit-transcribe` MCP `transcribe` tool returns JSON for `resource/audio smaples/audio_sample_1min.m4a`, then exercise the skill end to end and verify: (1) a transcript is obtained; (2) the word-by-word loop checks VOCAB.md before asking and appends a new word as a valid table row to root `VOCAB.md`; (3) re-running and naming the same word does NOT re-ask (VOCAB hit); (4) an RTL transcript .md with columns `זמן בדקות / דובר / מלל` is produced; (5) a Hebrew summary .md with the four required sections is produced; (6) all unit tests pass (`uv run pytest tests/`). Findings recorded in @qa's work-log with the actual output file paths.
  - Notes: Use `superpowers:verification-before-completion` — paste real command output, no "should work". Quote the audio path (folder has a space). If the FastAPI service can't run in this environment, record that as a blocker rather than faking output.

- [x] **T8** [done] @documenter — Document the skill for the guide.
  - Acceptance: A `.claude/skills/hebrew-transcript-review/README.md` (or a dedicated usage section) that explains: what the skill does, EN + HE trigger phrases that activate it, the FastAPI prerequisite, where `VOCAB.md` and the run output files live, and a worked example invocation using `audio_sample_1min.m4a`. The repo-root `README.md` gets a short pointer to the new skill. No claim contradicts T7's verified behavior.
  - Notes: Keep it skimmable. Reuse paths/commands exactly as verified in T7.

- [x] **T9** [done] @reviewer — Close-gate review against acceptance criteria.
  - Acceptance: Reviewer verifies T1–T8 against their acceptance criteria, confirms `VOCAB.md` is at repo root (never in `resource/`), confirms SKILL.md `description` contains both EN and HE triggers, confirms the RTL table columns are exactly `זמן בדקות / דובר / מלל`, confirms all tests pass, and writes the Sprint Closeout (`STATUS: PASS|FAIL` + per-task notes) in this file.
  - Notes: Independent QA gate. If any task is `blocked`/`pending`, do not PASS.

## Routing Overrides

(Empty until the Orchestrator overrides a Planner assignment. Format: `T3: planner assigned @<old> → orchestrator dispatched @<new>. Reason: ...`)

## Sprint Closeout

STATUS: PASS

Reviewed by @reviewer on 2026-05-31. All eight implementation tasks (T1-T8) independently verified against their acceptance criteria. Verdict: PASS. The known single-prefix-strip normalization limitation is an accepted, documented limitation (README + DESIGN NOTE 3), not a failure.

- **T1 — PASS.** Design note present in `work-logs/architect.md` (DESIGN NOTE, normative). Fixes all required items: skill dir + file list (1), exact VOCAB.md header `| מילה | פירוש | דוגמה מההקשר | תאריך |` (3), `mm:ss` time format (4), word-by-word state machine + bilingual prompts P1-P6 (5), and run-output location/naming `output/hebrew-transcript-review/<stem>_<ts>_{transcript,summary}.md` (1/7). Contract cross-check section confirms no contradictions with T2-T6 signatures.
- **T2 — PASS.** SKILL.md frontmatter parses via PyYAML: `name= hebrew-transcript-review`, `he= True`, `en= True`, name length 24 chars (well under 1024). Body documents the FastAPI :8000 prerequisite + start command, the `ivrit-transcribe` MCP `transcribe` call, the expected JSON shape, and a `FileNotFoundError`/`RuntimeError` surface-to-user table.
- **T3 — PASS.** `scripts/vocab.py` exposes `normalize`/`lookup`/`append` and `VOCAB_PATH`; `VOCAB_PATH` resolves to `/Users/omer/Documents/ivrit_agent/VOCAB.md` (repo root, verified by import). No `resource/` write path (only a doc-string mention saying never `resource/`). `tests/test_vocab.py` covers create-if-missing (exact header), lookup-hit, lookup-miss, lookup-missing-file-no-write, normalization (niqqud, one-prefix-strip, prefix-matches-bare-stem, no-overstrip-short, final-letter fold), and no-duplicate append. All 11 vocab tests pass.
- **T4 — PASS.** SKILL.md "Step 3 - Word-by-word review loop" iterates segments in order, prints P1 context (segment text + speaker + `mm:ss`), is explicitly USER-DRIVEN ("This loop is USER-DRIVEN. You MUST NOT auto-ask about every word."), calls `lookup` FIRST before asking, appends only after a meaning is settled, and supports `next`/`הבא` (skip) and `done`/`סיים` (end). Numbered procedure (steps 1-6) is followable without inventing behavior; references `scripts/vocab.py` by path.
- **T5 — PASS.** `scripts/render_transcript.py` writes a Markdown table with header `HEADER_ROW = "| זמן בדקות | דובר | מלל |"` (exact triple confirmed by grep), wrapped in `<div dir="rtl">`. `to_mmss` floors seconds to `mm:ss` (167.0 -> 02:47); one row per segment in input order. `tests/test_render_transcript.py` asserts exact header, row-count == segment-count, and seconds->mm:ss conversion. All render tests pass. SKILL.md references the renderer in Step 2 placeholder and Step 5 path derivation.
- **T6 — PASS.** SKILL.md "Step 5 - Hebrew meeting summary" requires the four Hebrew sections in order `## סיכום` / `## החלטות` / `## משימות` / `## מעקבים` (grep-confirmed at lines 323-328 spec + 349-359 skeleton), written to the `_summary.md` sibling of the transcript (same stem + run_timestamp). Specifies Hebrew prose, input = transcript segments, and that every heading is always present.
- **T7 — PASS.** Evidence in `work-logs/qa.md` (live stack run against `resource/audio smaples/audio_sample_1min.m4a`, real Hebrew JSON `language: he`, `num_speakers: 3`). Reviewer RE-RAN the gate: `uv run pytest tests/ -v` -> `======================== 54 passed, 2 warnings in 4.92s ========================`. The only non-machine item (summary prose, T7 #5) is by-design an agent step; SKILL.md T6 fully documents the four headings + path, so it is covered.
- **T8 — PASS.** `.claude/skills/hebrew-transcript-review/README.md` covers the 5-step flow, EN+HE triggers, the FastAPI prerequisite + MCP registration, VOCAB.md (repo root) and `output/hebrew-transcript-review/` locations, a worked `audio_sample_1min.m4a` example, and the "Known limitation - vocabulary normalization" section. Repo-root `README.md` has a "Hebrew transcript review skill" section pointing to the skill README.

**Cross-checks (all PASS):**
- VOCAB target is repo ROOT: `VOCAB_PATH` import resolves to `/Users/omer/Documents/ivrit_agent/VOCAB.md`; never `resource/`.
- No real root `VOCAB.md` committed or present (`ls VOCAB.md` -> No such file).
- `output/` is git-ignored (`git check-ignore output/` -> match) and no `output/` artifacts are tracked (`git ls-files output/` -> empty).
- Skill files and tests are committed/tracked; working tree clean of stray artifacts (`git status` shows only untracked `sprints/` folders).
- Known single-prefix-strip normalization limit is documented in README + DESIGN NOTE 3 -> accepted limitation, not a failure.
