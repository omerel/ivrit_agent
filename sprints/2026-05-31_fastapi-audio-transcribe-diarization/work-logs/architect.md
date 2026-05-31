## 2026-05-31T19:45:00 — Task T3

**Task:** Recommend the audio-send mechanism for the `POST /transcribe` endpoint and justify it.

### Options compared

| # | Mechanism | FastAPI shape | Wire format |
|---|-----------|---------------|-------------|
| 1 | **`multipart/form-data` upload** | `file: UploadFile` | raw binary part |
| 2 | base64-encoded audio in JSON body | `AudioPayload(audio_b64: str)` | JSON string |
| 3 | remote URL the server fetches | `AudioRef(url: str)` | server-side HTTP GET |

### Decision

**Recommend option 1: `multipart/form-data` file upload via FastAPI `UploadFile`.**

This sets the T4 endpoint signature to `async def transcribe(file: UploadFile)` and requires the `python-multipart` dependency (tracked in T5).

### Justification (full text — T7 README reuses this verbatim)

The `/transcribe` endpoint accepts audio as a `multipart/form-data` file upload (FastAPI `UploadFile`). This is the recommended and idiomatic mechanism for sending binary audio to the service, for four reasons:

1. **Payload efficiency.** `multipart/form-data` transmits the audio as raw bytes. Base64-encoding the same audio inside a JSON body inflates the payload by roughly 33% (4 encoded bytes per 3 source bytes) and adds CPU cost on both client and server to encode and decode. For a 1-minute sample that is minor, but for longer recordings the overhead grows linearly and is pure waste.

2. **Native streaming and large-file support.** `UploadFile` is backed by a spooled temporary file: small uploads stay in memory, larger ones spill to disk, so the whole file is never forced fully into RAM the way a base64 JSON string would be. This maps cleanly onto our pipeline, which needs the bytes written to a real file path anyway (`whisperx.load_audio()` takes a path and shells out to ffmpeg). Multipart lets us stream the upload straight to a `NamedTemporaryFile` and hand that path to whisperx.

3. **Idiomatic FastAPI.** `file: UploadFile` is the framework's first-class pattern for file intake: automatic content handling, filename/content-type metadata, and clean OpenAPI docs (a file-picker in `/docs`). It is the least surprising contract for any HTTP client (`curl -F`, `requests` `files=`, browsers).

4. **No SSRF / network-fetch surface.** Having the server fetch a client-supplied URL turns the service into an HTTP client against arbitrary destinations, which is a Server-Side Request Forgery (SSRF) risk — a caller could point it at internal/cloud-metadata endpoints — and adds timeout, retry, redirect, and content-type-validation concerns plus an unpredictable external dependency. A direct upload keeps the request self-contained and the trust boundary simple.

**When the secondary options would be preferable:**

- **base64-in-JSON** makes sense when the client genuinely cannot send multipart (e.g., a constrained JSON-only API gateway, a webhook integration, or an environment where every request must be a single JSON document), accepting the ~33% size penalty for protocol uniformity.
- **remote URL** makes sense when the audio is already hosted (e.g., in object storage / a signed S3 URL) so re-uploading bytes through the API is redundant, and especially in an **async/queued** architecture where a worker pulls the object out-of-band. That is out of scope for this single-process sprint, but it is the natural mechanism if the service later grows a job queue. If adopted, it must be paired with URL allow-listing / egress controls to mitigate the SSRF concern above.

### Files touched
- `sprints/2026-05-31_fastapi-audio-transcribe-diarization/plan.md` — T3 status pending → in_progress → done.
- `sprints/2026-05-31_fastapi-audio-transcribe-diarization/work-logs/architect.md` — this entry (created file).

No source files created; this is a design decision note. The justification text above is written to be lifted directly into the README "How to send audio" section (T7).

### Blockers
None.

## 2026-05-31T20:30:00 — Task T2

**Task:** Define the app module layout, the response JSON schema, the model-loading-at-startup strategy, and the env-var configuration design. This note is the implementation spec @backend follows in T4.

This design is built directly on @researcher's verified T1 facts (segment shape, missing-`speaker` default, path-from-file, offline-before-construct, defaults from `main.py`). Where T1 and the original plan Context disagreed (no `words` key; `speaker` conditional), T1 wins.

---

### (1) File layout

Four modules under a new `app/` package (plus `app/__init__.py`, empty). All four are created by @backend in T4.

```
app/
  __init__.py        # empty — makes `app` a package so `import app.main` works
  config.py          # env-driven Settings + repo-root resolution + HF_HUB_OFFLINE export
  schemas.py         # Pydantic response models (Segment, TranscriptionResponse)
  transcription.py   # TranscriptionPipeline: load() once, transcribe(path) per request
  main.py            # FastAPI app, lifespan (calls pipeline.load()), POST /transcribe
```

**Dependency direction (one-way, no cycles):**
```
main.py  ──imports──▶ config.py, schemas.py, transcription.py
transcription.py ──imports──▶ config.py
schemas.py ──imports──▶ (pydantic only)
config.py ──imports──▶ (pydantic-settings, pathlib only)
```

**Module responsibilities:**

- **`config.py`** — owns ALL configuration. Defines the `Settings` class (see §5), instantiates a module-level singleton `settings = Settings()`, computes `REPO_ROOT`, resolves `DIARIZATION_CONFIG` to an absolute path, and — critically — sets `os.environ["HF_HUB_OFFLINE"] = settings.HF_HUB_OFFLINE` at module import time (so it is set before `transcription.py` ever constructs a pipeline). Importing this module must NOT touch the network or load any model.

- **`schemas.py`** — pure Pydantic models, no logic, no heavy imports. Defines `Segment` and `TranscriptionResponse` (see §2).

- **`transcription.py`** — wraps the `main.py` pipeline. Class `TranscriptionPipeline` with `__init__` (stores config, sets model handles to `None`), `load()` (loads whisper model + `DiarizationPipeline` ONCE — the expensive step), and `transcribe(audio_path, min_speakers=...)` (mirrors `main.py`: `load_audio` → `transcribe` → `DiarizationPipeline.__call__` → `assign_word_speakers` → map to list of `{speaker, text, start, end}` dicts with `"UNKNOWN"` fallback). `whisperx` is imported at module level (it is heavy but import-only; the *model load* happens in `load()`, not at import) — this is fine for `python -c "import app.main"` because importing whisperx does not download anything. **No model loading at import or `__init__` time** — only inside `load()`.

- **`main.py`** — defines `app = FastAPI(lifespan=lifespan)`. The `lifespan` async context manager constructs `TranscriptionPipeline(settings)`, calls `pipeline.load()` (logging a single "models loaded" line), stores it on `app.state.pipeline`, yields, and on shutdown drops the reference. The `POST /transcribe` handler reads `app.state.pipeline` (via `request.app.state`), enforces upload size, temp-files the bytes, calls `pipeline.transcribe(...)`, and returns a `TranscriptionResponse`.

**Why this split:** `import app.main` must succeed in CI/QA without downloading the 1.5 GB whisper model (T4 acceptance #5, T8 check). Keeping config/schema import-light and deferring every model load to `lifespan`/`load()` guarantees that. Config is isolated so the `HF_HUB_OFFLINE` side-effect happens exactly once, early, and in one place.

---

### (2) Response JSON schema (`app/schemas.py`)

Per T1: each pipeline segment is `{start, end, text, avg_logprob, speaker?}`. We expose only `speaker, text, start, end` (drop `avg_logprob`), defaulting a missing `speaker` to `"UNKNOWN"` in `transcription.py` BEFORE building the model (so the schema field is plain `str`, not optional).

```python
from pydantic import BaseModel

class Segment(BaseModel):
    speaker: str   # "UNKNOWN" when no diarization segment overlapped this span
    text: str
    start: float   # seconds
    end: float     # seconds

class TranscriptionResponse(BaseModel):
    segments: list[Segment]
    language: str | None = None      # echoed from final_result["language"] (TranscriptionResult)
    num_speakers: int | None = None  # len(set of speaker labels), excluding "UNKNOWN"
```

**Field ordering** in `Segment` is `speaker, text, start, end` deliberately so the JSON reads like `main.py`'s `[speaker] text` output. Example response body:

```json
{
  "segments": [
    {"speaker": "SPEAKER_00", "text": "שלום וברוכים הבאים", "start": 0.008, "end": 2.531},
    {"speaker": "SPEAKER_01", "text": "תודה שאירחתם אותי", "start": 2.6, "end": 4.92},
    {"speaker": "UNKNOWN",    "text": "מוזיקת רקע",        "start": 4.92, "end": 5.4}
  ],
  "language": "he",
  "num_speakers": 2
}
```

**Computing the optional fields (in `transcription.py`, not the schema):**
- `language` ← `final_result.get("language")` (the `TranscriptionResult` top-level key; falls back to the configured `LANGUAGE` if absent).
- `num_speakers` ← `len({s["speaker"] for s in segments if s["speaker"] != "UNKNOWN"})`; if that set is empty, return `None` (or `0` — @backend's call, but `None` is cleaner for "couldn't determine"). Recommend `None` when no real speaker labels exist.

Both optional fields default to `None` so a minimal pipeline that only produced segments still yields a valid response. `segments` is always present (possibly empty list — though in practice always ≥1 for real audio).

---

### (3) Model loading at startup (FastAPI `lifespan` + `app.state`)

**Decision:** load whisper model + diarization pipeline EXACTLY ONCE, inside the FastAPI `lifespan` handler, and store the loaded `TranscriptionPipeline` on `app.state.pipeline`. Never load per request. This is mandatory (plan Context: model loading is expensive).

```python
# app/main.py (shape, not final code)
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from app.config import settings
from app.transcription import TranscriptionPipeline

logger = logging.getLogger("ivrit_agent")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading models (whisper=%s, device=%s)...", settings.WHISPER_MODEL, settings.DEVICE)
    pipeline = TranscriptionPipeline(settings)
    pipeline.load()                       # the single expensive load
    app.state.pipeline = pipeline
    logger.info("Models loaded; service ready.")   # the one-and-only load log line (T8 checks for exactly one)
    yield
    app.state.pipeline = None             # drop reference on shutdown

app = FastAPI(title="ivrit_agent transcription", lifespan=lifespan)
```

The handler retrieves it via `request.app.state.pipeline` (inject `request: Request`). Because `load()` runs synchronously inside the async lifespan, the first request only arrives after models are ready. T8 verifies "one load log line, not per-request" against the single `logger.info("Models loaded...")`.

**Note on blocking:** `pipeline.load()` and `transcribe()` are CPU-bound and synchronous (whisperx/torch). For this single-process sprint that is acceptable (the plan forbids a queue/worker system). The endpoint may be declared `async def` but should call the blocking `transcribe` directly; @backend MAY wrap it in `anyio.to_thread.run_sync` / `fastapi.concurrency.run_in_threadpool` to avoid blocking the event loop — recommended but not required this sprint. Document whichever is chosen.

---

### (4) Temp-file handling for uploads

`whisperx.load_audio()` needs a real file PATH (it shells out to ffmpeg) — T1 confirmed. So upload bytes MUST be written to a temp file, the path handed to the pipeline, and the temp file deleted afterward. Use the original filename's suffix so ffmpeg can sniff the format.

```python
# app/main.py — POST /transcribe (shape)
import tempfile, os
from pathlib import Path
from fastapi import UploadFile, HTTPException, Request

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(request: Request, file: UploadFile):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400,
                            detail=f"Upload exceeds MAX_UPLOAD_BYTES ({settings.MAX_UPLOAD_BYTES} bytes).")

    suffix = Path(file.filename or "").suffix  # e.g. ".m4a"; "" is acceptable to ffmpeg in most cases
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()                            # close so ffmpeg can read it on all platforms
        segments, language, num_speakers = request.app.state.pipeline.transcribe(tmp.name)
        return TranscriptionResponse(segments=segments, language=language, num_speakers=num_speakers)
    except HTTPException:
        raise
    except Exception as exc:                   # pipeline/ffmpeg/model failure
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed.") from exc
    finally:
        try:
            os.unlink(tmp.name)                # ALWAYS delete the temp file
        except OSError:
            pass
```

**Key rules for @backend:**
- `delete=False` on `NamedTemporaryFile` so the handle can be closed (and the path read by ffmpeg) before deletion; deletion is done explicitly in `finally` via `os.unlink`.
- Close the file (`tmp.close()`) before passing `tmp.name` to whisperx — on some platforms a still-open handle blocks ffmpeg/cleanup.
- Read the body with `await file.read()` and size-check the in-memory `len(data)` against `MAX_UPLOAD_BYTES` (simple and correct for ≤25 MB defaults; a streaming size-guard is over-engineering this sprint).
- The `finally` runs on success, on `HTTPException`, and on pipeline failure — so the temp file is never leaked.
- HTTP status discipline: **400** for empty / oversized / unreadable upload; **500** for pipeline/ffmpeg/model failure (clean message, no stack trace leaked to the client — log the trace server-side via `logger.exception`).

---

### (5) Env-var configuration design (`app/config.py`)

**Decision: Pydantic v2 `BaseSettings` via the `pydantic-settings` package.** In Pydantic v2, `BaseSettings` moved out of the core `pydantic` package into a separate distribution `pydantic-settings` (import: `from pydantic_settings import BaseSettings, SettingsConfigDict`). @devops MUST add `pydantic-settings` to `pyproject.toml` dependencies in T5 (FastAPI already pulls in `pydantic` v2, but NOT `pydantic-settings`). This gives free `.env` loading, type coercion, and per-field env-var binding. The app MUST run with **zero env vars set** — every field has a default matching `main.py`.

**Every env var, its default, and how it's read:**

| Field (env var)      | Type  | Default                                       | Source / meaning |
|----------------------|-------|-----------------------------------------------|------------------|
| `WHISPER_MODEL`      | str   | `ivrit-ai/whisper-large-v3-turbo-ct2`         | `main.py` `model_path` |
| `DEVICE`             | str   | `cpu`                                          | `main.py` `device_str` |
| `COMPUTE_TYPE`       | str   | `int8`                                         | `main.py` `compute_type` |
| `LANGUAGE`           | str   | `he`                                           | `main.py` `transcribe(language="he")` |
| `DIARIZATION_CONFIG` | str   | `models/pyannote-diarization/config.yaml`      | `main.py` local config; **resolved to absolute** (see below) |
| `MIN_SPEAKERS`       | int   | `2`                                            | `main.py` `min_speakers=2` |
| `BATCH_SIZE`         | int   | `4`                                            | `main.py` `batch_size=4` |
| `MAX_UPLOAD_BYTES`   | int   | `26214400`  (25 MiB)                           | upload guard (§4) |
| `HOST`               | str   | `0.0.0.0`                                      | uvicorn bind host |
| `PORT`               | int   | `8000`                                         | uvicorn bind port |
| `HF_HUB_OFFLINE`     | str   | `1`                                            | offline flag; exported to `os.environ` at import (see below) |

Note: `BATCH_SIZE` is added beyond the plan's enumerated list because `main.py` uses `batch_size=4` and the plan's own guide decision ("model name, device, compute type, language, ... ") intends ALL tunables to be env-driven; @backend passes it to `model.transcribe(...)`. The plan's T2 list omitted it but T1 confirms the value — including it is consistent, not contradictory.

**`Settings` shape (the spec @backend implements):**

```python
# app/config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = parent of the `app/` package dir (this file is app/config.py)
REPO_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    WHISPER_MODEL: str = "ivrit-ai/whisper-large-v3-turbo-ct2"
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"
    LANGUAGE: str = "he"
    DIARIZATION_CONFIG: str = "models/pyannote-diarization/config.yaml"
    MIN_SPEAKERS: int = 2
    BATCH_SIZE: int = 4
    MAX_UPLOAD_BYTES: int = 26_214_400  # 25 MiB
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    HF_HUB_OFFLINE: str = "1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def diarization_config_path(self) -> Path:
        """Absolute path to the diarization config.

        Absolute env value is used as-is; a relative value is resolved
        against REPO_ROOT (NOT the process CWD) so the server works
        regardless of where uvicorn is launched from.
        """
        p = Path(self.DIARIZATION_CONFIG)
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()

settings = Settings()

# Export offline flag BEFORE any whisperx/HF import constructs a pipeline (T1 req).
os.environ["HF_HUB_OFFLINE"] = settings.HF_HUB_OFFLINE
```

**Absolute-path resolution (the brittle-CWD fix from T1):** `DIARIZATION_CONFIG` defaults to the repo-relative string but is ALWAYS consumed through the `diarization_config_path` property, which resolves relative values against `REPO_ROOT = Path(__file__).resolve().parent.parent` (the repo root, since this file lives at `<root>/app/config.py`) — **not** the process CWD. `transcription.py` MUST pass `str(settings.diarization_config_path)` to `DiarizationPipeline(model_name=...)`. An operator may still override with an absolute path and it is honored verbatim.

**HF_HUB_OFFLINE side-effect:** set in `config.py` at module import (last lines above). Because `transcription.py` imports `config` and `main.py` imports both, by the time any pipeline is constructed the env var is already `"1"` — satisfying T1's "must be set BEFORE pipeline construction." Keeping it as a `str` (`"1"`, not int/bool) matches what `os.environ` requires and what HF reads.

**`.env.example` (created by @backend in T4):** list every row of the table above as `KEY=default`, so operators see the full surface. Example:
```
WHISPER_MODEL=ivrit-ai/whisper-large-v3-turbo-ct2
DEVICE=cpu
COMPUTE_TYPE=int8
LANGUAGE=he
DIARIZATION_CONFIG=models/pyannote-diarization/config.yaml
MIN_SPEAKERS=2
BATCH_SIZE=4
MAX_UPLOAD_BYTES=26214400
HOST=0.0.0.0
PORT=8000
HF_HUB_OFFLINE=1
```

**Zero-env-vars guarantee:** every field has a default; `Settings()` with no env and no `.env` file yields the `main.py` configuration exactly. T8 verifies both "runs with zero env vars" and "one override works" (e.g. `PORT=9000` → uvicorn binds 9000); `main.py`/run command should pass `host=settings.HOST, port=settings.PORT` to uvicorn so the `PORT` override is observable.

---

### Spec summary for @backend (T4 checklist)

1. Create `app/__init__.py` (empty), `app/config.py`, `app/schemas.py`, `app/transcription.py`, `app/main.py`.
2. `config.py`: `Settings(BaseSettings)` with the 11 fields above + `BATCH_SIZE`; module-level `settings`; `REPO_ROOT`; `diarization_config_path` property; `os.environ["HF_HUB_OFFLINE"]` export. No model loading.
3. `schemas.py`: `Segment{speaker,text,start,end}`, `TranscriptionResponse{segments, language?, num_speakers?}`.
4. `transcription.py`: `TranscriptionPipeline(settings)` with `load()` (whisper + diarization, once) and `transcribe(path, min_speakers=settings.MIN_SPEAKERS)` returning `(segments_list, language, num_speakers)`; `"UNKNOWN"` fallback; pass `str(settings.diarization_config_path)`, `batch_size=settings.BATCH_SIZE`, `language=settings.LANGUAGE`.
5. `main.py`: `lifespan` loads once → `app.state.pipeline`; `POST /transcribe` with size guard, temp-file `finally`-delete, 400/500 discipline.
6. `python -c "import app.main"` must succeed with no network/model load. Provide `.env.example`.

### Files touched
- `sprints/2026-05-31_fastapi-audio-transcribe-diarization/plan.md` — T2 status pending → done.
- `sprints/2026-05-31_fastapi-audio-transcribe-diarization/work-logs/architect.md` — this entry.

No source files created; this is the design spec @backend implements in T4.

### Blockers
None.
