# Work Log — @planner

## 2026-06-02T00:00 — Planning (sprint: audio-playback-edit-speaker-label)

**Task:** Decompose the sprint goal (two client-side UI enhancements) into an executable `plan.md`.

**Context read:**
- `CLAUDE.md` (workflow rules, §5 plan structure), `.claude/team.md` (validated all assignee nicknames exist: @architect, @frontend, @qa, @documenter).
- `app/static/index.html` IN FULL (1619 lines). Grounded the plan in the actual code: `setFile`/`clearFile` (~978/1003) currently create NO playback for the uploaded file — only the recorder has `#recPreview` (set in `onRecStop`, ~1154, with `revokeRecUrl`/`createObjectURL`/`beforeunload` discipline). Render path: `renderResults` (~1318) → `groupSegments` (~1207) groups consecutive segments by `speakerKey`; per-turn DOM builds avatar/`.who`/`.time`/`.line`; `registerNameNode`/`refreshSpeakerName` support live legend renames; `displayName` reads `speakerNames[key]`; `lastResult.turns` feeds `buildMarkdown` (~1434).
- `app/main.py` (POST /transcribe multipart `file`, MAX_UPLOAD_BYTES 26214400, no change needed), `app/schemas.py` (contract unchanged).
- `tests/test_web_features.py` (static-string guard style I told @qa to extend) and the prior sprint plan `2026-06-02_ui-theme-record-rename-md-export/plan.md` (mirrored its conventions, hard-constraints block, and serial-@frontend sequencing).
- README "Web UI" section (~line 96).

**How I decomposed the goal:**
- Confirmed the key subtlety: feature 2 is PER-TURN REASSIGNMENT (fixing diarization mistakes), NOT the GLOBAL per-speaker rename already shipped last sprint. Made the distinction explicit in the plan and flagged it as an open question for the approval gate.
- 5 tasks, all touching the single `index.html` (except tests/docs): T0 @architect alignment (IDs + state model) FIRST; T1 @frontend upload `<audio>` player (feature 1); T2 @frontend per-turn reassignment (feature 2); T3 @qa static guards; T4 @documenter README. Sequenced serially because both features edit the same file.
- Baked in all hard constraints: offline grep, `<audio>`+`createObjectURL` only (no libs/no server), pure client-side reassignment via a working copy of segments + re-run `groupSegments` + rebuild `lastResult.turns`, preserve `<html lang="he" dir="rtl">`/`/transcribe`/`type="file"`, Hebrew RTL, `frontend-design` skill for new controls, additive + green.
- No @backend task (default: none); documented the blocker condition if a server change turns out genuinely needed.

**Files touched:** `sprints/2026-06-02_audio-playback-edit-speaker-label/plan.md` (created), this work log.

**Open questions for the guide:**
1. Confirm feature 2 = per-turn speaker REASSIGNMENT (fix wrong attribution), since the global per-speaker RENAME already shipped. If the guide meant the rename, feature 2 would be redundant.

**Blockers:** none.
