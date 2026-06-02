# Work Log — @documenter

## 2026-06-02T15:10:00+0300 — Task T4

**What:** Updated the README "Web UI" section to document this sprint's two new
client-side features, matching what actually shipped in `app/static/index.html`
(verified against the T1/T2 frontend work logs and the plan).

**Changes (docs only, `README.md`):**
- Added a **"Listen to the uploaded file in the page"** bullet (feature 1):
  inline audio player on file select / drag / used recording, fed by a local
  `URL.createObjectURL` object URL, no upload-to-listen, fully offline, URL
  released on new file / clear / page leave, and noted it's a distinct player
  from the recorder preview (so uploaded + recorded clips don't clobber).
- Reworded the existing **"Rename speakers"** bullet to **"Rename a speaker
  (change a display name)"** and explicitly clarified it only relabels — it does
  NOT move turns between speakers — to keep it crisp against feature 2.
- Added a **"Reassign a turn (fix a wrong attribution)"** bullet (feature 2):
  per-turn control to move a turn to a different/new speaker, live re-render,
  adjacent same-speaker turns merge, custom names survive reassignment, fully
  client-side (working copy of segments), resets on new transcription.
- Updated the **"Download as Markdown"** bullet to note the export reflects both
  renamed speaker names AND turn reassignments at click time.
- Reaffirmed (existing top bullet kept intact) that the page is still a single
  self-contained `app/static/index.html` with no remote references / fully offline.

**Files touched:** `README.md` (only).

**Blockers:** none.

**Commit:** see summary (subject prefixed `@documenter:`).
