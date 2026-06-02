# Work Log — @documenter

## 2026-06-02T10:02:06Z — Task T6

**Task:** Update the README "Web UI" section to document the four features shipped this sprint (professional theme, in-browser recording, speaker renaming, Markdown export).

**What was done:**
- Read the final `app/static/index.html` and the `@frontend` work log (T1–T4) to ensure the docs match what actually shipped; verified shipped IDs/labels (`recordBtn`/`stopBtn`/`recPreview`/`recUse`/`recSave`, `speakerLegend`, `downloadMdBtn`) and the offline-only mechanisms (`getUserMedia`/`MediaRecorder`, `Blob` + `text/markdown`, `recording.<ext>`/`transcript.md`).
- Extended the existing "Web UI" section bullet list (no duplication, kept existing tone). Added/updated bullets for:
  1. Brief mention of the refreshed professional theme (plain inline CSS, system fonts) inside the existing "Fully offline" bullet.
  2. Microphone recording as an alternative to file upload — start/stop, preview, save/keep locally, and "use for transcription" feeding the SAME `/transcribe` flow under the same 25 MiB limit; `getUserMedia`/`MediaRecorder` only, no libs/network; Hebrew handling for no-support/denied permission.
  3. Per-speaker editable legend renaming applied live, reset per run.
  4. Client-side Markdown `.md` download via `Blob`, reflecting renamed speakers.
- Reaffirmed single self-contained `app/static/index.html`, no remote references, fully offline, no libraries.
- Kept all existing details (start command, `GET /`, 25 MiB limit, RTL Hebrew, speaker labels, `mm:ss` timestamps).
- Docs only — no code/HTML behavior changes.

**Files touched:** `README.md`.

**Blockers:** none. T6 done.

**Commit:** `f9dfa61` on branch `sprint/ui-theme-record-rename-md-export` (only `README.md` staged).
