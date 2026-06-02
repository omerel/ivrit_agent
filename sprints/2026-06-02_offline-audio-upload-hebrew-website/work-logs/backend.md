# Work Log — @backend

## 2026-06-02T00:00:00Z — Task T2

**Task:** T2 — Wire FastAPI to serve the offline page and mount static assets (TDD).

**What was attempted:** Serve a single-file offline page from the existing
FastAPI app via `GET /` and mount `app/static/` at `/static`, without breaking
`GET /health` or `POST /transcribe` and without triggering a real model load.

**What was done (TDD):**
1. Wrote `tests/test_web.py` FIRST and confirmed it failed (RED): both tests
   returned 404 because `GET /` and `/static` did not exist yet. Tests use
   `TestClient(main.app)` directly (no context manager) mirroring
   `tests/test_main.py`, so the lifespan/model load never runs.
2. Created placeholder `app/static/index.html` containing
   `<html lang="he" dir="rtl">` and the literal `/transcribe` (so the mount
   directory exists at import time and the T2 assertions pass before T3's real UI).
3. Modified `app/main.py`: imported `FileResponse` (fastapi.responses) and
   `StaticFiles` (fastapi.staticfiles); defined
   `STATIC_DIR = Path(__file__).resolve().parent / "static"` (package-relative,
   CWD-independent); added `app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")`
   and `@app.get("/", include_in_schema=False)` returning
   `FileResponse(STATIC_DIR / "index.html", media_type="text/html")`. Changes are
   additive; `/health` and `/transcribe` untouched.

**Files touched:**
- `tests/test_web.py` (new)
- `app/static/index.html` (new, placeholder)
- `app/main.py` (modified — imports + STATIC_DIR + mount + GET /)

**Test result:** `pytest tests/test_web.py tests/test_main.py -v` → **9 passed, 2 warnings**.

```
tests/test_web.py::test_index_returns_html_with_rtl_and_transcribe PASSED [ 11%]
tests/test_web.py::test_static_index_html_served PASSED                  [ 22%]
tests/test_main.py::test_health PASSED                                   [ 33%]
tests/test_main.py::test_transcribe_success_returns_segments PASSED      [ 44%]
tests/test_main.py::test_transcribe_empty_upload_400 PASSED              [ 55%]
tests/test_main.py::test_transcribe_oversized_upload_rejected PASSED     [ 66%]
tests/test_main.py::test_transcribe_pipeline_error_returns_500 PASSED    [ 77%]
tests/test_main.py::test_transcribe_deletes_temp_file PASSED             [ 88%]
tests/test_main.py::test_import_does_not_load_models PASSED              [100%]
======================== 9 passed, 2 warnings in 4.09s =========================
```

**Commit:** `d9f094f` — `@backend: serve offline index page and mount /static (T2)`
(only `app/main.py`, `app/static/index.html`, `tests/test_web.py` staged).

**Blockers:** none.
