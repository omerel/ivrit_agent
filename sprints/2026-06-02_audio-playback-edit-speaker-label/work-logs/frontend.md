# Work Log — @frontend

## 2026-06-02T13:27:54+0300 — Task T1

**What:** Implemented Feature 1 — an inline `<audio controls>` player for the UPLOADED file in `app/static/index.html`, matching the architect's T0 contract (IDs, lifecycle, var/helper names). Invoked the `frontend-design` skill before writing markup; mirrored the existing `.rec-preview` audio styling (dashed-top separator, mono uppercase `pv-label`, `filter: saturate(.85)` on `<audio>`) so the uploaded-file player reads as the same family as the recorder preview within the cool-slate/teal theme.

**Changes (all in the single self-contained `app/static/index.html`):**
- CSS: added a `.upload-preview` / `.upload-preview.show` block (its own `.show` toggle) plus `.upload-preview .pv-label` and `.upload-preview audio`, placed right before `.filebar`. Respects `prefers-reduced-motion` via the existing global reduced-motion rule (uses the shared `fade` animation).
- Markup: added `<div class="upload-preview" id="uploadPreview">` containing `<p class="pv-label">האזנה לקובץ שהועלה</p>` and `<audio id="uploadPreviewAudio" controls preload="metadata" ...>` as a full-width flex child inside `#filebar`, after `#clearBtn`. Distinct from `#recPreview` so uploaded file and recorded clip never clobber each other's `src`.
- JS (inside the one IIFE): registered `uploadPreview` + `uploadPreviewAudio` in the `el` map; added `var uploadUrl = null;` + `revokeUploadUrl()` helper (parallel to `recBlobUrl`/`revokeRecUrl`).
  - `setFile(file)`: after accept, `revokeUploadUrl(); uploadUrl = URL.createObjectURL(file); el.uploadPreviewAudio.src = uploadUrl; el.uploadPreview.classList.add("show");` — covers ALL three entry points (file picker, drag-drop, recorder `useRecording()` which funnels through `setFile`). Player stays visible alongside results.
  - `clearFile()`: `revokeUploadUrl(); el.uploadPreviewAudio.removeAttribute("src"); el.uploadPreview.classList.remove("show");`
  - Extended the `beforeunload` handler to also call `revokeUploadUrl()`.
- No leaks: previous `uploadUrl` is revoked before each new `createObjectURL`. Only the built-in `<audio>` + `URL.createObjectURL` used — NO libraries, NO server round-trip.
- Untouched: `#dropzone`, `#fileInput`, `#filebar`, `#fileName`, `#fileSize`, `#submitBtn`, `#clearBtn`, recorder controls, `#recPreview`, and `submit()`'s `/transcribe` POST.

**Files touched:** `app/static/index.html` (only).

**Verification:**
- Offline grep: `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → no output, `GREP_EXIT=1` (nothing matched, as required).
- `node --check` on the extracted inline `<script>` → `NODE_CHECK_OK` (valid JS syntax).
- Invariants present: `lang="he" dir="rtl"` (1), `/transcribe` (2), `type="file"` (2).
- `.venv/bin/python -m pytest -q` → `65 passed, 2 warnings in 5.76s` (fully green).

**Blockers:** none. (Note: verification was static — offline grep, JS syntax check, and the pytest static-string/contract suite. No live browser render was performed in this headless run; the player behavior is exercised via the established `setFile`/`clearFile`/object-URL pattern mirrored from the recorder preview.)

**Commit:** see summary (subject prefixed `@frontend:`).

## 2026-06-02T14:05:00+0300 — Task T2

**What:** Implemented Feature 2 — PER-TURN SPEAKER REASSIGNMENT (fix diarization misattribution: move a turn to a different / new speaker), per the architect's T0 state model. Invoked the `frontend-design` skill before writing the reassignment control markup; integrated it into the established cool-slate/teal theme as a quiet utility at the end of each `.meta` row (mono `ra-lab` + hairline `<select>` on `--panel-2`, teal `--accent` focus) so it never competes with the speaker name. This is DISTINCT from and coexists with the existing global rename legend (`#speakerLegend`/`speakerNames`).

**Changes (all in the single self-contained `app/static/index.html`):**
- CSS: added a `.reassign` / `.reassign .ra-lab` / `.reassign select` block (hover, `:focus-visible` with teal outline, themed `option`) after `.bubble .time`. `margin-inline-start: auto` pushes the control to the row end in the existing `flex-wrap`/`baseline` `.meta`.
- JS (inside the one IIFE):
  - Added `var workingSegments = []` (mutable working copy = source of truth for rendering) and `var workingMeta = {language,num_speakers}`, plus `nextFreeSpeakerLabel()` which scans `/^SPEAKER[_\s-]?(\d+)$/i` over `workingSegments` and returns `SPEAKER_NN` (zero-padded) = `max+1`, so `speakerName`/`speakerKey`/`displayName`/`colorForKey` keep working.
  - Refactored `renderResults(data)`: now resets rename state + node registry, builds `workingSegments` as a shallow clone of `data.segments` objects (`{speaker,text,start,end}`), sets `workingMeta`, updates the stat tiles, then calls `buildTranscript()` and shows/scrolls results. Rebuilding `workingSegments` from fresh data each run means NO reassignment leaks across transcriptions.
  - Factored the transcript-building body into re-runnable `buildTranscript()` reading `workingSegments`/`workingMeta`: resets `speakerNodes` (NOT `speakerNames`, so custom names survive a reassignment), re-runs `groupSegments(workingSegments)`, rebuilds the transcript DOM + `#speakerLegend` (`renderLegend`) + `lastResult.turns`. Computes a full distinct-speaker set (first-seen order) across all segments for the select options.
  - Added `buildReassignControl(ti, turn, distinctLabels)`: builds `<label class="ra-lab" for="reassign-<ti>">שיוך</label>` + `<select id="reassign-<ti>" data-turn-idx="<ti>" aria-label="שיוך הקטע לדובר/ת">`. Options = each distinct speaker by `displayName(label)` (value = the speaker LABEL), current speaker pre-selected, plus final option `"דובר/ת חדש/ה"` (value `"__new__"`). On `change`: resolve the turn via `lastResult.turns[data-turn-idx]`, compute `newLabel` (`nextFreeSpeakerLabel()` for `__new__`, else the chosen label), set `seg.speaker = newLabel` for every segment in the turn (refs into `workingSegments`), then `buildTranscript()` — re-grouping merges adjacent now-same-speaker turns and updates avatar/color/name/legend.
- Interop verified by code path: reassignment and the legend rename both route through `speakerKey`/`displayName`; `speakerNames` is NOT reset inside `buildTranscript()`, so a custom name persists across reassignments and a rename after a reassignment updates all that speaker's turns. `buildMarkdown`/`#downloadMdBtn` reads `lastResult.turns` + `displayName` at click time; since `lastResult.turns` is rebuilt from `workingSegments` on every `buildTranscript()`, the Markdown export reflects corrected assignments.
- Pure client-side: no backend change, response contract untouched, still exactly one `fetch("/transcribe"`.

**Files touched:** `app/static/index.html` (only).

**Verification:**
- Offline grep: `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → no output, `EXIT=1` (nothing matched).
- Fetch count: `grep -c 'fetch("/transcribe' app/static/index.html` → `1`.
- `node --check` on the extracted inline `<script>` → `NODE_CHECK_OK` (valid JS syntax).
- Invariants present: `<html lang="he" dir="rtl">` (1), `/transcribe` (2), `type="file"` (2). Feature-2 markers: `data-turn-idx` (12), `workingSegments` (12), `דובר/ת חדש/ה` (1).
- `.venv/bin/python -m pytest -q` → `65 passed, 2 warnings in 4.82s` (fully green).

**Blockers:** none. (Note: verification was static — offline grep, fetch count, JS syntax check, and the pytest static-string/contract suite. No live browser render in this headless run; the reassignment behavior is built on the established `groupSegments`/`displayName`/`colorForKey`/`escapeText` helpers and the T0 working-copy model. A browser smoke test of the merge/re-render and Markdown export is recommended at QA (T3) if a live server is available.)

**Commit:** `1418c05` (subject `@frontend: add per-turn speaker reassignment (feature 2)`).

## 2026-06-02T15:10:00+0300 — Task T5

**Bug (guide-reported):** After transcription, using a turn's reassignment `<select>` to change its speaker caused `buildTranscript()` → `groupSegments(workingSegments)` to re-group CONSECUTIVE same-speaker segments. When the reassigned turn matched an adjacent turn's (now-same) speaker, the turns MERGED and the text blocks united. The guide wants turn STRUCTURE preserved: reassigning a turn changes only that block's speaker (label/color/name), never merging it into neighbours.

**Root cause (systematic-debugging Phase 1–2):** Turn boundaries were recomputed from the CURRENT speaker on every render (`groupSegments` groups by consecutive `speakerKey`). So reassignment of `seg.speaker` directly altered the grouping, re-merging adjacent same-speaker turns. Data flow: reassign `change` handler mutates `t.segs[].speaker` → `buildTranscript()` → `groupSegments(workingSegments)` (re-derives boundaries) → fewer turns. `buildMarkdown` only reads `turn.label` + `turn.segs[].{start,end,text}`; `/transcribe` POSTs only `selectedFile`.

**Fix (minimal, localized):**
1. In `renderResults`, after building `workingSegments`, an IIFE `freezeTurns()` tags each working segment with a STABLE original-turn id `seg._turn` from the INITIAL consecutive-speaker grouping. `_turn` is client-side-only: it is never read by `buildMarkdown` and never sent to `/transcribe`; the per-run shallow clone explicitly lists `{speaker,text,start,end}` so any prior `_turn` is dropped — no leak across runs.
2. Added `groupByFrozenTurn(segments)` next to `groupSegments`: groups by `seg._turn` instead of current speaker; each frozen turn's `key`/`label` = the current speaker of its (uniformly-reassigned) segments. Falls back to `groupSegments` if untagged.
3. `buildTranscript()` now calls `groupByFrozenTurn(workingSegments)` instead of `groupSegments(...)`. Everything else (legend, `distinctLabels` from current speakers, `data-turn-idx`, `lastResult.turns`, reassign handler via `lastResult.turns[idx]`) is unchanged — frozen turns keep a CONSTANT count/order, so `data-turn-idx` stays valid and the reassign mutation (segs are refs into `workingSegments`) still works. Initial render is identical to before (frozen ids == initial consecutive grouping). `buildMarkdown` reflects corrections because `lastResult.turns` is rebuilt from the working copy each render; `speakerNames` legend untouched, custom names survive (not reset in `buildTranscript`).

**Trace verification:** turns `[A][B][A]` → `_turn` 0,1,2. Reassign `[B]`(idx 1)→A sets speaker A on all `_turn==1` segs → `groupByFrozenTurn` still yields THREE turns `[A][A][A]` (turnIds 0,1,2), each with its own editable select (`data-turn-idx` 0/1/2), and MD export emits three `##` turn sections. Old code merged all three into one.

**Files touched:** `app/static/index.html` only (3 localized edits: `freezeTurns` tag in `renderResults`, new `groupByFrozenTurn`, switch grouping in `buildTranscript`).

**Verification (verification-before-completion):**
- `grep -nE 'https?:|//cdn|fonts\.googleapis|fonts\.gstatic|<script src|<link ' app/static/index.html` → returns NOTHING (exit 1). Offline invariant holds.
- `grep -c 'fetch("/transcribe"'` → `1` (exactly one).
- Invariants present: `lang="he" dir="rtl"` ×1, `/transcribe` ×3, `type="file"` ×2.
- `node --check` on extracted inline IIFE (37812 chars, single `<script>` block) → OK, valid JS syntax.
- `.venv/bin/python -m pytest -q` → `72 passed, 2 warnings in 4.87s` (fully green).

**Blockers:** none.
