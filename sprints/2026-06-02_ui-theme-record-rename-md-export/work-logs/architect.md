# Work Log — @architect

## 2026-06-02T09:44:36Z — Task T0

**Task:** Lock the integration plan for the four UI features inside the single-file `app/static/index.html` so the serial frontend tasks T1–T4 share IDs and the speaker-name state shape.

**What I did:** Read `CLAUDE.md`, `.claude/team.md`, the active `plan.md` (T0 acceptance, Context & Design Decisions, HARD CONSTRAINTS), `app/static/index.html` (full) and `app/main.py` (the `/transcribe` endpoint). Pinned the shared contract below. No code changed.

### 1. Backend: NO change needed (confirmed)
`POST /transcribe` (`app/main.py:80`) takes the multipart field `file` (`UploadFile`), writes the bytes to a temp file using **the uploaded filename's suffix** (`Path(file.filename or "").suffix`, line 91) and lets ffmpeg sniff the format. The record flow builds `new File([blob], "recording.webm", {type: blob.type})`, so the suffix is `.webm` and ffmpeg decodes the Opus/WebM container exactly as it does an uploaded `.m4a`/`.mp3`. The blob travels the existing `submit()` → `FormData.append("file", selectedFile, selectedFile.name)` path unchanged.
- **The ONE fallback / blocker condition:** if, during T2, a genuine recorded `audio/webm` blob sent through `setFile()` + `submit()` comes back as a real decode/transcription failure from `/transcribe` (HTTP 500 "Transcription failed" caused by ffmpeg rejecting the container) — i.e. the round-trip cannot work without a server change. In that case T2 STOPS and surfaces a blocker to the guide. Do NOT edit `app/main.py`. (A different recorder mime such as `audio/mp4`/`audio/ogg` with the matching filename suffix is still in-scope and NOT a blocker — only a true "no recorded blob decodes" situation is.)

### 2. New DOM regions / IDs (canonical — all four tasks MUST use these exact IDs)
Verified against every existing id in `index.html` (`dropzone, fileInput, filebar, fileName, fileSize, clearBtn, submitBtn, alert, alertTitle, alertMsg, loading, elapsed, results, statLang, statSpeakers, statSegments, transcript`). **None of the new IDs below collide.**

**T2 — record panel** (place inside/after the upload `.card`, before the `#alert`):
- `#recordPanel` — container for the recording UI.
- `#recordBtn` — start recording (Hebrew label, e.g. "הקלטה").
- `#stopBtn` — stop recording (e.g. "עצירה").
- `#recPreview` — `<audio controls>` element for preview playback of the captured clip.
- `#recSave` — download/keep the recorded clip locally (client-side Blob download).
- `#recUse` — "use this recording for transcription" → calls existing `setFile(file)`.
- `#recStatus` — small Hebrew status/timer line (recording state, unsupported-browser / permission-denied messaging may also reuse the existing `showError(...)` alert pattern).

**T3 — editable per-speaker legend** (guide's chosen pattern: a compact legend, NOT inline-per-turn editing):
- `#speakerLegend` — container rendered by `renderResults`, listing each DISTINCT speaker.
- Per-speaker `<input>` keyed by `speakerKey(label)`: use `id="spk-name-" + key` and `data-speaker-key="<key>"` plus an associated `<label>`/`aria-label` for accessibility. Keep keyboard-usable.

**T4 — Markdown download:**
- `#downloadMdBtn` — button in the results header (the `.summary` block, near `.res-title`). Disabled/hidden until results exist; enabled by `renderResults` when there are segments.

### 3. Shared speaker-name state (single source of truth for T3 + T4)
One module-scoped object inside the existing IIFE:
```js
var speakerNames = {};            // speakerNames[ speakerKey(label) ] = customName (string)
function displayName(label) {     // single lookup rule used EVERYWHERE a speaker name is shown
  var key = speakerKey(label);
  var custom = speakerNames[key];
  return (custom != null && custom !== "") ? custom : speakerName(label);
}
```
- Keyed by the SAME `speakerKey(label)` the existing code already uses for grouping/colors (`index.html` `speakerKey`, line 609).
- **Display-name rule:** `speakerNames[key]` if set & non-empty, else fall back to the existing Hebrew default `speakerName(label)` (line 598). T1–T4: replace the current direct `speakerName(turn.label)` call in `renderResults` (line 743) and any avatar/legend/turn-name render with `displayName(...)` so renames propagate live.
- T3 writes `speakerNames[key]` on input; on edit it must re-render the affected turns/avatar/legend live. T4 reads `displayName(...)` at click time so the `.md` reflects current names.
- **Escaping:** user-entered names are escaped via the existing `escapeText` (line 613) wherever injected into the DOM.

### 4. Recorded blob goes through the SAME submit() path
The record panel does NOT add a parallel upload. `#recUse` calls the existing `setFile(file)` (line 636), which enforces the empty-file and 25 MiB `MAX_UPLOAD_BYTES` guard (lines 640–652) and toggles `#submitBtn`. The user then presses the existing `#submitBtn` → existing `submit()` (line 792) → existing POST to `/transcribe`. An over-25-MiB recording is rejected with the existing Hebrew "הקובץ גדול מדי" message for free.

### 5. Rename-state reset rule (no stale names across runs)
`speakerNames` must be rebuilt per transcription so names don't leak between runs. **Hook:** reset `speakerNames = {}` at the START of `renderResults(data)` (line 704), before grouping/rendering — this guarantees a fresh run with new `data.segments` starts with default Hebrew names and the legend is rebuilt from the current run's distinct speakers.

**Files touched:** this work-log only (no source files).
**Blockers:** none. T0 done.
