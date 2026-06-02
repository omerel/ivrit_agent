# Sprint: Offline audio-upload Hebrew transcript website

**Started:** 2026-06-02
**Goal:** Serve a static, offline, beautiful web page from the existing FastAPI app that uploads an audio file and renders the returned transcript in RTL Hebrew.

## Context & Design Decisions

Read these before starting any task:
- `app/main.py` — already exposes `POST /transcribe` (multipart field name `file`) returning
  `{segments:[{speaker,text,start,end}], language, num_speakers}` and `GET /health`.
- `app/schemas.py` — `Segment{speaker,text,start,end}`, `TranscriptionResponse{segments,language,num_speakers}`.
- `app/config.py` — `settings.MAX_UPLOAD_BYTES` (25 MiB) is the upload size cap the UI must respect/communicate.
- `tests/test_main.py` — established test style: `TestClient(main.app)`, fake pipeline on `app.state.pipeline`.

**Offline / static strategy (mandatory):**
- All UI assets live under `app/static/` and are served locally — **no external CDNs, no Google Fonts, no remote JS/CSS**.
- The page is a **single self-contained `app/static/index.html`** with CSS and JS inlined into it (no `<link href>`/`<script src>` to any remote host, and no local font files needed — use a system-font stack). This is the strongest offline guarantee and keeps the asset surface minimal.
- FastAPI serves it two ways: (a) `GET /` returns the HTML, and (b) `app/static/` is mounted via `StaticFiles` at `/static` so the page (and any future asset) is reachable as a real static mount.
- The page's JS calls the **same-origin** `POST /transcribe` (relative URL `/transcribe`, no hardcoded host) so it works behind any host/port and offline.

**Beauty / a11y requirements:**
- `@frontend` MUST use the `frontend-design` skill. Distinctive, production-grade, not generic-AI-looking.
- `<html lang="he" dir="rtl">`; transcript text rendered RTL.
- Show: drag-and-drop + file-picker upload, selected filename, an in-progress/loading state (transcription is slow), error states (empty file, too-large file, server 4xx/5xx), and a results view that lists segments grouped/labelled by speaker with `num_speakers` and `language` shown as a header summary. Timestamps (start/end) shown per segment in a readable mm:ss form.

## Tasks

- [x] **T1** [done] @architect — Confirm and document the serving approach so T2/T3 don't conflict.
  - Acceptance: A short decision note appended to `sprints/2026-06-02_offline-audio-upload-hebrew-website/work-logs/architect.md` that states: (1) single self-contained `app/static/index.html` with inlined CSS/JS, system-font stack (no font files); (2) `GET /` returns that file via `FileResponse`; (3) `StaticFiles` mounted at `/static`; (4) UI uses relative `/transcribe`; (5) the JSON contract the JS will consume (`segments[].{speaker,text,start,end}`, `language`, `num_speakers`) and the `MAX_UPLOAD_BYTES` cap the UI must surface. No code is written in this task.
  - Notes: This is a thin alignment step. If you disagree with single-file inlining, raise it here before any code is written, otherwise affirm it. Keep it to one screen of text.

- [x] **T2** [done] @backend — Wire FastAPI to serve the page and mount static assets (TDD).
  - Acceptance:
    - New `tests/test_web.py` written first and failing, then passing, covering: `GET /` returns `200`, `content-type` starts with `text/html`, and the body contains `dir="rtl"` and the string `/transcribe`; and `GET /static/index.html` returns `200` with `text/html`. Existing `GET /health` and `POST /transcribe` tests still pass.
    - `app/main.py` modified to: import `FileResponse` (from `fastapi.responses`) and `StaticFiles` (from `fastapi.staticfiles`); mount `app.mount("/static", StaticFiles(directory=<app>/static), name="static")`; add `@app.get("/", include_in_schema=False)` returning `FileResponse(<app>/static/index.html, media_type="text/html")`. The static directory path must be resolved relative to the package (like the existing `REPO_ROOT`/`Path(__file__)` pattern) so it works regardless of CWD.
    - A placeholder `app/static/index.html` exists (containing at minimum `<html lang="he" dir="rtl">` and the literal `/transcribe`) so tests pass before T3 replaces it with the real UI.
  - Notes: Follow `test-driven-development` and `verification-before-completion`. Run `pytest tests/test_web.py tests/test_main.py -v` and paste the passing output into your work log. Do NOT trigger a real model load — the static/`GET /` routes don't need the pipeline. Mounting `StaticFiles(directory=...)` requires the dir to exist at import time, so create `app/static/index.html` (placeholder) in this task. Prefix commit `@backend:`.

- [x] **T3** [done] @frontend — Build the beautiful offline RTL Hebrew upload + transcript UI in `app/static/index.html`.
  - Acceptance:
    - `app/static/index.html` is a single self-contained file: all CSS in a `<style>` block, all JS in a `<script>` block, **zero** external/remote references (no `http(s)://`, no `//cdn`, no Google Fonts `<link>`); fonts via a system-font stack only.
    - `<html lang="he" dir="rtl">`. Hebrew UI copy. Transcript renders RTL.
    - Upload: file picker + drag-and-drop, shows chosen filename, and blocks files over 25 MiB client-side with a Hebrew error before sending.
    - Submit posts the file as `multipart/form-data` field name `file` to the **relative** URL `/transcribe` via `fetch`; shows a loading state while awaiting; on success renders a header summary (`language`, `num_speakers`) and the segments grouped/labelled by `speaker` with `start`–`end` shown as `mm:ss`; on HTTP error shows the server `detail` (or a generic Hebrew message) without leaking stack traces.
    - Distinctive, polished visual design (not generic). Works with no internet connection.
  - Notes: MUST invoke the `frontend-design` skill before writing markup. The segment objects are `{speaker, text, start, end}` (start/end in seconds, floats). `num_speakers`/`language` may be `null` — handle gracefully. Verify offline behavior by loading the page with no network (e.g. note in the work log that the file contains no remote URLs — `grep -nE "https?:|//cdn|fonts.googleapis|fonts.gstatic" app/static/index.html` returns nothing). Keep the file replacing the T2 placeholder; it must still contain `<html lang="he" dir="rtl">` and the literal `/transcribe` so T2's tests keep passing. Prefix commit `@frontend:`.

- [x] **T4** [done] @qa — Add focused offline/contract tests guarding the static-no-CDN guarantee and the upload contract surface.
  - Acceptance:
    - Add tests (extend `tests/test_web.py` or new `tests/test_web_offline.py`) that: (1) assert the served `index.html` body contains **no** remote references — regex `https?://`, `fonts.googleapis`, `fonts.gstatic`, `//cdn` all find nothing; (2) assert it contains `multipart`/form upload to `/transcribe` is wired (body contains the literal `/transcribe` and `type="file"`); (3) assert `<html` line has both `lang="he"` and `dir="rtl"`.
    - All tests pass: `pytest -v` green for the whole suite (run it and paste the summary line into the work log).
  - Notes: Pure static-string assertions against the HTML served by `TestClient` — no browser, no model load needed. Follow `verification-before-completion`: only claim pass after you've seen green output. Prefix commit `@qa:`.

- [x] **T5** [done] @documenter — Document how to run and use the web UI.
  - Acceptance: `README.md` gains a short "Web UI" section: how to start the server (existing uvicorn command), that the page is at `GET /` (`http://localhost:8000/`), that it works fully offline, the 25 MiB upload limit, and that the transcript renders in RTL Hebrew with speaker labels. No source behavior changes.
  - Notes: Keep it additive — append a section, don't rewrite existing docs. Prefix commit `@documenter:`.

## Routing Overrides

(Empty until the Orchestrator overrides a Planner assignment.)

## Sprint Closeout

STATUS: PASS

Reviewed by @reviewer on 2026-06-02. All five `done` tasks independently verified against their acceptance criteria by inspecting the actual files and running the project venv test suite.

- **T1 PASS** — `work-logs/architect.md` contains a decision note that explicitly affirms all 5 points: (1) single self-contained `app/static/index.html` with inlined CSS/JS + system-font stack (no font files); (2) `GET /` via `FileResponse`; (3) `StaticFiles` mounted at `/static` with package-relative `Path(__file__)`; (4) UI uses relative `/transcribe`; (5) the JSON contract (`segments[].{speaker,text,start,end}`, `language`, `num_speakers`) and the `MAX_UPLOAD_BYTES` = 26214400 cap to surface. No code written in T1 (confirmed: only the work-log was touched).
- **T2 PASS** — `app/main.py` imports `FileResponse`/`StaticFiles`, resolves `STATIC_DIR = Path(__file__).resolve().parent / "static"` (CWD-independent), mounts `app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")`, and serves `GET /` via `FileResponse(STATIC_DIR / "index.html", media_type="text/html")`. `tests/test_web.py` exists and passes (`GET /` 200 + text/html + `dir="rtl"` + `/transcribe`; `GET /static/index.html` 200 text/html). `/health` and `/transcribe` untouched.
- **T3 PASS** — `app/static/index.html` is a single self-contained file. `grep -nE "https?:|//cdn|fonts.googleapis|fonts.gstatic|<script src|<link " app/static/index.html` returned nothing (exit 1) — zero remote references. Verified present: `<html lang="he" dir="rtl">`, literal `/transcribe` (x2), `type="file"`, drag-and-drop (dragenter/dragover/dragleave/drop handlers), client-side 25 MiB guard (`26214400`), zero-padded mm:ss rendering (`fmtTime` using `Math.floor(total/60)` + pad), FormData POST to relative `/transcribe` via `fetch`, and null-safe handling of `language`/`num_speakers` (rendered as "—" when null).
- **T4 PASS** — `tests/test_web_offline.py` contains the three required assertions: (1) `test_index_has_no_remote_references` (regex `https?://`, `fonts.googleapis`, `fonts.gstatic`, `//cdn` all find nothing); (2) `test_index_wires_file_upload_to_transcribe` (body contains `/transcribe` and `type="file"`); (3) `test_index_root_html_tag_is_rtl_hebrew` (`<html>` tag has both `lang="he"` and `dir="rtl"`). All three pass.
- **T5 PASS** — `README.md` has an additive "Web UI" section covering the uvicorn start command, the page at `GET /` (http://localhost:8000/), fully-offline single self-contained `app/static/index.html`, the 25 MiB `MAX_UPLOAD_BYTES` client-side limit, and RTL Hebrew results with speaker labels + a language/num_speakers summary. An Endpoints-table row for `GET /` was also added. No source behavior changes.

**Whole-suite pytest (project venv):** `.venv/bin/python -m pytest -v` → `======================== 59 passed, 2 warnings in 4.93s ========================` (fully green).

**Note:** The pre-existing `.env`/`tests/test_config.py::test_defaults_match_main_py` conflict (a stale `WHISPER_MODEL` default assertion shadowed by the repo `.env` after commit `6c6bdaa`) was flagged in `work-logs/qa.md` and resolved out-of-band via quick-fix `fixes/2026-06-02_config-test-env-isolation.md` (constructs the test `Settings` with `_env_file=None`; no change to `app/config.py` or `.env`). With that fix in place the whole suite is green.

