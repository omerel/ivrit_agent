# Work Log — @qa

## 2026-06-02T13:10:00Z — Task T5

**Task:** Add static-string guard tests for the four new features (theme/record/rename/MD-export) and re-confirm the full suite is green.

**What was done:**
- Read the final shipped `app/static/index.html` and verified the actual IDs/tokens before asserting (no guessing): record panel `#recordPanel`/`#recordBtn`/`#stopBtn`/`#recPreview`/`#recSave`/`#recUse`/`#recStatus`, plus `MediaRecorder` + `getUserMedia`; rename legend `#speakerLegend` + `speakerNames` state; MD export `#downloadMdBtn` + `text/markdown`; the literal `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"`.
- Added a new test file `tests/test_web_features.py` in the existing `test_web_offline.py` style: `TestClient(main.app)` built directly (NO lifespan context manager, so no model load), pure static-string assertions against `GET /` HTML. Six tests:
  - `test_index_still_offline_after_feature_work` — no `https?://`, `fonts.googleapis`, `fonts.gstatic`, `//cdn` against the new markup.
  - `test_index_still_has_contract_invariants` — `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"`.
  - `test_record_panel_controls_present` — the seven shipped record IDs.
  - `test_record_uses_browser_media_apis` — `getUserMedia` + `MediaRecorder`.
  - `test_speaker_rename_legend_present` — `#speakerLegend` + `speakerNames`.
  - `test_markdown_download_present` — `#downloadMdBtn` + `text/markdown`.
- Deliberately asserted only stable IDs / inlined-script tokens; no CSS/visual assertions (brittle), per T5 notes.
- Verified the assertions are non-vacuous: confirmed the asserted markers are really in the served HTML and a fake marker (`id="nonexistentBtn"`) is absent (would fail).

**Files touched:** `tests/test_web_features.py` (new).

**Verification (verification-before-completion):**
- New file alone: `.venv/bin/python -m pytest -q tests/test_web_features.py` → `6 passed, 2 warnings in 4.32s` (6 test functions in the new file).
- WHOLE suite: `.venv/bin/python -m pytest -q` → **65 passed, 2 warnings in 4.28s** (fully green; 59 prior + 6 new).

**Blockers:** none. T5 done.

**Commit:** `f0b37d6` on branch `sprint/ui-theme-record-rename-md-export` (only `tests/test_web_features.py` staged).
