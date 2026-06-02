# Sprint: Enhance offline Hebrew transcription UI (theme, record, rename, MD export)

**Started:** 2026-06-02
**Goal:** Add four features to the existing offline self-contained `app/static/index.html` — a more professional theme, in-browser audio recording fed into the same `/transcribe` flow, post-transcription speaker renaming, and client-side Markdown download — without breaking the offline/RTL/contract invariants.

## Context & Design Decisions

Read these before starting any task:
- `app/static/index.html` — the SINGLE self-contained offline page. ALL CSS lives in one `<style>` and ALL JS in one IIFE `<script>`. This is the file features 1–4 modify. Key existing pieces the new work plugs into:
  - The upload flow: `setFile(file)` / `clearFile()` validate against `MAX_UPLOAD_BYTES` (26214400) and toggle `#submitBtn`; `submit()` builds `FormData`, appends field `"file"`, and POSTs to relative `/transcribe`.
  - The render flow: `renderResults(data)` reads `data.segments[].{speaker,text,start,end}`, `data.language`, `data.num_speakers`; `groupSegments()` groups consecutive segments into turns; `speakerName(label)` maps `SPEAKER_00`→"דובר/ת 1", `UNKNOWN`→"דובר/ת לא מזוהה"; `fmtTime(sec)` → mm:ss (or h:mm:ss). `colorForKey` assigns per-speaker colors.
  - State machine: `clearStates()` / `show(node,on)` toggle `.show` on `#alert`, `#loading`, `#results`.
- `app/main.py` — `GET /` serves the file via `FileResponse`; `/static` is a `StaticFiles` mount; `POST /transcribe` accepts multipart field `file`, returns `{segments,language,num_speakers}`; `GET /health`. `MAX_UPLOAD_BYTES = 26214400`. The endpoint writes bytes to a temp file with the uploaded filename's suffix and lets ffmpeg sniff the format, so an `audio/webm` recording sent as a `File` works with NO backend change.
- `app/schemas.py` — `Segment{speaker,text,start,end}`, `TranscriptionResponse{segments,language,num_speakers}`. The response contract is unchanged this sprint.
- `tests/test_web.py` and `tests/test_web_offline.py` — the offline/contract guard tests that MUST keep passing.
- `README.md` — has a "Web UI" section (around line 96) describing the offline page; it gets updated in the docs task.

**HARD CONSTRAINTS (every code task must honor all of these):**
1. **Offline / single-file is non-negotiable.** The page stays one self-contained `app/static/index.html` with NO external/remote references: no CDNs, no Google Fonts, no remote `<script src>` / `<link href>`. Audio recording uses ONLY the built-in `getUserMedia` + `MediaRecorder` Web APIs (no libraries). MD download is generated client-side via `Blob` + `URL.createObjectURL` (no server round-trip, no libs). The recorded-audio "save" is also a client-side Blob download. After every code task this grep MUST return nothing:
   `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html`
2. **Preserve test invariants:** `<html lang="he" dir="rtl">`, the literal string `/transcribe`, and `type="file"` must remain present so `tests/test_web.py` + `tests/test_web_offline.py` keep passing.
3. **Hebrew RTL UI throughout.** Every new control, label, button, and error message is in Hebrew.
4. **`@frontend` MUST use the `frontend-design` skill** for the theme rework (feature 1) and all new UI controls.
5. **Additive + green.** The full suite (`pytest -q`) must stay green. New tests are static-string assertions in the style of `test_web_offline.py`.

**Backend impact:** NO backend change required. `POST /transcribe` already accepts any audio blob (incl. `audio/webm`) as the multipart `file` field and lets ffmpeg decode it. `@backend` is intentionally not assigned. If — and only if — `@frontend` discovers during T2 that a recorded blob cannot be transcribed by the existing endpoint, that is a blocker to surface to the guide (not a silent backend edit).

**Sequencing rationale:** All four features edit the same `index.html`, so they are done SERIALLY by `@frontend` to avoid conflicting concurrent edits, in dependency order: theme (T1) reshapes CSS/layout first → record (T2) adds a new input source → rename (T3) mutates rendered results → MD export (T4) consumes the (possibly renamed) results. Tests (T5) and docs (T6) come after the UI is final.

## Tasks

- [x] **T0** [done] @architect — Lock the integration plan for the four features inside the single-file page.
  - Acceptance: A short decision note (max one screen) appended to `sprints/2026-06-02_ui-theme-record-rename-md-export/work-logs/architect.md` that pins down, so T1–T4 don't collide:
    1. Confirms NO backend change is needed (recorded `audio/webm` blob → multipart `file` → existing `/transcribe`), and states the one fallback condition that would make it a blocker.
    2. Names the new DOM regions/IDs to be added (e.g. a record panel with `#recordBtn`/`#stopBtn`/`#recPreview`/`#recSave`, per-turn editable speaker name controls, a `#downloadMdBtn` in the results header) so feature tasks use consistent IDs.
    3. Defines a single client-side state object for renamed speakers (e.g. `speakerNames[key] = customName`) that both the live re-render (T3) and the MD export (T4) read, keyed by the same `speakerKey(label)` the existing code uses.
    4. Confirms the recorded blob is sent through the SAME `submit()` path (set it as `selectedFile` via the existing `setFile`, respecting the 25 MiB guard) rather than a parallel upload path.
  - Notes: No code in this task. This is a thin alignment doc so the serial frontend tasks share IDs and the speaker-name state shape. Keep it tight. Prefix any commit `@architect:`.

- [x] **T1** [done] @frontend — Rework the theme to a more professional look (feature 1).
  - Acceptance:
    - `app/static/index.html` CSS reworked to a more professional, restrained aesthetic (the current look is a warm-amber "archive" theme; move toward a cleaner, more professional palette/typography while keeping it distinctive — `@frontend` uses the `frontend-design` skill to drive this, not a generic template).
    - Layout/structure and all existing element IDs and JS behavior remain intact (do NOT rename `#dropzone`, `#fileInput`, `#submitBtn`, `#results`, `#transcript`, etc. — only restyle). All copy stays Hebrew RTL.
    - `<html lang="he" dir="rtl">`, the literal `/transcribe`, and `type="file"` are all still present.
    - Offline grep returns nothing: `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html`.
    - `pytest -q` is green after this task.
  - Notes: Invoke the `frontend-design` skill before writing CSS. Keep the system-font stack (no font files, no remote fonts). Respect `prefers-reduced-motion`. This task is purely visual; behavior changes belong to T2–T4. Paste the offline-grep result and `pytest -q` output into your work log. Prefix commit `@frontend:`.

- [x] **T2** [done] @frontend — Add in-browser audio recording that feeds the existing /transcribe flow (feature 2).
  - Acceptance:
    - A new recording panel is added to `app/static/index.html` with Hebrew controls: start recording, stop, preview playback of the captured clip, "save/keep recording" (download the recorded blob locally), and "use this recording for transcription".
    - Uses ONLY `navigator.mediaDevices.getUserMedia({audio:true})` + `MediaRecorder` (e.g. `audio/webm`) — NO libraries. Records to a `Blob`, builds a `File` from it (e.g. `new File([blob], "recording.webm", {type:blob.type})`), and routes it through the EXISTING upload path by calling the existing `setFile(file)` so the 25 MiB `MAX_UPLOAD_BYTES` guard and the existing `submit()` (POST multipart field `file` to `/transcribe`) handle it unchanged. No parallel upload code path.
    - The "save/keep" action downloads the recorded blob via a `Blob` + `URL.createObjectURL` + a temporary `<a download>` (client-side only, no server).
    - Graceful Hebrew handling of: permission denied (`getUserMedia` rejects), and unsupported browser (`navigator.mediaDevices`/`window.MediaRecorder` missing) — show a Hebrew message via the existing alert/error pattern rather than throwing; the rest of the page (file upload) still works.
    - A recorded clip that exceeds 25 MiB is rejected with the same Hebrew "too large" messaging the file path uses (reuse `setFile`'s guard).
    - Offline grep returns nothing; `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"` still present; `pytest -q` green.
  - Notes: Invoke `frontend-design` for the record-panel UI. Free the mic (`stream.getTracks().forEach(t=>t.stop())`) after stopping. Revoke object URLs after use. Match T0's chosen IDs. If a recorded blob cannot actually be transcribed by the existing endpoint, STOP and surface it as a blocker (do not edit the backend). Paste offline-grep + `pytest -q` output into your work log. Prefix commit `@frontend:`.

- [x] **T3** [done] @frontend — Add post-transcription speaker renaming, applied live (feature 3).
  - Acceptance:
    - After results render, each DISTINCT speaker can be renamed to a custom Hebrew/free-text name via a **small editable per-speaker legend** (guide's chosen pattern: a compact legend listing each distinct speaker with an editable name field — NOT inline-per-turn editing). Pure client-side — NO backend change, response contract untouched.
    - Renaming a speaker updates ALL of that speaker's turns/segments live (every place that speaker's display name appears, incl. the avatar/legend), keyed by the existing `speakerKey(label)`.
    - The custom names are stored in the shared client-side state defined in T0 (e.g. `speakerNames[key]`) so they are the names used by the MD export in T4. The display-name lookup falls back to the existing `speakerName(label)` Hebrew default when no custom name is set.
    - Re-running a transcription (new results) resets/rebuilds the speaker-name state for the new data (no stale names leaking across runs).
    - Offline grep returns nothing; test invariants still present; `pytest -q` green.
  - Notes: Invoke `frontend-design` for the editable-name control. Keep edits accessible (label/aria, keyboard-usable). Escape user-entered names when injecting into the DOM (reuse the existing `escapeText` helper). Match T0's state shape and IDs. Paste offline-grep + `pytest -q` output into your work log. Prefix commit `@frontend:`.

- [x] **T4** [done] @frontend — Add client-side Markdown (.md) download of the transcript (feature 4).
  - Acceptance:
    - A "download Markdown" button (Hebrew label) appears in the results header (per T0's `#downloadMdBtn` or equivalent). Disabled/hidden until results exist.
    - Clicking it builds a Markdown string entirely client-side: a header with language and num_speakers, then segments grouped by speaker (same turn grouping as the on-screen view) with mm:ss–mm:ss ranges (reuse `fmtTime`) and the segment text. Speaker names use the renamed values from T3's state when set, otherwise the `speakerName` default.
    - Download happens via `Blob([md], {type:"text/markdown"})` + `URL.createObjectURL` + a temporary `<a download="transcript.md">` — NO server round-trip, NO libraries. The object URL is revoked after the click.
    - The .md content reflects the CURRENT renamed speaker names at click time (i.e. rename in T3 then export reflects the new names).
    - Offline grep returns nothing; test invariants still present; `pytest -q` green.
  - Notes: Invoke `frontend-design` for the button styling so it fits the T1 theme. Keep the Markdown simple and valid (headings + plain lines). Match T0's IDs and read the same speaker-name state as T3. Paste offline-grep + `pytest -q` output into your work log. Prefix commit `@frontend:`.

- [x] **T5** [done] @qa — Add static-string guard tests for the four new features and re-confirm the full suite.
  - Acceptance:
    - New/extended tests (in the style of `tests/test_web_offline.py`: `TestClient(main.app)` without the lifespan context manager, pure static-string/regex assertions against `GET /` HTML) covering:
      - The offline grep equivalent in Python still passes (no `https?://`, `fonts.googleapis`, `fonts.gstatic`, `//cdn`) — extend/keep the existing offline test green against the new markup.
      - Test invariants present: `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"`.
      - Record feature markers present in served HTML (e.g. the record/stop/save control IDs or their Hebrew labels, and a `MediaRecorder` / `getUserMedia` reference in the inlined script).
      - Speaker-rename feature marker present (e.g. the rename control ID/label or the `speakerNames` state token).
      - MD-download feature marker present (e.g. `#downloadMdBtn` ID/Hebrew label and a `text/markdown` reference).
    - `pytest -q` is fully green; paste the output into the work log.
  - Notes: Assert on stable IDs/strings agreed in T0 (coordinate with whatever `@frontend` actually shipped — read the final `index.html` before writing assertions). Do NOT assert on exact CSS or visual details (brittle). Follow `test-driven-development` where practical and `verification-before-completion` before claiming green. Prefix commit `@qa:`.

- [x] **T6** [done] @documenter — Update the README "Web UI" section to describe the four new features.
  - Acceptance:
    - `README.md` "Web UI" section (around line 96) updated to mention: in-browser recording (mic) as an alternative to file upload and that it reuses the same offline `/transcribe` flow; the ability to save/keep a recording locally; renaming speakers after transcription; and downloading the transcript as a Markdown `.md` file — all client-side and fully offline. Note the new professional theme briefly if relevant.
    - The doc reaffirms the page is still a single self-contained `app/static/index.html` with no remote references.
    - No code/HTML behavior changes in this task; docs only.
  - Notes: Read the final `index.html` and the feature work logs before writing so the README matches what actually shipped. Keep the existing README tone. Prefix commit `@documenter:`.

## Routing Overrides

(Empty until the Orchestrator overrides a Planner assignment. Format: `T3: planner assigned @<old> → orchestrator dispatched @<new>. Reason: ...`)

## Sprint Closeout

STATUS: PASS

**Reviewed by @reviewer on 2026-06-02.** Every task with status `done` independently verified against its acceptance criteria by inspecting the actual `app/static/index.html`, `README.md`, `tests/test_web_features.py`, git history, and by running the offline grep, `node --check`, and the full pytest suite. No backend edit occurred this sprint.

- **T0 (@architect) — PASS.** Decision note present in `work-logs/architect.md`: pins the canonical IDs (`#recordPanel/#recordBtn/#stopBtn/#recPreview/#recSave/#recUse/#recStatus`, `#speakerLegend`, `#downloadMdBtn`), the `speakerNames[speakerKey(label)]` state, the `displayName()` fallback-to-`speakerName()` rule, the "route recorded blob through `setFile`/`submit()` (no parallel path)" decision, and "NO backend change" with the single decode-failure blocker condition. All four required points covered.
- **T1 (@frontend theme) — PASS.** `index.html` CSS reworked to a cool slate/teal professional theme. Existing IDs intact: confirmed `#dropzone`, `#fileInput`, `#submitBtn`, `#results`, `#transcript` all still present. `app/main.py` and `app/schemas.py` UNCHANGED across the sprint (`git diff 7c85ef2..HEAD` = 0 lines each; only `README.md`, `app/static/index.html`, `tests/test_web_features.py` changed).
- **T2 (record) — PASS.** Record panel with all seven T0 IDs present; uses `navigator.mediaDevices.getUserMedia({audio:true})` + `MediaRecorder` (no libs). Recorded `File` routed through existing `setFile(file)` (line 1171) — exactly ONE `fetch("/transcribe", ...)` call in the whole file (line 1510), no parallel upload. Save uses `Blob` + `URL.createObjectURL` + temporary `<a download>` with revoke (lines 1178-1192). Mic freed via `getTracks().forEach(...stop())`. Graceful Hebrew handling for permission-denied (`NotAllowedError`) and unsupported browser (feature-detect `navigator.mediaDevices`/`window.MediaRecorder`, lines 1011-1013).
- **T3 (rename) — PASS.** `#speakerLegend` with per-speaker inputs (`spk-name-<key>`, `data-speaker-key`, label/aria). Shared `speakerNames = {}` state + `displayName(label)` helper used in `renderResults` (avatar initial + `.who` label, lines 1376-1399). State reset (`speakerNames = {}`) at the START of `renderResults` (line 1323) — no stale names across runs. User names injected only via `textContent`/`input.value`/`placeholder`, never raw `innerHTML` — no injection.
- **T4 (MD export) — PASS.** `#downloadMdBtn` in the results header (hidden/disabled until results). `buildMarkdown(result)` uses `groupSegments` + `fmtTime` + `displayName(turn.label)` (read at click time → reflects renames). Download via `new Blob([md], {type:"text/markdown"})` + `URL.createObjectURL` + `<a download="transcript.md">` with `URL.revokeObjectURL` (lines 1472-1481).
- **T5 (@qa) — PASS.** `tests/test_web_features.py` present with six static-string tests (offline, contract invariants, record IDs, media APIs, rename legend + `speakerNames`, `#downloadMdBtn` + `text/markdown`). Every asserted ID/token confirmed to actually exist in the shipped `index.html`.
- **T6 (@documenter) — PASS.** `README.md` "Web UI" section (from line 96) documents all four features — mic recording feeding the same offline `/transcribe` flow under the 25 MiB limit (lines 123-130), save/keep recording locally, live per-speaker renaming (136-139), client-side Markdown `.md` download (140-142), and the refreshed professional theme — and reaffirms the single self-contained `app/static/index.html` with no remote references.

**Offline grep:** `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → returned NOTHING (exit 1). Invariants present: `<html lang="he" dir="rtl">` (1), `/transcribe` (2), `type="file"` (2).

**JS sanity:** extracted the single inline `<script>` (29,392 chars) and ran `node --check` (node v24.4.1) → OK (valid syntax).

**Whole suite:** `.venv/bin/python -m pytest -v` → **65 passed, 2 warnings in 5.40s** (fully green; 2 warnings are pre-existing deprecation notices, unrelated to this sprint).

**NOTE / residual risk:** Live-browser interaction testing was NOT performed. The record (mic capture → preview → use/save), live speaker-rename, and Markdown-download click-through behaviors were verified by code review + `node --check` + static-contract tests only — no headless browser driver is available in this environment. A manual browser smoke test of those three runtime flows is the recommended follow-up before relying on them in production. This is the residual risk attached to this PASS.
