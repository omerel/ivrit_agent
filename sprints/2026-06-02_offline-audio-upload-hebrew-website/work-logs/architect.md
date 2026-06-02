# Work Log — @architect

## 2026-06-02T00:00:00Z — Task T1

**Task:** T1 — Confirm and document the serving approach so T2/T3 don't conflict.

**What was done:** Reviewed `app/main.py`, `app/schemas.py`, `app/config.py` and the
sprint's "Context & Design Decisions". I **affirm** the planned serving approach; no
disagreement. Decision note below. No code written.

### Decision Note — Static offline serving approach

1. **Single self-contained file.** `app/static/index.html` holds all CSS in one
   `<style>` block and all JS in one `<script>` block. No `<link href>`/`<script src>`
   to any host, no font files — use a system-font stack
   (`-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans Hebrew", sans-serif`).
   This is the strongest offline guarantee and the minimal asset surface. **Affirmed.**

2. **`GET /` returns the file via `FileResponse`.** Add
   `@app.get("/", include_in_schema=False)` returning
   `FileResponse(<static>/index.html, media_type="text/html")`. Setting `media_type`
   explicitly guarantees the `Content-Type: text/html` the T2/T4 tests assert.
   **Affirmed.**

3. **`StaticFiles` mounted at `/static`, package-relative path.** The static dir is
   part of the `app/` package, so resolve it as `Path(__file__).resolve().parent / "static"`
   inside `app/main.py` (the same `Path(__file__)` discipline `app/config.py` uses for
   `REPO_ROOT` and `_resolve_local_model`). Do **not** use CWD-relative paths. Mount via
   `app.mount("/static", StaticFiles(directory=<that path>), name="static")`. Note for T2:
   `StaticFiles(directory=...)` validates the directory at **import time**, so a
   placeholder `app/static/index.html` must exist before the mount line runs — create it
   in T2 before T3 replaces it.

4. **UI calls same-origin relative `/transcribe`.** JS posts `multipart/form-data` with
   field name **`file`** (matches `transcribe(... file: UploadFile)` in `app/main.py`) to
   the relative URL `/transcribe` via `fetch` — no hardcoded host/scheme, so it works
   behind any host/port and fully offline. **Affirmed.**

5. **JSON contract the JS consumes** (verified against `app/schemas.py`):
   - `segments`: array of `{ speaker: string, text: string, start: float, end: float }`.
     `start`/`end` are **seconds** (floats) → render as `mm:ss`. `speaker` is a label
     string (e.g. `"SPEAKER_00"`, or `"UNKNOWN"` when no diarization segment overlapped).
   - `language`: `string | null` — handle `null` gracefully in the header summary.
   - `num_speakers`: `int | null` (distinct labels excluding `"UNKNOWN"`) — handle `null`.
   - **Error shape:** non-2xx responses are FastAPI/`HTTPException` `{ "detail": "..." }`.
     UI shows `detail` (or a generic Hebrew message) without leaking stack traces.
   - **Upload cap to surface:** `settings.MAX_UPLOAD_BYTES = 26_214_400` (= 25 MiB, exactly
     `25 * 1024 * 1024`) per `app/config.py`. The UI must block oversize files
     **client-side** with a Hebrew error before sending; the server independently returns
     **413** for oversize and **400** for an empty upload, which the UI should also handle.

**Contract guardrails for T2/T3 (so they don't conflict):** the served body must contain
the literal `<html lang="he" dir="rtl">` and the literal string `/transcribe` (asserted by
T2/T4), and must contain **no** remote references (`https?://`, `fonts.googleapis`,
`fonts.gstatic`, `//cdn`). T3's real UI replaces T2's placeholder but must preserve both
literals.

**Files touched:** this work-log only (no source files).

**Blockers:** none.
