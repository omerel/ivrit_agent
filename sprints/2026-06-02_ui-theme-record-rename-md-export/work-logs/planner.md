# Work Log — @planner

## 2026-06-02T12:40:00 — Task PLAN

**Attempted:** Decompose the sprint goal (4 UI features on the existing offline Hebrew transcription page) into an executable `plan.md`.

**Context read:** `CLAUDE.md`, `.claude/team.md`, `sprints/.active` (active = `2026-06-02_ui-theme-record-rename-md-export`), the full `app/static/index.html`, `app/main.py`, `app/config.py`, `app/schemas.py`, `tests/test_web.py`, `tests/test_web_offline.py`, the previous sprint's `plan.md`, and the README "Web UI" section. Listed `resource/` (README.md, main.py, "audio smaples" dir) — none directly relevant to this frontend-only sprint, so not read in depth.

**How I decomposed the goal:**
- Confirmed from `app/main.py` that `POST /transcribe` writes the upload to a temp file (suffix from filename) and lets ffmpeg sniff the format, so a recorded `audio/webm` blob sent as the multipart `file` field needs NO backend change. `@backend` is therefore intentionally not assigned; the one fallback-blocker condition is documented in T0/T2.
- All four features edit the SAME single-file `index.html`, so I sequenced them serially under `@frontend` to avoid conflicting concurrent edits, in dependency order: T1 theme (reshapes CSS) → T2 record (new input source, reuses `setFile`/`submit`) → T3 rename (mutates rendered results, shared `speakerNames` state) → T4 MD export (consumes possibly-renamed results).
- Added T0 (@architect) as a thin no-code alignment doc to pin shared DOM IDs and the `speakerNames[key]` state shape so the serial frontend tasks stay consistent.
- T5 (@qa) adds static-string guard tests in the `test_web_offline.py` style (offline grep, RTL/`/transcribe`/`type="file"` invariants, plus markers for each new feature). T6 (@documenter) updates the README "Web UI" section.
- Baked the hard constraints into every code task's acceptance: offline single-file (with the exact grep), preserved test invariants, Hebrew RTL copy, `frontend-design` skill required, additive + `pytest -q` green.

**Files touched:** `sprints/2026-06-02_ui-theme-record-rename-md-export/plan.md` (created), this work log.

**Self-review:** Spec coverage — all 4 features map to T1–T4; offline/invariant/test/docs requirements covered by per-task acceptance + T5/T6. Placeholder scan — every task has concrete acceptance criteria, exact IDs, exact grep command. Nickname validation — @architect, @frontend, @qa, @documenter all exist in `.claude/team.md`. Type/ID consistency — `speakerNames[key]` (keyed by existing `speakerKey`), `#downloadMdBtn`, and record-panel IDs referenced consistently across T0→T4.

**Blockers:** None.

**Open questions for the guide:** (1) The current theme is the warm-amber "archive" look; "more professional" is interpreted as a cleaner/more restrained palette+typography while staying distinctive — guide may want to specify a direction (e.g. corporate blue/neutral) at the plan-approval gate. (2) For speaker renaming UI, the plan leaves the exact control form (inline-edit per turn vs. editable legend) to `@frontend`'s `frontend-design` judgment; flag if a specific pattern is preferred.
