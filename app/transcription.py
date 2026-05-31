"""Whisper + pyannote diarization pipeline wrapper.

Mirrors ``resource/main.py``: load whisper model + a local diarization pipeline
ONCE (the expensive step), then per request run transcribe -> diarize ->
assign_word_speakers and map the result to plain ``{speaker, text, start, end}``
dicts with an ``"UNKNOWN"`` fallback for segments that got no speaker label.

Model loading happens only in ``load()`` — never at import or ``__init__`` time —
so ``import app.main`` succeeds without downloading the model.
"""
import logging

import torch
import whisperx
from whisperx.diarize import DiarizationPipeline

from app.config import Settings, settings as default_settings

logger = logging.getLogger("ivrit_agent")

DEFAULT_SPEAKER = "UNKNOWN"


class TranscriptionPipeline:
    """Holds the loaded whisper model + diarization pipeline for reuse."""

    def __init__(self, settings: Settings = default_settings):
        self.settings = settings
        self._model = None
        self._diarize_pipeline = None

    def load(self) -> None:
        """Load the whisper model and diarization pipeline exactly once."""
        device = torch.device(self.settings.DEVICE)
        self._model = whisperx.load_model(
            self.settings.WHISPER_MODEL,
            self.settings.DEVICE,
            compute_type=self.settings.COMPUTE_TYPE,
        )
        self._diarize_pipeline = DiarizationPipeline(
            model_name=str(self.settings.diarization_config_path),
            device=device,
        )
        logger.info("Models loaded")

    def transcribe(self, audio_path: str, min_speakers: int | None = None):
        """Transcribe + diarize ``audio_path``.

        Returns ``(segments, language, num_speakers)`` where ``segments`` is a
        list of ``{speaker, text, start, end}`` dicts.
        """
        if self._model is None or self._diarize_pipeline is None:
            raise RuntimeError("Pipeline not loaded; call load() first.")
        if min_speakers is None:
            min_speakers = self.settings.MIN_SPEAKERS

        audio = whisperx.load_audio(audio_path)
        result = self._model.transcribe(
            audio,
            batch_size=self.settings.BATCH_SIZE,
            language=self.settings.LANGUAGE,
        )
        diarize_segments = self._diarize_pipeline(audio, min_speakers=min_speakers)
        final_result = whisperx.assign_word_speakers(diarize_segments, result)

        segments = [
            {
                "speaker": seg.get("speaker", DEFAULT_SPEAKER),
                "text": seg["text"],
                "start": seg["start"],
                "end": seg["end"],
            }
            for seg in final_result["segments"]
        ]

        language = final_result.get("language") or self.settings.LANGUAGE
        real_speakers = {
            s["speaker"] for s in segments if s["speaker"] != DEFAULT_SPEAKER
        }
        num_speakers = len(real_speakers) if real_speakers else None
        return segments, language, num_speakers
