# Sprint: Add "include computer audio" toggle to the in-browser recorder (mic + tab audio mixed)

**Started:** 2026-06-03
**Goal:** When a user ticks a Hebrew "include computer audio" checkbox before recording, capture the active browser tab's audio (getDisplayMedia) and the microphone (getUserMedia), mix both into one stream via the Web Audio API, and feed that single mixed stream into the existing MediaRecorder — leaving the mic-only path unchanged when the toggle is off.

## Scope notes (read before planning your edits)

- **Single file:** all changes live in `app/static/index.html`. There is no build step; the file is served as-is and is fully offline (no CDNs).
- **In scope:** Linux/Chrome tab-audio capture via `getDisplayMedia({ video: true, audio: true })`, where the requested video track is requested only to surface Chrome's "share tab audio" checkbox and is then stopped/discarded; only audio tracks are mixed.
- **Out of scope:** any OS / PipeWire setup, full-system audio, native-app audio. Browser-only.
- **Preserve unchanged:** when the toggle is OFF, `startRecording()` must behave exactly as today (mic only). The "use recording" path (`useRecording()` → `setFile()` → 25 MiB guard) and `saveRecording()` must remain untouched — the mixed blob flows through the same path.
- **Relevant existing code** (`app/static/index.html`):
  - Recording UI markup: `.rec-controls` ~lines 781-794; preview ~796-814.
  - `el` registry ~lines 934-964 (add the checkbox here).
  - Recording JS: `recSupported` ~1098, `freeStream()` ~1125, `revokeRecUrl()` ~1132, `pickRecMime()` ~1136, `startRecording()` ~1154 (getUserMedia at ~1165), `stopRecording()` ~1218, `onRecStop()` ~1224, `useRecording()` ~1248, `saveRecording()` ~1265.
  - Event wiring ~1831-1834; `beforeunload` cleanup ~1844-1847.
  - CSS theme tokens: `--accent` teal #2dd4bf (~line 24), `--panel-2` (~18), `--mono` (~38), `text-transform: uppercase` pattern for mono labels (~129, ~253). `.rec-controls`/`.btn-rec` styles ~264-288.
  - `showError(title, body)` is the existing Hebrew error pattern; `setFile()` is the existing upload-guard entry point.

## Tasks

- [x] **T1** [done] @frontend — Add the "כלול שמע מהמחשב" checkbox control to the recorder markup, register it in `el`, and style it to match the existing mono/teal/panel vocabulary.
  - Acceptance:
    - A labelled checkbox (id e.g. `incCompAudio`) appears inside/adjacent to `.rec-controls` with the Hebrew label "כלול שמע מהמחשב"; it is keyboard-focusable and has an appropriate `aria-label` or associated `<label>`.
    - The checkbox is registered in the `el` object (~lines 934-964).
    - Styling uses existing CSS custom properties (`--mono`, `--accent`/`--accent-2`, `--panel-2`) and matches the RTL layout; no new colors invented, no CDN/asset added.
    - The checkbox is disabled together with the record button when `!recSupported` (consistent with the existing `recSupported` guard at ~1836-1841).
  - Notes: Keep it visually consistent with `.rec-head .rec-kick` mono-uppercase labels. The label text must be exactly `כלול שמע מהמחשב`.

- [x] **T2** [done] @frontend — Implement tab-audio capture + Web Audio mixing in `startRecording()`, gated on the checkbox, and extend cleanup so all tracks/AudioContext are released.
  - Acceptance:
    - **Toggle OFF:** `startRecording()` path is byte-for-byte behaviorally identical to today (mic-only `getUserMedia({audio:true})` → MediaRecorder). No display prompt appears.
    - **Toggle ON:** the recorder requests `getUserMedia({audio:true})` AND `getDisplayMedia({ video:true, audio:true })`; builds an `AudioContext`; creates one `MediaStreamAudioSourceNode` per source (mic stream + display stream); connects both into a single `MediaStreamAudioDestinationNode`; and passes `destination.stream` to the existing `MediaRecorder` (mime selection via existing `pickRecMime()` unchanged).
    - The display **video** track is stopped and discarded immediately after capture (not mixed, not recorded).
    - **User cancels the share prompt** (`getDisplayMedia` rejects, e.g. `NotAllowedError`/`AbortError`): no recording starts, mic stream (if already acquired) is stopped, buttons reset to ready state, and a Hebrew `showError(...)` consistent with existing strings is shown (e.g. title "שיתוף השמע בוטל"). No uncaught promise rejection.
    - **User forgets to tick "share audio"** (display stream has zero audio tracks): **fall back to mic-only and proceed** (guide decision 2026-06-03). Stop/discard the orphaned display stream (it has no audio to mix and its video track must not be recorded), then continue recording the mic alone exactly as the toggle-OFF path would. Do NOT hard-error. A brief, non-blocking Hebrew status note is acceptable but optional; recording must still start.
    - **Cleanup / no leaks:** on `stopRecording()`/`onRecStop()` AND on the error/cancel paths AND on `beforeunload`, every acquired track (mic + display audio + display video) is `.stop()`ped and the `AudioContext` is `.close()`d. Extend or supplement `freeStream()` so it also releases the second stream and the AudioContext (e.g. track the extra stream + ctx in module-scope vars and close them in the existing cleanup helpers).
    - The resulting mixed blob still routes through the unchanged `onRecStop()` → preview → `useRecording()`/`saveRecording()` path; the 25 MiB guard in `setFile()` is untouched.
  - Notes:
    - Request `getUserMedia` first, then `getDisplayMedia`, so a denied mic doesn't leave a dangling display capture — and remember to stop the mic stream if the display step then fails.
    - Reuse `recSupported`; optionally guard `navigator.mediaDevices.getDisplayMedia` existence and fall back to a Hebrew error if absent.
    - Keep all error strings in the existing `showError(title, body)` Hebrew style. Reuse `freeStream()`/`revokeRecUrl()` rather than duplicating teardown logic.
    - Do not change `pickRecMime()`, `extForMime()`, `useRecording()`, `saveRecording()`, or `setFile()`.

- [x] **T3** [done] @qa — Manually verify both modes in Linux/Chrome and confirm no resource leaks.
  - Acceptance (record evidence in the work-log):
    - Toggle OFF: record → stop → preview plays → "use recording" populates the filebar → mic-only behavior matches pre-change baseline.
    - Toggle ON, share-with-audio: pick a tab playing audio, record a few seconds of mic+tab, stop, confirm the preview contains BOTH the spoken mic audio and the tab audio.
    - Cancel path: trigger record with toggle ON, cancel the share dialog → Hebrew error shown, buttons return to ready, no console errors, mic LED/indicator off.
    - No-tab-audio path: share a tab WITHOUT ticking "share audio" → recorder falls back to mic-only and recording starts (no hard error); resulting clip contains mic audio.
    - After each stop, verify (Chrome tab "recording"/share indicator gone, `chrome://media-internals` or devtools) that no audio context / tracks remain live — no leaks.
  - Notes: This is a browser-manual test (no automated harness exists for getDisplayMedia). If a behavior fails, report the exact step and observed vs. expected to the Orchestrator so the task can be re-routed to @frontend.

- [x] **T4** [done] @reviewer — Independent code + acceptance review of T1/T2 against this plan and the scope notes.
  - Acceptance:
    - Confirms toggle-OFF path is unchanged (mic only, no display prompt).
    - Confirms toggle-ON path matches the required Web Audio topology (two source nodes → one destination node → MediaRecorder) and discards the display video track.
    - Confirms the cancel and unsupported failure paths surface Hebrew errors via `showError` and restore the ready state; and confirms the no-tab-audio case **falls back to mic-only and records** (guide decision) rather than hard-erroring.
    - Confirms full teardown (all tracks stopped + AudioContext closed) on stop, error, and beforeunload — no leaked streams/contexts.
    - Confirms the new control uses existing CSS tokens, stays offline (no new asset/CDN), and the mixed blob still flows through the unchanged `setFile()` 25 MiB path.
    - Writes the Sprint Closeout (STATUS: PASS|FAIL + per-task notes) once T1–T3 are done.
  - Notes: Pull the diff for `app/static/index.html` only; flag any change outside the recording UI/JS as scope creep.

## Routing Overrides

(Empty until the Orchestrator overrides a Planner assignment. Format: `T3: planner assigned @<old> → orchestrator dispatched @<new>. Reason: ...`)

## Sprint Closeout

**STATUS: PASS** (code-inspection PASS on all criteria; live-browser behavioral acceptance pending the guide's hand-test — see below).

Reviewed by @reviewer on 2026-06-03 via independent inspection of commit `55411be`
(`git show --stat`, `git diff 55411be^ 55411be -- app/static/index.html`) and the
current file on branch `sprint/record-mic-plus-computer-audio`. I did not rely solely
on @frontend's or @qa's reports; I re-derived each verdict from the diff and the file.

### Environment limitation (read first)
No browser and no JS runtime exist in this environment, so live `getDisplayMedia` /
`getUserMedia` / mixing / leak behavior could NOT be executed here. All verdicts below
are **verified-by-code-inspection**. The actual runtime behavior (mixed-clip audio
content, real cancel-dialog UX, real teardown of share/mic indicators) is **pending the
guide's hand-test** using the checklist in
`sprints/2026-06-03_record-mic-plus-computer-audio/work-logs/qa.md` (Part 2, sections A-E).
This PASS certifies the code; it does NOT claim live-tested results that were not observed.

### Per-task verification

**T1 — checkbox UI — PASS (code).**
- `<label class="rec-toggle" id="incCompAudioLabel" for="incCompAudio">` with native
  `<input type="checkbox" id="incCompAudio" aria-label="כלול שמע מהמחשב">` sits INSIDE
  `.rec-controls` (container opens line 826, toggle at 839-842, container closes 843).
- Label text is exactly `כלול שמע מהמחשב`; control is both `for`-associated AND
  `aria-label`led; native checkbox is keyboard-focusable with a `:focus-visible` teal ring.
- Registered in `el` (lines 1014-1015: `incCompAudio`, `incCompAudioLabel`).
- Styling uses only pre-existing tokens (`--mono`, `--panel-2`, `--accent`, `--accent-2`,
  `--accent-ink`, `--line`, `--paper-faint`, `--paper-dim`); checkmark drawn with CSS
  borders. No new color, no CDN/asset. Diff grep for `https?://|cdn|<script src|<link href`
  on added lines: none.
- Disabled together with the record button under `!recSupported` (lines 1996-2002:
  input `.disabled=true`, label gets `.is-disabled`).

**T2 — capture + mixing + teardown — PASS (code).**
- Toggle OFF: `startRecording()` (1278) reads `includeComputer` (1288); when false it runs
  the original mic-only `getUserMedia({audio:true})` → `beginRecorder(micStream)` with no
  `getDisplayMedia` reachable, so no display prompt. `beginRecorder()` (factored out) is a
  faithful copy of the prior recorder construction (same `pickRecMime`, same listeners,
  same button/timer state) — behavioral parity confirmed against `55411be^`.
- Toggle ON topology: mic first, then `addComputerAudioAndRecord()` →
  `getDisplayMedia({video:true,audio:true})`; on success builds `AudioContext`, one
  `createMediaStreamSource` per stream (mic + display) → one `createMediaStreamDestination`,
  and `beginRecorder(dest.stream)`. Exactly two source nodes → one destination → MediaRecorder.
- Display video track stopped AND `removeTrack`ed immediately after capture, before mixing;
  only audio tracks are mixed — video is never recorded.
- Cancel/deny of share prompt: `.catch` → `freeStream()` + button reset +
  `showError("שיתוף השמע בוטל", …)`; handled on the promise chain, no uncaught rejection.
- `getDisplayMedia` absent: guard → mic released, reset, `showError("שיתוף שמע אינו נתמך", …)`.
- No-"share audio" (zero display audio tracks): orphaned display stream stopped/nulled,
  then `beginRecorder(micStream)` — FALLS BACK to mic-only and STILL records, no hard error.
  Matches guide decision 2026-06-03.
- Teardown: `freeStream()` (1178) stops all tracks of `recStream` (mic) AND
  `recDisplayStream` (display audio + residual video) and `close()`s `recAudioCtx` (try/catch),
  nulling all three. Called on `onRecStop()` (1381, the stop path), every error/cancel path
  (1253, 1314, 1362), and `beforeunload` (2006-2008). No leaked streams/contexts in any path.
- Protected functions untouched: diff contains no definition change for `pickRecMime`,
  `extForMime`, `onRecStop`, `useRecording`, `saveRecording`, or `setFile`. The mixed blob
  flows through the unchanged `onRecStop()` → preview → `useRecording()` → `setFile()` path;
  the 25 MiB guard (`MAX_UPLOAD_BYTES = 26214400`, line 974; enforced in `setFile` 1114) is
  unchanged.

**T3 — manual QA — PASS (static portion); LIVE PENDING GUIDE.**
- @qa performed a rigorous static code-trace + git-history verification (9 criteria, all
  PASS) and authored a Linux/Chrome hand-test checklist (work-logs/qa.md, Part 2). @qa
  explicitly did NOT run, and did not claim, any live-browser result. I independently
  re-verified @qa's static findings against the diff and concur. The behavioral acceptance
  criteria of T3 that require a browser (mixed-clip audio content, cancel-dialog UX,
  leak/indicator state) are **outstanding and must be observed by the guide** before the
  feature is considered runtime-verified. This is the one honest gap in the closeout.

**T4 — independent review — PASS.**
- Confirmed scope: `git show --stat 55411be` = `1 file changed, 203 insertions(+),
  41 deletions(-)`, `app/static/index.html` ONLY. No scope creep. (The repo's other
  pre-existing modified files — `pyproject.toml`, `.env.example`, `uv.lock`, etc. — are
  unrelated to this sprint and were left untouched.)
- Inline-script bracket balance re-checked independently: `{}` 181/181, `()` 575/575,
  `[]` 62/62 — balanced (balance check, not a full parse).
- All five T4 acceptance bullets verified above.

### Verdict
Code is correct, in-scope, offline, and meets every acceptance criterion by inspection —
**STATUS: PASS**. The only remaining item is the guide's live-browser hand-test
(work-logs/qa.md Part 2 A-E); if any step there deviates from Expected, reopen the sprint
and route the fix to @frontend.

