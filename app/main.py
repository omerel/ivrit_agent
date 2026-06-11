"""FastAPI app: load models once at startup, transcribe uploaded audio.

The whisper model + diarization pipeline are loaded a single time inside the
``lifespan`` handler and stored on ``app.state.pipeline``. ``POST /transcribe``
accepts a ``multipart/form-data`` file upload (field name ``file``), writes the
bytes to a temp file (whisperx/ffmpeg needs a real path), runs the pipeline, and
returns the diarized transcription as JSON.
"""
import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.chat import ChatCompletionClient, build_transcript_text
from app.config import REPO_ROOT, settings
from app.schemas import (
    Segment,
    SummarizeRequest,
    SummarizeResponse,
    TranscriptionResponse,
)
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


def _require_ffmpeg() -> None:
    """Fail fast at startup if the ``ffmpeg`` binary is not on the PATH.

    whisperx shells out to ``ffmpeg`` to decode audio (``whisperx.load_audio``),
    so a missing binary otherwise surfaces as a cryptic ``FileNotFoundError`` on
    the first ``/transcribe`` request. Checking here turns that into an obvious
    startup failure with install instructions.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. whisperx needs it to decode audio. "
            "Install it, e.g. `sudo apt-get install -y ffmpeg` (Debian/Ubuntu), "
            "`brew install ffmpeg` (macOS), or `conda install -c conda-forge ffmpeg`."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _require_ffmpeg()
    settings.WHISPER_MODEL = _resolve_local_model(settings.WHISPER_MODEL)
    logger.info(
        "Loading models (whisper=%s, device=%s)...",
        settings.WHISPER_MODEL,
        settings.DEVICE,
    )
    pipeline = TranscriptionPipeline(settings)
    pipeline.load()  # the single expensive load (logs "Models loaded")
    app.state.pipeline = pipeline
    app.state.chat = ChatCompletionClient(settings)  # cheap; no model load
    try:
        yield
    finally:
        app.state.pipeline = None
        app.state.chat = None


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
async def transcribe(
    request: Request,
    file: UploadFile,
    min_speakers: int | None = Form(None),
    max_speakers: int | None = Form(None),
    num_speakers: int | None = Form(None),
):
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
        segments, language, detected_speakers = request.app.state.pipeline.transcribe(
            tmp.name,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            num_speakers=num_speakers,
        )
        return TranscriptionResponse(
            segments=[Segment(**s) for s in segments],
            language=language,
            num_speakers=detected_speakers,
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


# Sync def on purpose: the chat client may make a blocking HTTP request, so
# FastAPI runs this in a threadpool instead of blocking the event loop.
@app.post("/summarize", response_model=SummarizeResponse)
def summarize(request: Request, payload: SummarizeRequest):
    instruction = payload.instruction.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Empty instruction.")

    segments = [s.model_dump() for s in payload.transcription.segments]
    transcript_text = build_transcript_text(segments)
    if not transcript_text:
        raise HTTPException(status_code=400, detail="Empty transcription.")

    try:
        answer, model = request.app.state.chat.complete(instruction, transcript_text)
    except Exception as exc:  # chat backend / network failure
        logger.exception("Summarization failed")
        raise HTTPException(status_code=502, detail="Summarization failed.") from exc

    return SummarizeResponse(answer=answer, model=model)
