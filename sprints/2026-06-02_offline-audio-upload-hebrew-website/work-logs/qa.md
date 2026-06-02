# Work Log — @qa

## 2026-06-02T00:00:00 — Task T4

**Attempted:** Add focused offline/contract tests guarding the static-no-CDN
guarantee and the upload contract surface for the served `index.html`.

**Done:**
- Wrote new `tests/test_web_offline.py` with 3 tests (matching existing
  `TestClient(main.app)` style, no model load), asserting against the HTML
  served by `GET /`:
  1. `test_index_has_no_remote_references` — regex search for `https?://`,
     `fonts.googleapis`, `fonts.gstatic`, `//cdn` all find nothing.
  2. `test_index_wires_file_upload_to_transcribe` — body contains literal
     `/transcribe` AND `type="file"`.
  3. `test_index_root_html_tag_is_rtl_hebrew` — the `<html ...>` tag contains
     both `lang="he"` and `dir="rtl"`.
- Ran the WHOLE suite with `pytest -v`.

**Files touched:**
- `tests/test_web_offline.py` (added)

**Pytest summary:** `1 failed, 58 passed, 2 warnings in 4.84s`
- All 3 new T4 tests PASSED; existing `tests/test_web.py` tests still PASS.
- The single failure is `tests/test_config.py::test_defaults_match_main_py`,
  which is PRE-EXISTING and unrelated to T4. Verified via `git stash -u` that
  it fails on the tree without my changes. Root cause: commit `6c6bdaa`
  ("change app to use local models") changed the `WHISPER_MODEL` default in
  `app/config.py` to a local snapshot path but did not update
  `tests/test_config.py:23`, which still asserts
  `"ivrit-ai/whisper-large-v3-turbo-ct2"`.

**Commit:** `0a218365a2311587ad7a7a0d9237c7cbb0fdff9a` (staged only
`tests/test_web_offline.py`).

**Blockers:** The whole suite is NOT green because of the pre-existing
`test_config.py` failure. It is outside T4's scope (T4's own acceptance —
the offline/contract tests — is fully green). Recommend dispatching a Builder
(@backend) to reconcile `tests/test_config.py` with the new local-model
default in `app/config.py`. T4 deliverable itself is complete.
