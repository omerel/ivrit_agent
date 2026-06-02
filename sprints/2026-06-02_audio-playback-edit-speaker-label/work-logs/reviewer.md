## 2026-06-02T16:30:00+0300 — Sprint review (T0–T5)

**What:** Independent QA gate for sprint `audio-playback-edit-speaker-label`. Verified all six `done` tasks against acceptance criteria by inspecting `app/static/index.html`, `README.md`, `tests/test_web_features.py`, and the four work-logs, plus running the cross-cutting checks. Wrote `STATUS: PASS` in `plan.md` Sprint Closeout.

**Commands run + evidence:**
- `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → no output, exit 1 (offline invariant holds).
- `grep -c 'lang="he" dir="rtl"'` → 1; `grep -c '/transcribe'` → 3; `grep -c 'type="file"'` → 2; `grep -c 'fetch("/transcribe'` → 1 (single contract call).
- `git diff --name-only 119be99..HEAD` → `README.md`, `app/static/index.html`, `tests/test_web_features.py` only. NO `app/main.py` / `app/schemas.py` change → backend UNCHANGED. (Current sprint folder is untracked/uncommitted, so it does not show in the diff — left for the orchestrator to commit.)
- Existing IDs intact: dropzone/fileInput/filebar/fileName/fileSize/submitBtn/clearBtn = 1 each; speakerLegend = 1; speakerNames = 10 refs.
- Feature 1: `#uploadPreview` (835) / `#uploadPreviewAudio` (837); createObjectURL in setFile (1081, revoke-first 1080); clearFile revoke+clear (1092–1094); beforeunload revokeUploadUrl (1847). Distinct from `#recPreview`.
- Feature 2: buildReassignControl (1620) `<select data-turn-idx>` + `דובר/ת חדש/ה` (1647); nextFreeSpeakerLabel SPEAKER_NN (1356); change handler mutates workingSegments refs then buildTranscript (1650–1659); lastResult.turns rebuilt from working copy (1610).
- T5 no-merge: freezeTurns tags seg._turn from initial consecutive grouping (1475–1483); groupByFrozenTurn groups by seg._turn (1316–1330); buildTranscript uses it (1520). seg._turn NOT sent to /transcribe (FormData appends only selectedFile, 1740–1741) and NOT in buildMarkdown (1684–1695); per-run clone drops prior _turn (1466–1468).
- JS sanity: extracted the single inline `<script>` (37,819 chars) → `node --check` OK.
- Whole suite: `.venv/bin/python -m pytest -v` → `72 passed, 2 warnings in 5.52s` (fully green; warnings pre-existing Starlette/opentelemetry deprecations).
- README: upload-player bullet (123–130), reassignment bullet (150–161) with T5 followup "turn structure is preserved … never merges turns together" (156–157); no remaining "merge on reassignment" claim. MD-export bullet reflects reassignments (162–165).
- Test file asserts only on tokens confirmed present (uploadPreview/uploadPreviewAudio/createObjectURL/data-turn-idx/workingSegments/דובר-ת-חדש-ה/single fetch).

**Verdict:** STATUS: PASS. Residual risk flagged in closeout: no live-browser interaction test was run (playback/reassignment-no-merge/MD export verified by code review + node --check + static contract tests only).

**Files touched:** `plan.md` (Sprint Closeout section — left uncommitted for the orchestrator), this work-log. **Blockers:** none.
