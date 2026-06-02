# Work Log — @planner

## 2026-06-02T07:08:41Z — Task PLAN

- **Attempted:** Decompose the sprint goal "static, offline, beautiful FastAPI-served website for audio upload -> RTL Hebrew transcript" into an executable plan.
- **Context read:** `CLAUDE.md`, `.claude/team.md`, `resource/README.md`, and the existing app (`app/main.py`, `app/schemas.py`, `app/config.py`, `app/transcription.py`) plus the test conventions in `tests/test_main.py`.
- **Decomposition rationale:**
  - The existing `POST /transcribe` (multipart `file` -> `{segments[{speaker,text,start,end}],language,num_speakers}`) and `GET /health` are reused unchanged; the sprint is purely additive (serve a page + a UI that calls the existing endpoint).
  - Chose a **single self-contained `app/static/index.html`** (inlined CSS/JS, system-font stack, no font files) as the strongest offline guarantee — eliminates any chance of a stray CDN/Google-Fonts reference. Still mount `StaticFiles` at `/static` per the goal's "served locally by FastAPI" requirement, and serve `GET /` via `FileResponse`.
  - T1 (@architect) is a thin alignment note so the backend wiring and frontend build don't conflict on the serving contract; no code.
  - T2 (@backend) wires `GET /` + `StaticFiles` mount with TDD (`tests/test_web.py`), creating a placeholder HTML so the mount/tests work before the real UI lands.
  - T3 (@frontend) builds the real UI with the `frontend-design` skill; RTL Hebrew, drag-and-drop, loading/error states, segment rendering grouped by speaker with mm:ss timestamps. Constrained to keep the markers (`dir="rtl"`, `/transcribe`) T2 asserts on.
  - T4 (@qa) locks the offline guarantee with static-string tests (no remote URLs, file upload wired, RTL/lang attrs) over the full suite.
  - T5 (@documenter) adds a README "Web UI" section.
- **Files touched:** wrote `plan.md`; created this work log.
- **Assignments use only roster nicknames:** @architect, @backend, @frontend, @qa, @documenter (all present in `.claude/team.md`).
- **Open questions for the guide:**
  1. Single-file inlined `index.html` vs. separate `style.css`/`app.js` under `/static` — I picked single-file for offline safety; flag if you prefer split files.
  2. Should the UI expose a control for `min_speakers` (the pipeline accepts it but `/transcribe` does not currently pass it through)? Left out of scope to keep changes additive; say so if you want it wired.
- **Blockers:** none.
