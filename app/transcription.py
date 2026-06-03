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


def _allowlist_pyannote_globals() -> None:
    """Allowlist the globals the local pyannote VAD checkpoint needs to deserialize.

    Under PyTorch >= 2.6 ``torch.load`` defaults to ``weights_only=True``, which
    refuses to unpickle anything not on its safe-globals list. The local pyannote
    diarization/VAD checkpoints we ship are trusted, but they reference omegaconf
    container types (and a few builtins/typing objects), so loading them raises:

        WeightsUnpickler error: Unsupported global: GLOBAL
        omegaconf.listconfig.ListConfig was not an allowed global by default.

    Rather than the blunt ``weights_only=False`` (which disables the safety check
    for *all* loads), we explicitly allowlist only the symbols these trusted
    checkpoints need. Each import is guarded so a symbol that moved or was removed
    across omegaconf versions cannot break startup — we add whatever resolves.
    """
    add_safe_globals = getattr(torch.serialization, "add_safe_globals", None)
    if add_safe_globals is None:
        # Older torch (<2.6) has no allowlist mechanism and no weights_only default.
        return

    safe: list = []

    # omegaconf container types referenced by pyannote checkpoints.
    omegaconf_globals = [
        ("omegaconf.listconfig", "ListConfig"),
        ("omegaconf.dictconfig", "DictConfig"),
        ("omegaconf.base", "ContainerMetadata"),
        ("omegaconf.base", "Metadata"),
        ("omegaconf.nodes", "AnyNode"),
    ]
    for module_name, attr in omegaconf_globals:
        try:
            module = __import__(module_name, fromlist=[attr])
            safe.append(getattr(module, attr))
        except (ImportError, AttributeError):
            continue

    # Builtins / typing objects pyannote checkpoints frequently reference.
    try:
        import collections

        safe.append(collections.defaultdict)
    except (ImportError, AttributeError):
        pass
    try:
        import typing

        safe.append(typing.Any)
    except (ImportError, AttributeError):
        pass
    safe.extend([dict, list, int])

    if safe:
        add_safe_globals(safe)


# Run once at import, before any model load, so the pyannote VAD checkpoint
# deserializes under torch>=2.6 weights_only=True.
_allowlist_pyannote_globals()


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
