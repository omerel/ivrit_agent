# Work Log — @qa

## 2026-05-31T23:05:00 — Task T7

**Attempted:** End-to-end validation of the `hebrew-transcript-review` skill chain:
unit tests, deterministic helper smoke tests (render + vocab), and a best-effort
live-stack run against the 1-minute Hebrew sample. Invoked
`superpowers:verification-before-completion` and `superpowers:systematic-debugging`.

**Did / evidence:**

1. **Unit tests — PASS.** `uv run pytest tests/ -v` →
   `======================== 54 passed, 2 warnings in 4.80s ========================`.
   Includes all `test_vocab.py` (12) and `test_render_transcript.py` (16) cases.

2. **render_transcript smoke test — PASS.** Built a 3-segment fake result (Hebrew
   text, speakers, starts 0/12/167s) and called `render(...)`. Wrote
   `output/hebrew-transcript-review/audio_sample_1min_20260531-235900_transcript.md`.
   Header exactly `| זמן בדקות | דובר | מלל |`; DATA_ROW_COUNT 3 == 3 segments;
   167s → `02:47`. Confirmed.

3. **vocab smoke test — PASS (with one investigation).** Monkeypatched
   `vocab.VOCAB_PATH` to a tmp file (real root `VOCAB.md` never created — verified
   absent before and after). Confirmed: lookup on missing file → None with no write;
   append new Hebrew word → lookup hit returns the row dict; lookup of a different
   word (`שולחן`) → None (the "first place to check" miss path); append a
   niqqud+prefix variant of an already-stored prefix-free stem (`דירה`/`בּדִירָה`) →
   still ONE row.
   - **Investigation (not a code bug):** my first dedup attempt used `מליאה` +
     variant `בּמליאה` and produced TWO rows. Systematic-debugging traced
     `normalize`: `מליאה` starts with the prefix letter `מ`, so it normalizes to
     `ליאה`, while `במליאה` strips only its single leading `ב` → `מליאה`; the two
     keys differ. This is the DOCUMENTED §3 limitation ("at most ONE leading prefix
     letter is stripped; matching unreliable for stems beginning with ו/ה/ב/כ/ל/מ/ש")
     — the implementation behaves exactly as specified, and the test suite correctly
     uses the prefix-free stem `דירה`. No implementation defect; my poison input.

4. **Live stack — PASS (worked).** A transcribe service was ALREADY running on
   :8000 (PID 86120, `/health` → `{"status":"ok"}`, routes `/health` + `/transcribe`);
   I did NOT start or stop it (left the pre-existing process untouched). Invoked the
   `ivrit-transcribe` MCP `transcribe` tool (real code path, `mcp_code/server.py`)
   against the quoted `resource/audio smaples/audio_sample_1min.m4a`. Returned real
   Hebrew JSON: `language: he`, `num_speakers: 3`, 3 segments, ~75s on CPU. Rendered
   that real result → `output/hebrew-transcript-review/audio_sample_1min_20260531-230346_transcript.md`
   with the exact header, 3 rows == 3 segments, `<div dir="rtl">` wrapper, mm:ss
   conversion (00:00 / 00:29 / 00:59). No faked output.

**Acceptance items (T7):**
- (1) transcript obtained — PASS (live, real Hebrew).
- (2) word-by-word checks VOCAB before asking + appends a valid row — PASS at helper
  level (lookup-before-append + valid row); the interactive Q&A is SKILL.md agent
  instructions, exercised here via the deterministic `vocab.lookup`/`append` path.
- (3) re-naming the same (prefix-free) word does NOT re-ask — PASS (lookup hit /
  idempotent append → one row).
- (4) RTL transcript .md with `זמן בדקות / דובר / מלל` — PASS (both fake and live).
- (5) Hebrew summary .md with four sections — NOT machine-validated: the summary is
  pure agent-generated prose (no script), so it can only be produced inside a live
  skill session, not by a deterministic harness. SKILL.md Step 5 documents the four
  required headings (`סיכום`/`החלטות`/`משימות`/`מעקבים`) and the `_summary.md` path
  derivation; the path-derivation one-liner is covered by the renderer that T7 ran.
  Flagged for the live-session demo / @reviewer rather than blocked.
- (6) all unit tests pass — PASS (54/54).

**Files touched:** `plan.md` (T7 → done); this work-log.
**Output artifacts produced (git-ignored, NOT committed):**
- `output/hebrew-transcript-review/audio_sample_1min_20260531-230346_transcript.md` (live run)
- `output/hebrew-transcript-review/audio_sample_1min_20260531-235900_transcript.md` (fake-data smoke)
Real root `VOCAB.md` was never created; vocab smoke tests used a tmp path only.

**Blockers:** None. Live stack worked. The only non-machine-verifiable item is the
Hebrew summary prose (5), which is by design an agent step, not a script — recommend
the live-session demo confirm it for @reviewer's gate.
