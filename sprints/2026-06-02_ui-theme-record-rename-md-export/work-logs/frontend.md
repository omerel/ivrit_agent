# Work Log — @frontend

## 2026-06-02T11:18:00Z — Task T1

**Task:** Rework the theme of `app/static/index.html` to a more professional, restrained aesthetic (feature 1) — purely visual, no JS/ID changes.

**Skill:** Invoked `frontend-design` before writing any CSS, per HARD CONSTRAINT 4.

**Design direction chosen:** "Professional editorial console." Moved off the warm-amber "archive" theme to a cool, restrained slate/ink palette with a single confident teal accent (`--accent: #2dd4bf`). Kept light-on-dark (suits an audio/transcription tool, avoids generic-AI white). Distinctive, non-generic details: a thin top accent rule (`body::before`), a faint masked precision grid overlay replacing the paper-grain texture (`body::after`), monospace-driven metadata/labels (kicker, stat keys, time stamps, hint, footer), sharpened 1px hairlines and border-inline-start accents instead of amber glow, cooled speaker-color palette, squared seal/avatars, tightened type scale and spacing. Kept the serif display stack for headings.

**What was done (CSS only):**
- Reworked `:root` palette + tokens (cool ink/panel/line vars, teal accent set, cooled speaker A–F, added `--line-soft`, `--radius-sm`, `--shadow-soft`).
- Restyled body background (cool gradients), added top accent rule and masked grid overlay; preserved `prefers-reduced-motion` block unchanged.
- Restyled masthead/seal/kicker/h1/lede; card/dropzone/filebar; buttons (added `:focus-visible`); alert; loading wave + elapsed; results summary/stats; transcript avatars/bubbles/meta; footer.
- Minor copy/title tweaks only (title text + kicker text), no behavioral copy removed; all Hebrew RTL retained.

**Untouched (as required):** all element IDs (`#dropzone`, `#fileInput`, `#submitBtn`, `#results`, `#transcript`, `#alert`, `#loading`, etc.), all JS in the IIFE, `<html lang="he" dir="rtl">`, the literal `/transcribe`, `type="file"`, system-font stacks (no font files / no remote fonts), reduced-motion handling.

**Files touched:** `app/static/index.html`.

**Verification:**
- Offline grep `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → **no matches** (grep EXIT=1).
- `.venv/bin/python -m pytest -q` → **59 passed, 2 warnings in 5.53s** (fully green).
- Invariant grep confirms `<html lang="he" dir="rtl">`, `/transcribe`, and `type="file"` still present.
- Render sanity: served `GET /` via `TestClient(main.app)` → HTTP 200; confirmed all original IDs + new `--accent` token + `prefers-reduced-motion` present in served HTML.
- Screenshot limitation: Chrome is installed but no headless automation driver (playwright/puppeteer) is available in the venv, and I did not add remote/extra tooling to capture a programmatic screenshot. Visual change is a scoped variable/value restyle over the existing working layout; structural breakage risk is low and the render check passed.

**Blockers:** none. T1 done.

**Commit:** `b5c40ed` on branch `sprint/ui-theme-record-rename-md-export` (only `app/static/index.html` staged).

## 2026-06-02T12:05:00Z — Task T2

**Task:** Add in-browser audio recording (feature 2) that feeds the EXISTING `/transcribe` flow inside the single-file offline page, using T0's canonical IDs.

**Skill:** Invoked `frontend-design` before writing the record-panel markup so it extends the T1 "professional editorial console" theme (cool ink palette, teal accent, mono uppercase micro-labels, hairline rules). The panel uses a calm instrument-panel vocabulary: a mono "או הקליטו ישירות" kicker with a hairline rule, a record button with a red dot, a stop button with a square, a mono status/timer line with a pulsing red dot while recording, and a dashed-separated preview block with native `<audio controls>` plus the use/save actions.

**What was done (single file `app/static/index.html`):**
- **Markup:** Added `#recordPanel` inside the upload `.card` (after `#fileInput`, before `#filebar`) with `#recordBtn` (הקלטה), `#stopBtn` (עצירה, disabled initially), `#recStatus` (+`#recStatusText`) status line, `#recPreviewWrap` containing the `#recPreview` `<audio controls>`, `#recUse` (השתמשו בהקלטה לתמלול), and `#recSave` (שמרו את ההקלטה). Hebrew labels + `aria-label`/`role="status"`/`aria-live` throughout; disabled states reflect recording status.
- **CSS:** Added `.recpanel`, `.rec-head`/`.rec-kick`/`.rule`/`.rec-mic`, `.btn-rec` (+ `is-record`/`is-stop` variants, focus-visible, disabled), `.rec-status` + `.pulse` with a `recpulse` keyframe, and `.rec-preview` block — all reusing existing theme tokens. No new remote assets.
- **JS (inside the existing IIFE):** Recording module using ONLY `navigator.mediaDevices.getUserMedia({audio:true})` + `MediaRecorder`. Records `dataavailable` chunks into a `Blob`. `pickRecMime()` prefers `audio/webm` (falls back to ogg/mp4 via `MediaRecorder.isTypeSupported`); `extForMime()` keeps the download filename suffix matching the container so ffmpeg sniffs it (per T0). `onRecStop` builds the blob, frees the mic via `stream.getTracks().forEach(t=>t.stop())`, revokes the previous preview URL, and shows the preview. `useRecording()` builds `new File([blob], "recording.<ext>", {type: blob.type||"audio/webm"})` and calls the EXISTING `setFile(file)` — NO parallel upload/fetch path; the 25 MiB `MAX_UPLOAD_BYTES` guard + existing `#submitBtn`/`submit()` handle it unchanged (over-limit recordings get the existing "הקובץ גדול מדי" message for free). `saveRecording()` downloads via `Blob` + `URL.createObjectURL` + a temporary `<a download>`, revoking the URL after. Graceful Hebrew handling for permission-denied (`NotAllowedError`/`SecurityError`/`PermissionDeniedError`), no-mic (`NotFoundError`), generic failure, and unsupported browser (feature-detect `navigator.mediaDevices`/`window.MediaRecorder` → disable buttons + Hebrew status, never throw; file upload unaffected). `beforeunload` frees the stream and revokes the preview URL.

**Backend:** No backend file touched. Confirmed the recorded `audio/webm` File rides the existing multipart `file` → `/transcribe` path exactly as T0 specified; no blocker condition hit.

**Files touched:** `app/static/index.html` (only).

**Verification:**
- Offline grep `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → **no matches** (grep EXIT=1).
- `.venv/bin/python -m pytest -q` → **59 passed, 2 warnings in 4.99s** (fully green).
- Invariant grep confirms `<html lang="he" dir="rtl">` (1), `/transcribe` (2), `type="file"` (2) still present.
- Browser-runtime limitation: no headless automation driver (playwright/puppeteer) is available in the venv, so I could not script a real mic-permission/MediaRecorder run or capture a screenshot. The recording APIs require a live browser + user gesture + mic; logic was implemented to T0's contract and statically verified. A manual browser smoke test of the record→preview→use/save flow is recommended (QA/T5 covers static markers).

**Blockers:** none. T2 done.

**Commit:** `3706053` on branch `sprint/ui-theme-record-rename-md-export` (only `app/static/index.html` staged).

## 2026-06-02T12:30:00Z — Task T3

**Task:** Add post-transcription speaker renaming via a small editable per-speaker legend (feature 3), applied live across all turns. Pure client-side, no backend change.

**What I did:**
- Invoked the `frontend-design` skill before writing legend markup so it fits the established dark cool-ink / teal / serif+mono theme. Designed the legend as a compact "roster" strip between the results summary and the transcript: one row per DISTINCT speaker, each with a color swatch (same color as that speaker's avatar/bubble) and a quiet inline-editable text input (borderless until hover/focus, mono micro-label, pen affordance). Not inline-per-turn editing — a single legend, per the guide's chosen pattern.
- Added `#speakerLegend` (container) + `#speakerLegendGrid` markup, with a Hebrew header "שמות הדוברים · לחצו כדי לערוך".
- Per-speaker inputs: `id="spk-name-"+key`, `data-speaker-key="<key>"`, associated `<label for=…>` ("שם הדובר/ת") + `aria-label` ("עריכת השם של <default>"), placeholder = Hebrew default name, `maxLength=60`, keyboard-usable.
- Introduced the shared `speakerNames = {}` state (keyed by existing `speakerKey(label)`) and the `displayName(label)` helper (returns custom name if set & non-empty, else `speakerName(label)`). Replaced the direct `speakerName(turn.label)` usage in `renderResults` with `displayName(...)` for both the avatar initial and the `.who` label. Added `avatarInitial(name)` helper.
- Live update: built a `speakerNodes` registry mapping each key → its avatar/`.who` DOM nodes; on `input`, `speakerNames[key]` is set (or deleted when blank) and `refreshSpeakerName(key,label)` rewrites every registered node's `textContent` (and avatar initial/title) in place — all of that speaker's turns + avatar + legend update live.
- Reset rule: `speakerNames = {}` and `speakerNodes = {}` at the START of `renderResults`, so names never leak across transcription runs. Legend is rebuilt from the current run's distinct speakers (first-seen order).
- Escaping: all speaker names (custom + default) are injected via `textContent`/`input.value`/`placeholder` only — never `innerHTML` — so user-entered names cannot inject HTML (equivalent to the existing `escapeText` safe path).
- T4 will read the same `speakerNames` / `displayName` state for MD export.

**Files touched:** `app/static/index.html` (CSS `.legend*` block; `#speakerLegend` markup; JS: DOM refs, `speakerNames`/`displayName`/`avatarInitial`, `speakerNodes`/`registerNameNode`/`refreshSpeakerName`/`renderLegend`, and `renderResults` rework).

**Offline grep:** `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → no matches (exit 1). Invariants present: `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"`.

**pytest:** `.venv/bin/python -m pytest -q` → `59 passed, 2 warnings in 5.00s`.

**Extra verification:** extracted the inline `<script>` and ran `node --check` → JS SYNTAX OK; confirmed tokens `displayName` (1 def), `speakerNames = {}` (2 resets), `spk-name-`, `data-speaker-key`, `getElementById("speakerLegend")` all present.

**Verification limitation:** no live browser/headless runner in this environment, so the live-rename interaction was verified by code review + node syntax check rather than a real DOM click-through.

**Blockers:** none. T3 done.

## 2026-06-02T12:30:00Z — Task T4

**Task:** Add client-side Markdown (.md) download of the transcript (feature 4) to `app/static/index.html`.

**What was done:**
- Invoked the `frontend-design` skill before styling. Styled `#downloadMdBtn` using the established secondary-button vocabulary (`.btn-md`: panel-2 surface, hairline border, teal `--accent-2` icon, teal focus ring, lift-on-hover) so it complements rather than competes with the primary teal CTA. Placed it at the inline-end of the `.res-title` row in the `.summary` results header via a `.rt-spacer` flex spacer.
- Added the button markup with id `#downloadMdBtn`, Hebrew label "הורדה כ־Markdown", aria-label/title "הורדת התמלול כקובץ Markdown". Hidden + disabled by default (`.btn-md` has `display:none`, `disabled` attr); shown + enabled by `renderResults` once results exist (both the empty-segments path and the populated path).
- JS: added `downloadMdBtn` to the `el` map; added a `lastResult` state object `{language, num_speakers, turns}` stored at the end of `renderResults` (and reset/disabled at its start so nothing leaks across runs). Added `buildMarkdown(result)` — top-level `# תמלול` heading, `- שפה:` / `- מספר דוברים:` lines (null → "—"), then each turn from the SAME `groupSegments` grouping rendered as `## <displayName> (mm:ss–mm:ss)` (range via `fmtTime`) followed by each segment's text (blank → "[ללא טקסט]"). Speaker names use `displayName(turn.label)` read at click time, so T3 renames are reflected.
- Download via `new Blob([md], {type:"text/markdown"})` + `URL.createObjectURL` + a temporary `<a download="transcript.md">` appended/clicked/removed, with the object URL revoked after. No server round-trip, no libraries. Wired `el.downloadMdBtn` click → `downloadMarkdown`.
- Reused existing helpers `groupSegments`, `fmtTime`, `displayName`, and the `speakerNames` state per the architect's T0 contract. Single self-contained file; all CSS in `<style>`, all JS in the one IIFE `<script>`; no external/remote refs. Preserved `<html lang="he" dir="rtl">`, `/transcribe`, `type="file"`.

**Files touched:** `app/static/index.html`.

**Verification:**
- Offline grep `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → returned nothing (grep exit 1, no matches).
- `node --check` on the extracted inline script → OK (JS syntax valid).
- `.venv/bin/python -m pytest -q` → `59 passed, 2 warnings in 4.83s` (fully green).

**Blockers:** none. T4 done.
