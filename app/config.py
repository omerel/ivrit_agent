"""Env-driven configuration for the transcription service.

All tunables are read from environment variables (optionally a `.env` file) with
defaults that match `resource/main.py` exactly, so the app runs with zero env
vars set. Importing this module performs no network access and loads no models;
it only sets the `HF_HUB_OFFLINE` flag on `os.environ` so any later whisperx /
Hugging Face pipeline construction runs offline.
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = parent of the `app/` package dir (this file is app/config.py).
REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    WHISPER_MODEL: str = "ivrit-ai/whisper-large-v3-turbo-ct2"
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"
    LANGUAGE: str = "he"
    DIARIZATION_CONFIG: str = "models/pyannote-diarization/config.yaml"
    # Speaker-count hints for diarization. MIN_SPEAKERS is a floor used when the
    # exact count is unknown; NUM_SPEAKERS pins the count exactly (set it when you
    # know how many speakers a recording has — similar-sounding voices otherwise
    # cluster into fewer speakers than are present); MAX_SPEAKERS caps the count.
    # A per-request form field overrides any of these.
    MIN_SPEAKERS: int = 2
    MAX_SPEAKERS: int | None = None
    NUM_SPEAKERS: int | None = None
    BATCH_SIZE: int = 4
    MAX_UPLOAD_BYTES: int = 26_214_400  # 25 MiB
    # Chat-completion backend for /summarize. Leave CHAT_API_URL empty to use a
    # built-in dummy responder (no network); set it to an OpenAI-compatible
    # /chat/completions URL (+ CHAT_API_KEY, CHAT_MODEL) to use a real model.
    CHAT_API_URL: str = ""
    CHAT_API_KEY: str = ""
    CHAT_MODEL: str = "gpt-4o-mini"
    CHAT_TIMEOUT: float = 30.0
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    HF_HUB_OFFLINE: str = "1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def diarization_config_path(self) -> Path:
        """Absolute path to the diarization config.

        An absolute env value is used as-is; a relative value is resolved
        against ``REPO_ROOT`` (NOT the process CWD) so the server works
        regardless of where uvicorn is launched from.
        """
        p = Path(self.DIARIZATION_CONFIG)
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()


settings = Settings()

# Export the offline flag BEFORE any whisperx / Hugging Face pipeline is built.
os.environ["HF_HUB_OFFLINE"] = settings.HF_HUB_OFFLINE
