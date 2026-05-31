# Work Log — @qa

## 2026-05-31T20:30:00 — Task T8

**Task:** Acceptance gate — validate the `/transcribe` endpoint + `client_example.py`
end-to-end against the small `resource/audio smaples/audio_sample_1min.m4a`, using a
**REAL** (not mocked) transcription per the guide decision.

**Determination: REAL run.** Not mocked. Feasibility was confirmed up front:
- Whisper model `ivrit-ai/whisper-large-v3-turbo-ct2` is fully cached in the HF hub
  (`~/.cache/huggingface/hub/models--ivrit-ai--whisper-large-v3-turbo-ct2/snapshots/.../model.bin`
  + config/tokenizer/vocabulary present), so `HF_HUB_OFFLINE=1` does not block it.
- Diarization model present locally at `models/pyannote-diarization/config.yaml` (+ embedding/plda/segmentation).
- Sample audio present (1,465,908 bytes).

### Step 1 — Server startup (default env vars, zero set)
Command: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` (backgrounded, log → /tmp/uvicorn_8000.log).
- **Startup time ≈ 19s** (epoch 1780248187 → 1780248206), measured from launch to the "Models loaded" log line.
- Server log showed a SINGLE `INFO:ivrit_agent:Models loaded` line at startup, after
  `Loading models (whisper=ivrit-ai/whisper-large-v3-turbo-ct2, device=cpu)...` and
  `Loading diarization model: .../models/pyannote-diarization/config.yaml`, then `Application startup complete`.
- Harmless `objc[...] Class AVFFrameReceiver implemented in both ...` ffmpeg dylib-collision
  notices (not errors).

### Step 2 — GET /health
`curl http://localhost:8000/health` → `{"status":"ok"}` HTTP 200.

### Step 3 — REAL client transcription
`uv run python client_example.py` (default sample).
- **Wall-clock ≈ 131s (~2m11s)** (epoch 1780248415 → 1780248546). Exit code 0.
- Output `[speaker] text` lines (first few):
  ```
  [SPEAKER_03]  אני שומע את זה. לפולקמן זה נעים, אז הוא אומר שזה יענה. חברים יקרים, אני שואל, באגף שוק ההון. ...
  [SPEAKER_04]  אתה זוכר איזה דגמנים, אדוני, לקבל ממך את החומר לגבי עמדתך בעניין העיצומים, ...
  [SPEAKER_00]  באמתי
  ```
- Raw JSON: 3 segments, `language: "he"`, `num_speakers: 3`. Segment starts/ends span 0.031 → 60.19s.

### Step 4 — Schema validation against TranscriptionResponse
Parsed the live response JSON through the actual Pydantic model
(`TranscriptionResponse.model_validate(...)`): PASSED.
- `segments` is a non-empty list (3); each segment: `speaker` (str), `text` (str),
  `start` (float), `end` (float). `language` ("he") and `num_speakers` (3) both present.
- No schema mismatch — no action needed from @backend.

### Step 5 — Models loaded ONCE (no per-request reload)
- `grep -c "Models loaded" /tmp/uvicorn_8000.log` → **1**.
- Log ordering: `Models loaded` (line 10) appears BEFORE any request line
  (`GET /health` and `POST /transcribe` at lines 13–17), confirming startup-time load.
- Made a SECOND `POST /transcribe` request (curl, 200, 3 segments). Re-checked log:
  still exactly **1** `Models loaded` line (two POST /transcribe 200 lines, one load line)
  → no per-request reload. Second request also ~133s, consistent with reusing the loaded model.

### Step 6 — Env-var configuration
- Default server's process environment had **none** of the tunable env vars set
  (WHISPER_MODEL/DEVICE/COMPUTE_TYPE/LANGUAGE/DIARIZATION_CONFIG/MIN_SPEAKERS/MAX_UPLOAD_BYTES/HOST/PORT/HF_HUB_OFFLINE)
  — confirmed via `ps eww` — so defaults from `app/config.py` were used.
- `Settings()` with no env → `PORT=8000`; with `PORT=8123` env → `PORT=8123` (override read correctly).
- End-to-end bind: stopped the 8000 server, launched with `PORT=8123` driving
  `uvicorn.run(host=settings.HOST, port=settings.PORT)`. Log:
  `Uvicorn running on http://0.0.0.0:8123`. `GET http://localhost:8123/health` → 200
  `{"status":"ok"}`; port 8000 no longer reachable (HTTP 000). Override demonstrated.
  NOTE: `app/main.py` has no `__main__`/`uvicorn.run` runner, so the documented T5 command
  passes `--host/--port` as CLI flags to uvicorn (uvicorn does not natively read the `PORT`
  env var). The app's `settings.PORT` was exercised via an explicit `uvicorn.run(port=settings.PORT)`
  runner to prove the env-var path binds. This is informational, not a defect.

### Step 7 — Cleanup
All background uvicorn/app processes killed; `pgrep` confirms none remain.

**Real vs mock:** REAL end-to-end run (whisperx + pyannote on CPU). No mock used.

**Files touched:**
- created: this work-log (`sprints/.../work-logs/qa.md`).
- modified: `sprints/.../plan.md` (T8 in_progress → done).
- No app/test code changed (no schema mismatch found).

**Blockers/failures:** None. All acceptance criteria met.
