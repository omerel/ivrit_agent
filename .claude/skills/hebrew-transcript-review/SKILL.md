---
name: hebrew-transcript-review
description: 'Use when the user wants to transcribe a Hebrew audio recording and then go over it interactively to learn unfamiliar words, build a vocabulary list, and get an RTL transcript plus a Hebrew summary. English triggers: "review/transcribe this meeting and teach me the words", "go over the transcript word by word", "transcribe and quiz me on the Hebrew words". Hebrew triggers: "תמלל ותעבור איתי על המילים", "תעבור איתי מילה-מילה על התמלול", "תלמד אותי את המילים מההקלטה", "תמלל את הישיבה ותסביר לי מילים".'
---

# Hebrew Transcript Review

## Overview

Transcribe a Hebrew audio file, then walk it interactively to learn unfamiliar
words (backed by a root-level `VOCAB.md`), and produce an RTL transcript plus a
Hebrew meeting summary as Markdown files.

The flow has five ordered steps:

1. **Transcribe** — call the `ivrit-transcribe` MCP `transcribe` tool (this file).
2. **Render transcript** — `scripts/render_transcript.py` writes the RTL table.
3. **Word-by-word review** — interactive loop backed by `scripts/vocab.py`.
4. *(folded into step 3)*
5. **Hebrew summary** — agent-written Hebrew summary Markdown file.

This document covers **Step 1**. Steps 2/3 and 5 are appended in later sections
below (see the placeholders) — do not invent their behavior here.

## When to Use

- The user gives an audio file (`.m4a`, `.wav`, `.mp3`, …) and wants it
  transcribed and then explained / studied word by word.
- The user asks (EN or HE) to "go over the transcript and teach me the words",
  "transcribe the meeting and explain words", "תעבור איתי מילה-מילה על התמלול".

Do NOT use this skill for: plain transcription with no review step (use the
`ivrit-transcribe` MCP directly), or non-Hebrew audio.

## Prerequisites

The `ivrit-transcribe` MCP forwards to the project's FastAPI `/transcribe`
service, which **must be running first**:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

By default the MCP forwards to `http://localhost:8000`. To target a different
host/port, set `TRANSCRIBE_API_URL` (e.g. `export TRANSCRIBE_API_URL=http://my-host:9000`).

If the service is not running, the `transcribe` call surfaces a `RuntimeError`
(see below). Tell the user to start the service with the command above before
retrying — do not attempt to start it silently on their behalf.

## Step 1 — Transcribe the audio

1. Get the `audio_path` from the user. **Quote paths that contain spaces** — the
   sample audio lives at `resource/audio smaples/audio_sample_1min.m4a` (the
   folder name has a literal space and a typo).
2. Capture a single `run_timestamp` for the whole run in the format
   `YYYYMMDD-HHMMSS` (local time at run start). Reuse this same string for the
   transcript and summary output files so they pair up.
3. Call the `ivrit-transcribe` MCP **`transcribe`** tool with `audio_path`. Do
   NOT re-implement the HTTP call — the MCP owns that logic. (See
   `mcp_code/README.md` for the tool contract.)

### Expected result shape

The tool returns the FastAPI JSON unchanged:

```json
{
  "segments": [
    {"speaker": "SPEAKER_00", "text": "...", "start": 0.0, "end": 3.2}
  ],
  "language": "he",
  "num_speakers": 1
}
```

- `segments` — diarized chunks in chronological order; `text` is **Hebrew**.
- `language` — detected language code or `null`.
- `num_speakers` — speaker count or `null`.

Keep this dict in memory; later steps render and review it.

### Error handling — surface to the user verbatim

| Error | Cause | What to tell the user |
| --- | --- | --- |
| `FileNotFoundError` | `audio_path` is not an existing file (the MCP checks before calling the API). | The path doesn't exist. Re-quote it (mind spaces) and confirm the file is on this machine. |
| `RuntimeError` | The FastAPI service returned a non-2xx response, or is not running. | Show the HTTP status from the message. Most often the service isn't up — point them at the `uv run uvicorn …` command in Prerequisites. |

Surface the raised error message to the user as-is; do not swallow or retry it
automatically.

<!-- ==========================================================================
     Step 2 — Render RTL transcript  (added in T5)
     Will call scripts/render_transcript.py: render(result, audio_path, run_timestamp).
     ========================================================================== -->

## Step 3 — Word-by-word review loop

This is the heart of the skill. After Step 2 has rendered the transcript, walk
the **same `result["segments"]`** in chronological order (input order) and let the
user learn unfamiliar words, backed by the root-level `VOCAB.md`.

**This loop is USER-DRIVEN. You MUST NOT auto-ask about every word.** Show each
segment as context and let the user name only the word(s) they don't understand.
Never quiz, define, or append a word the user did not name (except a meaning you
*propose* and the user *confirms* — see below).

### How to call the `scripts/vocab.py` helper

All VOCAB matching/writing is delegated to `scripts/vocab.py` (do NOT re-implement
normalization or edit `VOCAB.md` by hand). The module is a plain file (not an
installed package), so load it by path. From the **repo root**, run a one-liner per
operation. Substitute the real values for the `<...>` placeholders.

**Look up a word (call this FIRST, before asking the user anything about it):**

```bash
uv run python -c '
import importlib.util, pathlib, json, sys
p = pathlib.Path(".claude/skills/hebrew-transcript-review/scripts/vocab.py")
spec = importlib.util.spec_from_file_location("vocab", p)
vocab = importlib.util.module_from_spec(spec); spec.loader.exec_module(vocab)
row = vocab.lookup(sys.argv[1])
print(json.dumps(row, ensure_ascii=False))
' "<word>"
```

- Output `null` → the word is **unknown** (not in `VOCAB.md`).
- Output a JSON object `{"word","meaning","example","date"}` → the word is **known**;
  use its `meaning` field for prompt P3.

**Append a settled word** (only after a meaning is settled — user-explained or
user-confirmed). Writes ONE row to repo-root `VOCAB.md`; idempotent on the
normalized key, so a re-append is a safe no-op:

```bash
uv run python -c '
import importlib.util, pathlib, sys
p = pathlib.Path(".claude/skills/hebrew-transcript-review/scripts/vocab.py")
spec = importlib.util.spec_from_file_location("vocab", p)
vocab = importlib.util.module_from_spec(spec); spec.loader.exec_module(vocab)
vocab.append(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
' "<word>" "<meaning>" "<example>" "<date>"
```

- `<word>` = the surface word **exactly as the user named it** (human-readable; do
  NOT pass a normalized form — `vocab.py` normalizes internally for matching).
- `<meaning>` = the settled explanation (user's wording, or the meaning the user
  confirmed).
- `<example>` = a short snippet of the **current segment text** that contains the
  word (the word in context).
- `<date>` = today's date in ISO `YYYY-MM-DD` (today is the run date).

`VOCAB.md` is the **only** file written. Never write vocabulary to `resource/` or
anywhere else.

### Command tokens (case-insensitive, trimmed before matching)

| Meaning | English | Hebrew |
| --- | --- | --- |
| skip to next segment | `next` | `הבא` |
| end the pass early | `done` | `סיים` |
| ask the agent to propose a meaning | `propose` | `הצע` |
| confirm a proposed meaning | `yes` | `כן` |
| reject a proposed meaning | `no` | `לא` |

Trim whitespace and lowercase the Latin tokens before comparing. Anything that is
not one of these command tokens is treated as the user **naming a word** (or words).

### Procedure (follow exactly — do not invent behavior)

Iterate `segments` with a 0-based index `i`, in order. Let `total = len(segments)`.

1. **Show context.** For segment `i`, print prompt **P1** verbatim, substituting:
   - `<n>` = `i + 1` (1-based), `<total>` = `total`.
   - `<speaker>` = `segments[i]["speaker"]`.
   - `<mm:ss>` = the `start` seconds of this segment formatted as `mm:ss`. Reuse the
     same conversion as the transcript renderer
     (`scripts/render_transcript.py:to_mmss`); e.g. `167.0` → `02:47`.
   - `<segment text>` = `segments[i]["text"]`.

2. **Await the user's input** and branch on it:
   - `next` / `הבא` → skip this segment: set `i := i + 1` and go to step 1 (or end if
     `i == total`).
   - `done` / `סיים` → end the pass: go to step 6.
   - otherwise → the user named one or more words. Handle **each named word** with
     step 3, in the order given.

3. **Handle one named word `w`** — call `lookup` FIRST (see the helper one-liner above):
   - **Known** (lookup returns a JSON object): print prompt **P3** verbatim with the
     stored `meaning`. Do **not** re-ask and do **not** append. Move to the next named
     word (or step 4 if none remain). This satisfies the "known words never re-ask"
     requirement.
   - **Unknown** (lookup returns `null`): print prompt **P4** verbatim and read the
     user's reply:
     - If the user explains the word in their own words → that text is the settled
       meaning. Go to step 5.
     - If the user types `propose` / `הצע` (or you are confident and want to offer
       one) → print prompt **P5** verbatim with your proposed meaning, then read the
       user's reply:
       - `yes` / `כן` → the proposed meaning is settled. Go to step 5.
       - `no` / `לא` → ask the user to explain it instead (re-issue P4 without the
         propose hint); their reply is the settled meaning. Go to step 5.

4. **Ask for more words in the same segment.** After a word is handled (echoed as
   known, or appended), print prompt **P2** verbatim. Re-apply the step-2 branching to
   the reply (`next`/`הבא`, `done`/`סיים`, or another word → step 3). When the user
   moves on (`next`/`הבא`) or no more words are named for this segment, set
   `i := i + 1` and go to step 1 (or end if `i == total`).

5. **Append the settled word.** Call `append` (see the helper one-liner above) with
   `word=w` (surface form as named), `meaning=<settled>`,
   `example=<snippet of segments[i]["text"]>`, `date=<today ISO>`. Then print prompt
   **P6** verbatim with the word and meaning. Return to step 4 (ask for more words in
   this segment).

6. **End of pass.** When the user issues `done`/`סיים`, or all segments are exhausted
   (`i == total`), the word-by-word pass is complete. Proceed to Step 5 (Hebrew
   summary) below.

### Exact bilingual prompt strings (paste verbatim; substitute only the `<...>` parts)

**P1 — segment context (shown at the start of each segment):**

```
--- קטע <n>/<total> · דובר <speaker> · <mm:ss> ---
<segment text>

Which word(s) here don't you understand? Type the word(s), or 'next'/'הבא' to skip, 'done'/'סיים' to finish.
אילו מילים כאן אינך מבין/ה? כתוב/כתבי את המילה/ים, או 'הבא' לדילוג ו'סיים' לסיום.
```

**P2 — after handling a word, ask for more in the same segment:**

```
Any other word in this segment? (word / 'next'/'הבא' / 'done'/'סיים')
עוד מילה בקטע הזה? (מילה / 'הבא' / 'סיים')
```

**P3 — word already known (VOCAB hit); echo the stored meaning:**

```
"<word>" כבר מופיעה ב-VOCAB: <stored meaning>.
"<word>" is already in your vocabulary: <stored meaning>.
```

**P4 — unknown word, ask the user to explain:**

```
לא מצאתי את "<word>" ב-VOCAB. איך היית מסביר/ה אותה? (או כתוב/כתבי 'הצע' כדי שאציע פירוש)
"<word>" isn't in your vocabulary yet. How would you explain it? (or type 'propose'/'הצע' and I'll suggest one)
```

**P5 — agent proposes a meaning for the user to confirm (used after 'propose'/'הצע',
or when you are confident):**

```
הצעה לפירוש של "<word>": <proposed meaning>. לאשר? (כן/לא · yes/no)
Proposed meaning for "<word>": <proposed meaning>. Confirm? (yes/no · כן/לא)
```

**P6 — confirmation that the word was added to VOCAB.md:**

```
נוסף ל-VOCAB.md: "<word>" — <meaning>.
Added to VOCAB.md: "<word>" — <meaning>.
```

<!-- ==========================================================================
     Step 5 — Hebrew meeting summary  (added in T6)
     Agent writes Hebrew summary (סיכום / החלטות / משימות / מעקבים) to _summary.md.
     ========================================================================== -->
