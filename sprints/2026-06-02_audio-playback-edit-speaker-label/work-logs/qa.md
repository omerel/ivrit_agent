# Work Log — @qa

## 2026-06-02T10:33:25Z — Task T3

**What:** Added static-string guard tests for the two new client-side features (upload audio playback + per-turn speaker reassignment) to `tests/test_web_features.py`, matching the existing style (`TestClient(main.app)` without the lifespan context manager; pure static-string/regex assertions against `GET /` HTML, no model load).

**Verification of markers before asserting:** grepped the FINAL `app/static/index.html` and confirmed every asserted token actually shipped:
- Feature 1: `id="uploadPreview"` (line 835), `id="uploadPreviewAudio"` (837), `URL.createObjectURL` (1081).
- Feature 2: `workingSegments` (multiple), `data-turn-idx` (1594/1613), Hebrew option `דובר/ת חדש/ה` (1609).
- Offline grep `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link '` returned nothing (exit 1).
- Exactly one `fetch("/transcribe"` reference (line 1705).

**Tests added (7):**
- `test_index_still_offline_after_playback_and_reassignment` — offline invariant vs new markup.
- `test_index_contract_invariants_after_playback_and_reassignment` — `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"`.
- `test_upload_audio_player_present` — `id="uploadPreview"` + `id="uploadPreviewAudio"`.
- `test_upload_player_uses_object_url` — `createObjectURL`.
- `test_reassignment_per_turn_token_present` — `data-turn-idx` + `workingSegments`.
- `test_reassignment_add_new_speaker_option_present` — `דובר/ת חדש/ה`.
- `test_single_transcribe_fetch_call` — exactly one `fetch("/transcribe"` (contract not duplicated).

**Files touched:** `tests/test_web_features.py` (added 75 lines; this work log created).

**pytest summary (full suite, `.venv/bin/python -m pytest -q`):** `72 passed, 2 warnings in 4.90s` — fully green (pre-existing StarletteDeprecationWarning + opentelemetry DeprecationWarning, unrelated to this change).

**Commit:** `3394e89` on branch `sprint/audio-playback-edit-speaker-label` (test file only staged).

**Blockers:** none.
