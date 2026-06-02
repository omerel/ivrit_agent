# Work Log — @documenter

## 2026-06-02T00:00:00Z — Task T5

**Attempted:** Document how to run and use the offline Web UI in `README.md`.

**Done:**
- Read CLAUDE.md, .claude/team.md, the active plan, README.md, and app/main.py
  to confirm the run command (`uv run uvicorn app.main:app`) and routes
  (`GET /` serves the page, `GET /health`, `POST /transcribe`).
- Appended an additive "Web UI" section to README.md (placed before "How to
  send audio"): start command, the `GET /` page at http://localhost:8000/,
  the fully-offline single self-contained `app/static/index.html` (no CDNs/
  remote assets), the 25 MiB `MAX_UPLOAD_BYTES` limit, and RTL Hebrew
  transcript rendering with speaker labels + a language/num_speakers summary.
- Added a `GET /` row to the Endpoints table linking to the new section.
- No source behavior changed (docs only). Existing docs left intact.

**Files touched:**
- `README.md` (additive Web UI section + Endpoints table row)
- `sprints/2026-06-02_offline-audio-upload-hebrew-website/plan.md` (T5 -> done)

**Commit:** cca46f4b5085c1571388dc8a4e845e2263c7e4df (branch
`sprint/offline-audio-upload-hebrew-website`)

**Blockers:** None.
