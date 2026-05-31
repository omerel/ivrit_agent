# Sprint: Create a FastAPI app that accepts an audio file upload and returns JSON of the transcription after STT + speaker diarization

**Started:** 2026-05-31
**Goal:** Build a FastAPI service that accepts an uploaded audio file and returns structured JSON of speaker-diarized Hebrew transcription, derived from the working `resource/main.py` whisperx + pyannote pipeline.

## Context (read before starting)

- Reference pipeline: `resource/main.py` — loads `whisperx` model `ivrit-ai/whisper-large-v3-turbo-ct2` on CPU with `compute_type="int8"`, runs `model.transcribe(..., language="he")`, then `DiarizationPipeline` from a **local** config at `./models/pyannote-diarization/config.yaml`, then `whisperx.assign_word_speakers`, and prints `[speaker] text` per segment.
- Offline mode is mandatory: `main.py` sets `os.environ["HF_HUB_OFFLINE"] = "1"` and the diarization model is loaded from the local `models/pyannote-diarization/` folder (config.yaml + embedding/ + plda/ + segmentation/). Preserve this — do not introduce network-dependent model loading.
- Sample audio for the client example and manual testing: `resource/audio smaples/audio_sample_1min.m4a` (~1.4 MB, 1 minute). Note the folder name has a typo ("smaples") and a space — paths must be quoted.
- `whisperx.load_audio()` takes a **file path** (uses ffmpeg under the hood), not bytes — uploaded bytes must be written to a temp file before transcription.
- Model loading (whisper + diarization pipeline) is **expensive** and MUST happen once at app startup (FastAPI lifespan), not per request.
- Current `pyproject.toml` only depends on `whisperx>=3.8.6`; FastAPI/uvicorn/client deps must be added.

**Guide decisions (post-plan approval, 2026-05-31):**
- **Real validation, small file:** T8 must perform a **real** end-to-end transcription run (NOT mocked) using the small `resource/audio smaples/audio_sample_1min.m4a` (1.4 MB, ~1 min) so it runs fast on CPU. Only fall back to a shorter file/mock if the real run is genuinely infeasible, and document why.
- **Config via env vars:** ALL tunable settings (model name, device, compute type, language, diarization config path, min speakers, host, port, max upload size, HF offline flag) must be read from **environment variables with sensible defaults** (e.g. via Pydantic `BaseSettings` / `os.getenv`). The app must run with zero env vars set, using defaults that match `main.py`.

## Tasks

- [x] **T1** [done] @researcher — Confirm and document the exact runtime contract of `resource/main.py` so downstream tasks build on verified facts.
  - Acceptance: A short findings note (in `@researcher` work-log) that confirms: (1) the exact whisperx call signatures used (`load_model`, `transcribe`, `DiarizationPipeline`, `assign_word_speakers`), (2) the shape of each item in `final_result["segments"]` (keys: `start`, `end`, `text`, `speaker`, `words`), (3) that the local diarization config path resolves relative to repo root, and (4) the required env/offline settings. Any discrepancy from this plan's Context section is flagged.
  - Notes: Do not run the full model (slow/heavy) unless trivial; inspect whisperx source/docs to confirm `assign_word_speakers` output keys. The segment JSON schema you confirm here is the contract for T4 and T6.

- [x] **T2** [done] @architect — Define the app module layout, the response JSON schema, the model-loading-at-startup strategy, and the env-var configuration design.
  - Acceptance: A design note (in `@architect` work-log) specifying: (1) file layout — `app/main.py` (FastAPI app + lifespan), `app/transcription.py` (pipeline wrapper), `app/schemas.py` (Pydantic models), `app/config.py` (env-driven settings); (2) the response model — top-level object with `segments: list[Segment]` where `Segment = {speaker: str, text: str, start: float, end: float}` plus optional `language` and `num_speakers`; (3) decision that whisper model + diarization pipeline load once in a FastAPI `lifespan` handler and are stored on `app.state`; (4) how the temp-file handling for uploads works (write bytes to `NamedTemporaryFile`, pass path to `whisperx.load_audio`, delete in `finally`); (5) **env-var config design** — define a Pydantic `BaseSettings` (or `os.getenv`-based) `Settings` object listing every tunable with its env var name and default value: `WHISPER_MODEL` (default `ivrit-ai/whisper-large-v3-turbo-ct2`), `DEVICE` (`cpu`), `COMPUTE_TYPE` (`int8`), `LANGUAGE` (`he`), `DIARIZATION_CONFIG` (`models/pyannote-diarization/config.yaml`), `MIN_SPEAKERS` (`2`), `MAX_UPLOAD_BYTES` (e.g. `26214400` = 25 MB), `HOST` (`0.0.0.0`), `PORT` (`8000`), `HF_HUB_OFFLINE` (`1`). The app MUST run with zero env vars set.
  - Notes: Keep it minimal and single-process — no queue/worker system this sprint. Honor offline/local-model constraints from Context. Defaults must match `main.py` exactly. This note is the spec @backend implements in T4.

- [x] **T3** [done] @architect — Recommend the audio-send mechanism for the API and justify it.
  - Acceptance: A decision note (in `@architect` work-log AND summarized into the README task T7) that compares the three options — `multipart/form-data` file upload, base64-in-JSON, and remote URL — and **recommends `multipart/form-data`**, with justification covering: payload efficiency (no ~33% base64 bloat), native streaming/large-file support, idiomatic FastAPI `UploadFile`, and avoidance of SSRF/network-fetch concerns that a URL approach introduces. Note when base64/URL would be preferable (e.g., async/queued processing, client can't do multipart) as secondary options.
  - Notes: This recommendation drives the endpoint signature in T4 (`file: UploadFile`). Keep it to a focused comparison; the README (T7) will surface it to the client.

- [x] **T4** [done] @backend — Implement the FastAPI app: startup model loading + `POST /transcribe` endpoint returning diarized JSON.
  - Files: create `app/main.py`, `app/transcription.py`, `app/schemas.py`, `app/config.py`.
  - Acceptance: (1) `app/config.py` defines an env-driven `Settings` object (Pydantic `BaseSettings` or `os.getenv` with defaults) exposing every tunable from T2 — `WHISPER_MODEL`, `DEVICE`, `COMPUTE_TYPE`, `LANGUAGE`, `DIARIZATION_CONFIG` (resolved from repo root), `MIN_SPEAKERS`, `MAX_UPLOAD_BYTES`, `HOST`, `PORT`, `HF_HUB_OFFLINE` — each read from its env var with a default matching `main.py`; the module also sets `os.environ["HF_HUB_OFFLINE"]` from the setting. The app MUST import and run with zero env vars set. (2) `app/transcription.py` exposes a `TranscriptionPipeline` class with a `load()` method (loads whisper model + `DiarizationPipeline` once) and a `transcribe(audio_path, min_speakers=settings.MIN_SPEAKERS)` method that mirrors `main.py` (transcribe → diarize → `assign_word_speakers`) and returns a list of `{speaker, text, start, end}` dicts. (3) `app/schemas.py` defines the Pydantic `Segment` and `TranscriptionResponse` models from T2. (4) `app/main.py` defines a FastAPI app with a `lifespan` that calls `pipeline.load()` and stores it on `app.state`, and a `POST /transcribe` endpoint accepting `file: UploadFile` that enforces `MAX_UPLOAD_BYTES`, writes bytes to a temp file, calls the pipeline, deletes the temp file in `finally`, and returns `TranscriptionResponse`. (5) Code imports cleanly: `python -c "import app.main"` succeeds (model load deferred to `lifespan`/`load()` so import alone doesn't download).
  - Notes: Reuse `main.py` logic verbatim where possible. Use `tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False)` so the suffix helps ffmpeg. Wrap transcription in try/except → return HTTP 500 with a clean message on failure, HTTP 400 on empty/invalid/oversized upload. Do NOT load models at import time (breaks `import app.main` checks) — only inside `lifespan`/`load()`. Provide a `.env.example` listing every env var with its default.

- [x] **T5** [done] @devops — Add dependencies and a documented run command for the service.
  - Files: modify `pyproject.toml`.
  - Acceptance: (1) `pyproject.toml` `dependencies` adds `fastapi`, `uvicorn[standard]`, `python-multipart` (required for `UploadFile`), and `requests` (for the client example), in addition to existing `whisperx`. (2) `uv lock` / `uv sync` succeeds (or the equivalent is documented if sync is too heavy in this environment). (3) A run command is recorded (e.g. `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`).
  - Notes: `python-multipart` is easy to forget and FastAPI raises an error without it when using `UploadFile`. Coordinate the run command wording with T7.

- [x] **T6** [done] @backend — Write a Python REST client example that calls `/transcribe` with the sample audio file.
  - Files: create `client_example.py`.
  - Acceptance: (1) `client_example.py` uses `requests` to POST `resource/audio smaples/audio_sample_1min.m4a` to `http://localhost:8000/transcribe` as `multipart/form-data` (matching the T3 recommendation), under a `files={"file": (...)}` upload. (2) It pretty-prints the returned JSON segments as `[speaker] text` lines (mirroring `main.py`'s output) plus the raw JSON. (3) The default audio path is the quoted sample path (handles the space + "smaples" typo) and is overridable via CLI arg. (4) The script is self-documenting (module docstring explaining it requires the server running first). `python -c "import ast; ast.parse(open('client_example.py').read())"` parses without error.
  - Notes: Set a generous `timeout` (CPU transcription of 1 min audio can take a while). Use the exact endpoint URL/field name defined in T4 — confirm them, don't assume.

- [ ] **T7** [pending] @documenter — Write `README.md` covering setup, run, the audio-send recommendation, the request/response contract, and the client example.
  - Files: create/modify repo-root `README.md` (currently the project has only a placeholder readme).
  - Acceptance: README contains: (1) project summary; (2) install/run instructions matching T5; (3) the `POST /transcribe` contract — multipart field name, a sample `curl`, and a sample JSON response matching the T2/T4 schema; (4) a "How to send audio" section summarizing the T3 recommendation (multipart/form-data) and its justification; (5) a pointer to `client_example.py` (T6) with how to run it; (6) note on offline model requirements (the `models/pyannote-diarization/` folder must be present); (7) a **Configuration** section documenting every env var, its default, and pointing at `.env.example`. All commands, env var names, and the field name match what T4/T5/T6 actually implement.
  - Notes: Pull the comparison/justification text from @architect's T3 note. Keep the JSON example consistent with the real schema — do not invent fields.

- [ ] **T8** [pending] @qa — Validate the endpoint and client end-to-end against the sample audio.
  - Acceptance: (1) Start the server per T5's run command; (2) run `client_example.py` (T6) against the small `audio_sample_1min.m4a` for a **real** transcription (per guide decision — do not mock by default); (3) confirm a 200 response whose JSON matches `TranscriptionResponse` (segments each have `speaker`, `text`, `start`, `end`; at least one segment present); (4) confirm models loaded once at startup (a single load log line, not per-request); (5) confirm the app starts with zero env vars set (defaults work) AND that at least one setting can be overridden via env var (e.g. set `PORT` and observe it bind); (6) record the observed output (first few `[speaker] text` lines) and timing in the `@qa` work-log. Only if the real run is genuinely infeasible (e.g. whisper model not downloadable/cached in this environment), document exactly why and fall back to a mocked pipeline, clearly stating which path was taken.
  - Notes: This is the acceptance gate for the Reviewer. Be explicit about whether the run was real or mocked, and why. Surface any schema mismatch back to @backend rather than silently adjusting.

## Routing Overrides

(Empty until the Orchestrator overrides a Planner assignment. Format: `T3: planner assigned @<old> → orchestrator dispatched @<new>. Reason: ...`)

## Sprint Closeout

(Empty until the Reviewer fills it in. Format: `STATUS: PASS|FAIL`, plus per-task verification notes.)
