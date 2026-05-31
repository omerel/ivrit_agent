# Work Log — @backend

## 2026-05-31T21:10:00 — Task T4

**Task:** Implement the FastAPI app — startup model loading + `POST /transcribe`
returning diarized JSON, following @architect's T2 spec and the T1 verified contract.

**What I built (TDD — tests first, watched them fail on missing `app` module, then implemented):**
- `app/__init__.py` — package marker so `import app.main` works.
- `app/config.py` — Pydantic v2 `Settings(BaseSettings)` from `pydantic_settings`
  with the 11 fields (incl. `BATCH_SIZE`) and `main.py`-matching defaults; module
  singleton `settings`; `REPO_ROOT`; `diarization_config_path` property that
  resolves a relative `DIARIZATION_CONFIG` against the repo root (absolute override
  honored); sets `os.environ["HF_HUB_OFFLINE"]` from the setting at import time.
  No model loading at import.
- `app/schemas.py` — `Segment{speaker,text,start,end}` and
  `TranscriptionResponse{segments, language?, num_speakers?}`.
- `app/transcription.py` — `TranscriptionPipeline` class: `load()` loads whisper
  model + `DiarizationPipeline` once and logs a single `"Models loaded"` line;
  `transcribe(audio_path, min_speakers=None)` mirrors `main.py`
  (load_audio → transcribe → diarize → assign_word_speakers), maps segments to
  `{speaker,text,start,end}` with `"UNKNOWN"` fallback, and returns
  `(segments, language, num_speakers)`. Passes `str(settings.diarization_config_path)`,
  `batch_size=settings.BATCH_SIZE`, `language=settings.LANGUAGE`. whisperx/torch
  imported at module level (import-only; no download) — model load deferred to `load()`.
- `app/main.py` — FastAPI app with `lifespan` that builds the pipeline, calls
  `.load()`, stores it on `app.state.pipeline` (cleared on shutdown). `POST /transcribe`
  accepts `file: UploadFile`: rejects empty (400) and oversized (413) uploads BEFORE
  touching the pipeline, writes bytes to `NamedTemporaryFile(suffix=..., delete=False)`,
  calls `pipeline.transcribe`, builds `TranscriptionResponse`, `os.unlink`s the temp
  file in `finally`, and maps pipeline failures to a clean HTTP 500 (no internals
  leaked). Added `GET /health` → `{"status":"ok"}`. No model load at import time.
- `.env.example` — every env var with its default and a short comment.
- `pyproject.toml` — added a `[dependency-groups] dev` with `pytest` + `httpx`
  (needed for `TestClient`); ran `uv sync --group dev`.
- `tests/` — 15 tests: config defaults/override/HF-offline-export/path-resolution;
  schema shape; endpoint health, success, empty→400, oversized→reject (never reaches
  pipeline), pipeline error→500 (message not leaked), temp-file cleanup, and
  import-does-not-load-models. Endpoint tests inject a `FakePipeline` onto
  `app.state` so no real model is ever loaded.

**Test results:** `uv run pytest tests/ -q` → **15 passed** (2 unrelated
third-party deprecation warnings).

**Import-check output (zero env vars set, no model download):**
```
$ env -u WHISPER_MODEL ... -u HF_HUB_OFFLINE uv run python -c "import app.main; ..."
import ok
HF_HUB_OFFLINE= 1
pipeline on state at import? False
```
(plus harmless `objc[...] Class AVFFrameReceiver implemented in both ...` ffmpeg
dylib-collision notices from importing whisperx — not errors.)

**Endpoint contract for downstream (T6/T7):**
- URL path: `POST /transcribe`
- Multipart field name: `file`
- Health check: `GET /health` → `{"status":"ok"}`

**Files touched:**
- created: `app/__init__.py`, `app/config.py`, `app/schemas.py`,
  `app/transcription.py`, `app/main.py`, `.env.example`,
  `tests/__init__.py`, `tests/test_config.py`, `tests/test_schemas.py`,
  `tests/test_main.py`
- modified: `pyproject.toml` (dev deps), `uv.lock`
- `sprints/.../plan.md` — T4 → done; this work-log entry.

**Commit:** `42abd64` — `@backend: implement FastAPI transcribe endpoint with startup model loading`

**Blockers:** None. (Did NOT run a real model load / transcription — that is T8's job per the task.)

## 2026-05-31T22:05:00 — Task T6

**Task:** Write a Python REST client example (`client_example.py`) that POSTs the
sample audio to `/transcribe` as `multipart/form-data`, matching the exact T4
endpoint contract.

**What I built (TDD — tests first, watched all 6 fail on missing file, then implemented):**
- `client_example.py` (repo root):
  - Module docstring explaining the server must be running first, pointing at the
    T5 run command `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`, and
    documenting the full endpoint contract.
  - `DEFAULT_AUDIO = "resource/audio smaples/audio_sample_1min.m4a"` — exact literal,
    space + "smaples" typo preserved, handled as a plain string / `Path` (no shell
    escaping). `DEFAULT_URL = "http://localhost:8000"`. `REQUEST_TIMEOUT = 600`.
  - `build_parser()` — argparse with optional positional `audio` (defaults to
    `DEFAULT_AUDIO`) and `--url` (defaults to `DEFAULT_URL`).
  - `format_segments()` — renders `[speaker] text` lines, `UNKNOWN` fallback,
    mirroring `main.py`.
  - `check_health()` — best-effort `GET /health` probe; prints a friendly "start the
    server first" message and exits non-zero if the server is down.
  - `transcribe()` — POSTs via `files={"file": (name, fileobj, "audio/m4a")}` with the
    600s timeout, raises for status, returns parsed JSON.
  - `main()` — validates the file exists, health-checks, uploads, prints the
    `[speaker] text` lines then the indented raw JSON; `if __name__ == "__main__"` guard
    via `raise SystemExit(main())`.
- `tests/test_client_example.py` — 6 tests: module parses; `DEFAULT_AUDIO` exact literal;
  `DEFAULT_URL`; argparser defaults; argparser overrides (positional + `--url`);
  `format_segments` (speaker present + UNKNOWN fallback). No live server needed.

**Test results:** `uv run pytest tests/test_client_example.py -q` → **6 passed**.

**Parse + --help output (required by task):**
```
$ uv run python -c "import ast; ast.parse(open('client_example.py').read()); print('parse ok')"
parse ok

$ uv run python client_example.py --help
usage: client_example.py [-h] [--url URL] [audio]

POST an audio file to the ivrit_agent /transcribe endpoint.

positional arguments:
  audio       Path to the audio file to transcribe (default: 'resource/audio
              smaples/audio_sample_1min.m4a').

options:
  -h, --help  show this help message and exit
  --url URL   Base URL of the transcription server (default:
              http://localhost:8000).
```

**Endpoint contract used (matches T4 exactly):** `POST {url}/transcribe`, multipart
field `file`, content-type `audio/m4a`; response `{segments:[{speaker,text,start,end}],
language, num_speakers}`; health `GET {url}/health` → `{"status":"ok"}`.

**Files touched:**
- created: `client_example.py`, `tests/test_client_example.py`
- modified: `sprints/.../plan.md` (T6 → done), this work-log entry.

**Blockers:** None. (Did NOT run against a live server — that is T8's job.)
