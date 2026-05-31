# hebrew-transcript-review — usage

A Claude Code **skill** that transcribes a Hebrew audio recording and then walks
it with you interactively to learn unfamiliar words, building a personal
vocabulary list as you go. It produces an RTL transcript and a Hebrew meeting
summary as Markdown files.

> This README is the human-facing guide. The agent-facing procedure lives in
> [`SKILL.md`](SKILL.md); the deterministic helpers live in
> [`scripts/vocab.py`](scripts/vocab.py) and
> [`scripts/render_transcript.py`](scripts/render_transcript.py).

## What it does — the 5-step flow

1. **Transcribe** — calls the `ivrit-transcribe` MCP `transcribe` tool on your
   audio file. Returns diarized Hebrew JSON (`segments`, `language`,
   `num_speakers`).
2. **Render transcript** — `scripts/render_transcript.py` writes an RTL Markdown
   table with the columns `זמן בדקות | דובר | מלל` (one row per segment, times as
   `mm:ss`).
3. **Word-by-word review** — for each segment, the skill shows the text as
   context and lets **you** name the word(s) you don't understand. It is
   user-driven: it never quizzes you on every word. Each named word is looked up
   in `VOCAB.md` **first**; if known, it echoes the stored meaning; if not, you
   explain it (or confirm a proposed meaning) and it is appended to `VOCAB.md`.
4. *(folded into step 3)*
5. **Hebrew summary** — the agent writes a Hebrew meeting summary file with four
   sections: `## סיכום`, `## החלטות`, `## משימות`, `## מעקבים`.

## What activates it

The skill triggers on these phrases (from the `SKILL.md` `description`):

**English**

- "review/transcribe this meeting and teach me the words"
- "go over the transcript word by word"
- "transcribe and quiz me on the Hebrew words"

**Hebrew**

- "תמלל ותעבור איתי על המילים"
- "תעבור איתי מילה-מילה על התמלול"
- "תלמד אותי את המילים מההקלטה"
- "תמלל את הישיבה ותסביר לי מילים"

## Prerequisites

1. **The FastAPI transcription service must be running** (the MCP forwards to it):

   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   The MCP forwards to `http://localhost:8000` by default. To target a different
   host/port, set `TRANSCRIBE_API_URL` (e.g.
   `export TRANSCRIBE_API_URL=http://my-host:9000`). If the service isn't up, the
   `transcribe` call surfaces a `RuntimeError` — start the service with the
   command above and retry.

2. **The `ivrit-transcribe` MCP must be registered** with Claude Code:

   ```bash
   claude mcp add ivrit-transcribe -- uv run python -m mcp_code.server
   ```

   (See [`../../../mcp_code/README.md`](../../../mcp_code/README.md) for the full
   MCP contract.)

## Where files live

| What | Path |
| --- | --- |
| Your vocabulary list | `VOCAB.md` at the **repo root** (`/Users/omer/Documents/ivrit_agent/VOCAB.md`). Created automatically on the first word you add; never written under `resource/`. |
| Run outputs (transcript + summary) | `output/hebrew-transcript-review/` (git-ignored — run artifacts, not committed source). |

Output files are named from the audio file's stem plus a per-run timestamp, so
the transcript and summary always pair up:

```
output/hebrew-transcript-review/<audiostem>_<YYYYMMDD-HHMMSS>_transcript.md
output/hebrew-transcript-review/<audiostem>_<YYYYMMDD-HHMMSS>_summary.md
```

## Worked example

Use the 1-minute sample. **Quote the path** — the folder name `audio smaples`
contains a space.

First, in one terminal, start the service:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then ask Claude Code (either language works):

**English**

> Transcribe `"resource/audio smaples/audio_sample_1min.m4a"` and go over it
> with me word by word.

**Hebrew**

> תמלל את `"resource/audio smaples/audio_sample_1min.m4a"` ותעבור איתי
> מילה-מילה על התמלול.

For this sample the live run returns Hebrew JSON (`language: he`,
`num_speakers: 3`) and writes, for example:

```
output/hebrew-transcript-review/audio_sample_1min_20260531-230346_transcript.md
output/hebrew-transcript-review/audio_sample_1min_20260531-230346_summary.md
```

The transcript is an RTL `זמן בדקות | דובר | מלל` table; the summary has the four
Hebrew sections. Any words you explained during the pass are appended to the
root `VOCAB.md`.

## Known limitation — vocabulary normalization

Word matching in `scripts/vocab.py` strips **at most one** leading Hebrew prefix
letter (ו / ה / ב / כ / ל / מ / ש) before comparing. The rule is purely lexical:
it can't tell a genuine prefix from a root that simply *starts* with one of those
letters.

- Dedup and "already known, don't re-ask" are **reliable** for stems that do not
  begin with a prefix letter.
- A stored stem that itself **begins** with a prefix letter (e.g. `מליאה`) may not
  match an inflected/prefixed form of the same word (e.g. `במליאה`), because
  `מליאה` normalizes to `ליאה` while `במליאה` strips only its single leading `ב`
  to `מליאה` — the two keys differ, so you could be asked about the word twice or
  end up with two rows.

This is a documented behavior of the lexical normalizer, not a bug. If you hit a
duplicate for such a word, you can merge the rows in `VOCAB.md` by hand.
