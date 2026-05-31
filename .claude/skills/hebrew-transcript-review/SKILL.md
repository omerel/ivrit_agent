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

<!-- ==========================================================================
     Step 3 — Word-by-word review loop  (added in T4)
     User-driven loop over segments backed by scripts/vocab.py (lookup/append);
     bilingual prompts; next/הבא skips, done/סיים ends.
     ========================================================================== -->

<!-- ==========================================================================
     Step 5 — Hebrew meeting summary  (added in T6)
     Agent writes Hebrew summary (סיכום / החלטות / משימות / מעקבים) to _summary.md.
     ========================================================================== -->
