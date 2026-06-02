"""FastAPI app: load models once at startup, transcribe uploaded audio.

The whisper model + diarization pipeline are loaded a single time inside the
``lifespan`` handler and stored on ``app.state.pipeline``. ``POST /transcribe``
accepts a ``multipart/form-data`` file upload (field name ``file``), writes the
bytes to a temp file (whisperx/ffmpeg needs a real path), runs the pipeline, and
returns the diarized transcription as JSON.
"""
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import REPO_ROOT, settings
from app.schemas import Segment, TranscriptionResponse
from app.transcription import TranscriptionPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ivrit_agent")


def _resolve_local_model(model_ref: str) -> str:
    """Resolve a local whisper model directory.

    A relative ``WHISPER_MODEL`` that points at an existing directory is
    resolved against ``REPO_ROOT`` (not the process CWD) so the model loads
    from disk regardless of where uvicorn is launched. Anything that is not a
    local directory (e.g. a Hugging Face repo id) is returned unchanged.
    """
    candidate = Path(model_ref)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / model_ref
    if candidate.is_dir():
        return str(candidate.resolve())
    return model_ref


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.WHISPER_MODEL = _resolve_local_model(settings.WHISPER_MODEL)
    logger.info(
        "Loading models (whisper=%s, device=%s)...",
        settings.WHISPER_MODEL,
        settings.DEVICE,
    )
    pipeline = TranscriptionPipeline(settings)
    pipeline.load()  # the single expensive load (logs "Models loaded")
    app.state.pipeline = pipeline
    try:
        yield
    finally:
        app.state.pipeline = None


# Static UI assets live in the app/ package. Resolve package-relative (NOT CWD)
# so the page serves regardless of where uvicorn is launched. StaticFiles
# validates this directory at import time, so app/static/index.html must exist.
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="ivrit_agent transcription", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(request: Request, file: UploadFile):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds MAX_UPLOAD_BYTES ({settings.MAX_UPLOAD_BYTES} bytes).",
        )

    suffix = Path(file.filename or "").suffix  # e.g. ".m4a" — helps ffmpeg sniff format
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()  # close so ffmpeg can read it on all platforms
        segments, language, num_speakers = request.app.state.pipeline.transcribe(tmp.name)
        return TranscriptionResponse(
            segments=[Segment(**s) for s in segments],
            language=language,
            num_speakers=num_speakers,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pipeline / ffmpeg / model failure
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed.") from exc
    finally:
        try:
            os.unlink(tmp.name)  # ALWAYS delete the temp file
        except OSError:
            pass
