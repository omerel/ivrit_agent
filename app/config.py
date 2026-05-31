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

        An absolute env value is used as-is; a relative value is resolved
        against ``REPO_ROOT`` (NOT the process CWD) so the server works
        regardless of where uvicorn is launched from.
        """
        p = Path(self.DIARIZATION_CONFIG)
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()


settings = Settings()

# Export the offline flag BEFORE any whisperx / Hugging Face pipeline is built.
os.environ["HF_HUB_OFFLINE"] = settings.HF_HUB_OFFLINE
