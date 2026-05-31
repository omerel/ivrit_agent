# Work Log — @architect

## 2026-05-31T23:05:00 — Task T1

**Attempted:** Design the `hebrew-transcript-review` skill — file layout, end-to-end flow,
data contracts (VOCAB.md schema, render contract, summary contract), the word-by-word loop
state machine, and the SKILL.md description triggers. Decisions only; T2–T6 implement.

**Did:** Read CLAUDE.md (§3/§4/§5), the full plan (Context + T1–T9), `mcp_code/server.py`
+ `mcp_code/README.md`, `.claude/team.md`, the existing `using-git/SKILL.md` for structure,
`.gitignore`, and invoked `superpowers:writing-skills` (CSO: description = triggers only).
Wrote the design note below — it is the spec T2–T6 implement.

**Files touched:** `plan.md` (T1 → done); this work-log (design note).

**Blockers:** None.

---

# DESIGN NOTE — `hebrew-transcript-review` skill (spec for T2–T6)

This note is normative. Where it gives a function signature, a column header, a prompt string,
or a path, implement it verbatim. Do not introduce behavior not described here without
flagging it back to the Orchestrator. Locked decisions from the plan Context (skill name,
VOCAB at repo root + its columns, `mm:ss` time format, user-driven loop) are restated here so
the contracts are self-contained — they are NOT up for re-litigation.

Skill type: **Reference / Technique** (a how-to procedure executed by the live agent), NOT a
discipline-enforcing skill. No pressure-baseline test is required; correctness is validated by
the helper unit tests (T3/T5) plus the live end-to-end run (T7).

---

## 1. File layout

All skill files live under `.claude/skills/hebrew-transcript-review/`:

```
.claude/skills/hebrew-transcript-review/
  SKILL.md                     # T2 scaffold; T4 loop procedure; T6 summary step
  scripts/
    vocab.py                   # T3 — VOCAB.md lookup/append + Hebrew normalization
    render_transcript.py       # T5 — transcribe JSON -> RTL transcript .md
  README.md                    # T8 — guide-facing usage doc
```

Helper scripts go under `scripts/` (per writing-skills: reusable tools as separate files).
No template files are needed — the transcript table and the summary skeleton are emitted by
`render_transcript.py` / written inline by the agent, so a static template would only drift.

**Tests** (T3/T5) live in the repo-root `tests/` dir (consistent with the existing
`tests/test_*.py` layout), named:
- `tests/test_vocab.py`        — selected by `uv run pytest tests/ -k vocab`
- `tests/test_render_transcript.py` — selected by `uv run pytest tests/ -k render`

Import path: scripts are plain modules under a non-package dir, so tests load them via an
explicit path. Recommended in each test file:
```python
import importlib.util, pathlib
_p = pathlib.Path(__file__).resolve().parents[1] / ".claude/skills/hebrew-transcript-review/scripts/vocab.py"
spec = importlib.util.spec_from_file_location("vocab", _p)
vocab = importlib.util.module_from_spec(spec); spec.loader.exec_module(vocab)
```
(T3/T5 may instead add an `__init__.py` + sys.path insert; either is fine as long as no
`scripts/` package name collides with the existing `app`/`mcp_code` packages.)

### Run-output location & naming (T5 transcript, T6 summary)

Run outputs are **generated artifacts**, not source. They go in a repo-root, git-ignored dir:

```
output/hebrew-transcript-review/
  <audiostem>_<YYYYMMDD-HHMMSS>_transcript.md
  <audiostem>_<YYYYMMDD-HHMMSS>_summary.md
```

- `<audiostem>` = the audio filename without extension, slugified (lowercase, spaces/non
  `[a-z0-9-]` → `-`). For `audio_sample_1min.m4a` → `audio_sample_1min`.
- `<YYYYMMDD-HHMMSS>` = local timestamp at run start; the SAME timestamp string is used for
  both files of one run so they pair up.
- Example pair: `output/hebrew-transcript-review/audio_sample_1min_20260531-231012_transcript.md`
  and `..._20260531-231012_summary.md`.
- The skill MUST create `output/hebrew-transcript-review/` if missing.

**Git:** add `output/` to `.gitignore` (T2 or T5 — whoever first writes there). Generated
artifacts are not committed; T7 records the actual produced paths in its work-log instead.

`render_transcript.py` owns building the transcript path from `(audio_path, run_timestamp)` so
naming stays in one place — see §4. The summary path is the sibling with the `_summary.md`
suffix and the identical stem+timestamp.

---

## 2. End-to-end flow (5 ordered steps)

Legend: **[PY]** = deterministic Python helper · **[AGENT]** = live-agent instruction in SKILL.md.

1. **Transcribe** `[AGENT]` — user gives an `audio_path`. Verify prerequisite (FastAPI service
   on :8000; if not running, tell the user the start command). Call the `ivrit-transcribe` MCP
   `transcribe` tool with `audio_path`. Surface `FileNotFoundError` (bad path — quote paths with
   spaces) and `RuntimeError` (API non-2xx / service down) to the user verbatim. Capture the
   returned JSON dict and a single `run_timestamp` (`YYYYMMDD-HHMMSS`) for the whole run.
2. **Render transcript** `[PY]` — call `render_transcript.render(result, audio_path, run_timestamp)`
   → writes the RTL `זמן בדקות | דובר | מלל` table to the `_transcript.md` path and returns it.
   Deterministic: tokenization-free, just seconds→`mm:ss` + table assembly.
3. **Word-by-word review** `[AGENT]` loop driving `[PY]` lookups — walk segments in order; per
   segment show context; user names unknown word(s); for each word call
   `vocab.lookup(word)` `[PY]` first; known → echo meaning; unknown → user explains OR agent
   proposes+confirms, then `vocab.append(...)` `[PY]`. `next`/`הבא` skips, `done`/`סיים` ends.
   The Q&A itself (deciding prompts, judging answers, proposing meanings) is **[AGENT]**;
   normalize/lookup/append are **[PY]** (deterministic, in `vocab.py`). See §5.
4. **(folded into 3)** — there is no separate step; the plan's "5 steps" = steps 1,2,3,5 here
   plus the implicit "gather words into VOCAB" which IS step 3. Kept the numbering 1/2/3/5 to
   match the plan's "step 5 = summary" wording.
5. **Hebrew summary** `[AGENT]` — from the transcript segments, the agent writes a Hebrew
   summary with the four required sections to the `_summary.md` path (same stem+timestamp). See §7.

Determinism boundary, explicit: normalization, lookup, append, seconds→mm:ss, and table/file
writing are Python (testable). Everything requiring judgment or natural-language interaction
(transcription trigger, interactive Q&A, proposing meanings, summary prose) is agent
instructions in SKILL.md.

---

## 3. VOCAB.md schema + normalization + `vocab.py` contract

### File location & format
Repo root: `/Users/omer/Documents/ivrit_agent/VOCAB.md`. Never under `resource/`.

**Exact header (create-if-missing writes exactly these three lines, then data rows):**
```
| מילה | פירוש | דוגמה מההקשר | תאריך |
| --- | --- | --- | --- |
```
(First content line above is the header row; second is the Markdown separator row. The plan's
Context names the columns "מילה / פירוש / דוגמה מההקשר / תאריך" — use those bare Hebrew labels,
no parenthetical English in the actual file.)

**Sample data row:**
```
| מליאה | ישיבת המליאה — הרכב מלא של חברי הוועדה/הפרלמנט | "נצביע על זה במליאה הבאה" | 2026-05-31 |
```

- `תאריך` is ISO `YYYY-MM-DD` (the date the row was added).
- The word stored in column 1 is the **surface word as the user named it** (human-readable),
  NOT the normalized key. Normalization is applied only for *matching*, never for *display*.
- A literal `|` inside any cell MUST be escaped as `\|` so the table stays well-formed.

### Normalization rule (used for lookup matching and duplicate detection)
`normalize(word)` applies, in order:
1. Unicode NFC, then **strip niqqud / cantillation**: remove all chars in U+0591–U+05C7.
2. **Strip punctuation & maqaf**: remove maqaf `־` (U+05BE), geresh/gershayim `׳ ״`, ASCII
   quotes/periods/commas, and the RTL/LTR marks (U+200E/U+200F) if present.
3. **Strip a single leading prefix letter** from the set `ו ה ב כ ל מ ש` IFF the remaining
   stem is length ≥ 2 (so single-letter words and the bare prefix aren't over-stripped). Strip
   at most ONE prefix letter (keep it simple and predictable; document this limit).
4. **Normalize final-letter forms** to their medial forms: `ך→כ ם→מ ן→נ ף→פ ץ→צ`.
5. Trim surrounding whitespace.

The result is the **lookup key**. lookup and the no-duplicate check both compare on
`normalize(...)` equality, so e.g. " והמליאה" matches a stored "מליאה".

### `vocab.py` function signatures (contract for T3)
```python
VOCAB_PATH: pathlib.Path           # repo-root VOCAB.md (module-level default; tests override)

def normalize(word: str) -> str: ...
    # the rule above; pure, no I/O. Exposed for testing.

def lookup(word: str) -> dict | None: ...
    # Create-if-missing is NOT triggered by lookup of a non-existent file:
    #   if VOCAB.md is absent, lookup returns None (no write).
    # Reads VOCAB.md, returns the FIRST row whose col-1 word normalizes equal to
    # normalize(word), as {"word","meaning","example","date"}; else None.

def append(word: str, meaning: str, example: str, date: str) -> None: ...
    # Creates VOCAB.md with the exact header (above) if missing, then appends ONE
    # well-formed row. Idempotent on the normalized key: if normalize(word) already
    # present, it is a no-op (does NOT add a second row, does NOT mutate the existing
    # row). Escapes '|' in cells. `date` is caller-supplied ISO YYYY-MM-DD.
```
- "create-if-missing" behavior: only `append` creates the file (with header + the new row).
  `lookup` on a missing file returns `None` and writes nothing.
- For T7's re-ask test: naming the same word twice → second `lookup` is a hit → no re-ask;
  and if append were called again it is a no-op (one row total).
- The skill calls `lookup` BEFORE asking the user, and `append` only after a meaning is settled.
  T3 should allow `VOCAB_PATH` to be monkeypatched (e.g. via an env var or module attribute)
  so tests write to a tmp file, not the real root VOCAB.md.

---

## 4. `render_transcript.py` contract (for T5)

```python
def to_mmss(seconds: float) -> str: ...
    # floor to whole seconds; m = total//60, s = total%60; return f"{m:02d}:{s:02d}".
    # 167.0 -> "02:47", 5.0 -> "00:05", 605.4 -> "10:05". (No hours field; mm can exceed 59
    # for long audio, e.g. 3725s -> "62:05" — acceptable, format stays mm:ss.)

def output_path(audio_path: str, run_timestamp: str) -> pathlib.Path: ...
    # output/hebrew-transcript-review/<slug(stem)>_<run_timestamp>_transcript.md (see §1).

def render(result: dict, audio_path: str, run_timestamp: str) -> pathlib.Path: ...
    # Input `result` = the transcribe tool JSON dict (§ MCP shape).
    # Creates the output dir if missing, writes the .md, returns the written Path.
```

**Input** (passed through from the MCP tool, unchanged):
```
{ "segments": [{"speaker": str, "text": str, "start": float, "end": float}, ...],
  "language": str|null, "num_speakers": int|null }
```

**Output file** — exact structure (one row per segment, chronological = input order):
```markdown
<!-- transcript for: <audio basename> · generated <run_timestamp> -->
<div dir="rtl">

| זמן בדקות | דובר | מלל |
| --- | --- | --- |
| 00:00 | SPEAKER_00 | ... |
| 02:47 | SPEAKER_01 | ... |

</div>
```

- Columns are EXACTLY `זמן בדקות | דובר | מלל` (this exact triple — T9 checks it).
- `זמן בדקות` = `to_mmss(segment["start"])`. `דובר` = `segment["speaker"]`.
  `מלל` = `segment["text"]` with any `|` escaped as `\|` and newlines collapsed to spaces.
- **RTL hint:** wrap the table in `<div dir="rtl"> … </div>` (load-bearing — this is the
  reliable RTL mechanism in rendered Markdown; the CLI itself does not render RTL, so the .md
  file is the deliverable). Do NOT rely on bare RLM marks alone.
- Row count MUST equal `len(result["segments"])` (T5 test asserts this).
- Empty `segments` → still write a valid file with the header rows and zero data rows.

---

## 5. Word-by-word loop state machine (for T4) + exact bilingual prompts

State per pass: `i` = current segment index (0-based), iterate in order. The loop is
**user-driven** — the skill MUST NOT auto-quiz every word; it only acts on words the user names.

```
For each segment i in order:
  STATE show_context  -> print the segment context block (prompt P1), then go to await_words
  STATE await_words   -> read user input:
        - "next" or "הבא"  -> skip this segment, i := i+1, back to show_context
        - "done" or "סיים" -> end the pass (go to STATE end)
        - otherwise the user named one or more words -> for each named word: handle_word,
          then re-prompt P2 ("any more words in this segment?"); same next/done rules apply
  STATE handle_word(w):
        key := vocab.lookup(w)
        if key is not None:  print P3 (known — echo stored meaning); return
        else:                # unknown
            ask P4 (user explains) OR if the agent is confident, propose via P5 and confirm
            once a meaning is settled:
                vocab.append(word=w, meaning=<settled>, example=<segment text snippet>,
                             date=<today ISO>)
                print P6 (added confirmation); return
  STATE end -> proceed to step 5 (Hebrew summary)
```

The agent uses `lookup` BEFORE asking (so known words never re-ask — satisfies T7 #3). The
`example` stored is a short snippet of the current segment text (the word in context).

### Exact user-facing prompt strings (T4 pastes these verbatim; bilingual EN + HE)

**P1 — segment context (shown at start of each segment):**
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

**P5 — agent proposes a meaning for the user to confirm (used after 'propose'/'הצע', or when
the agent is confident):**
```
הצעה לפירוש של "<word>": <proposed meaning>. לאשר? (כן/לא · yes/no)
Proposed meaning for "<word>": <proposed meaning>. Confirm? (yes/no · כן/לא)
```

**P6 — confirmation that the word was added to VOCAB.md:**
```
נוסף ל-VOCAB.md: "<word>" — <meaning>.
Added to VOCAB.md: "<word>" — <meaning>.
```

Command tokens recognized (case-insensitive, trimmed): skip = `next` / `הבא`; end = `done` /
`סיים`; request-proposal = `propose` / `הצע`; confirm = `yes` / `כן`; reject = `no` / `לא`.

---

## 6. SKILL.md `description` frontmatter (for T2; CSO = triggers only, no workflow summary)

`name: hebrew-transcript-review`

```
description: Use when the user wants to transcribe a Hebrew audio recording and then go over it interactively to learn unfamiliar words, build a vocabulary list, and get an RTL transcript plus a Hebrew summary. English triggers: "review/transcribe this meeting and teach me the words", "go over the transcript word by word", "transcribe and quiz me on the Hebrew words". Hebrew triggers: "תמלל ותעבור איתי על המילים", "תעבור איתי מילה-מילה על התמלול", "תלמד אותי את המילים מההקלטה", "תמלל את הישיבה ותסביר לי מילים".
```
(Under 1024 chars total with `name`. Pure triggering conditions in both languages — no "then
it renders…/then it summarizes…" workflow recap, per writing-skills CSO.)

---

## 7. Hebrew summary step (for T6)

**[AGENT]**-generated Hebrew prose written to the `_summary.md` path (§1: same stem+timestamp as
the transcript, `_summary.md` suffix). Input = the transcript segments. Output is in **Hebrew**.

Exact section skeleton the agent fills (wrap RTL like the transcript):
```markdown
<!-- summary for: <audio basename> · generated <run_timestamp> -->
<div dir="rtl">

# סיכום פגישה

## סיכום
<2–5 משפטים: על מה הייתה הפגישה ועיקרי הדברים>

## החלטות
- <החלטה 1>
- <החלטה 2>

## משימות
- <מטלה — אחראי אם ידוע>

## מעקבים
- <נושא פתוח / לבירור בהמשך>

</div>
```

Four required sections, in this order, with these exact Hebrew headings: `סיכום`, `החלטות`,
`משימות`, `מעקבים`. If a section has no items, the agent writes a short Hebrew placeholder
(e.g. `אין החלטות שתועדו`) rather than omitting the heading — so the file always has all four.

---

## Contract cross-check (no contradictions)

- Time format `mm:ss` is defined once in §4 `to_mmss` and used by both §2 step 2 and the §5 P1
  context line. ✔
- VOCAB columns `מילה | פירוש | דוגמה מההקשר | תאריך` identical in §3 header and the §5 append
  call args (`word/meaning/example/date`). ✔
- `vocab.lookup`/`append` signatures in §3 match the calls in §5. ✔
- `render_transcript.render(result, audio_path, run_timestamp)` in §4 matches §2 step 2 and the
  §1 naming convention; summary path is its sibling. ✔
- Output dir `output/hebrew-transcript-review/` is git-ignored (§1), so T7 records real paths in
  its log rather than committing artifacts. ✔
- Skill name + description (§6) match the plan's locked name and EN/HE trigger requirement. ✔
