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
from whisperx.diarize import DiarizationPipeline, assign_word_speakers

from app.config import Settings, settings as default_settings

logger = logging.getLogger("ivrit_agent")

DEFAULT_SPEAKER = "UNKNOWN"


def _split_words_by_speaker(words: list[dict]) -> list[dict]:
    """Group consecutive same-speaker words into ``{speaker, text, start, end}`` turns.

    ``assign_word_speakers`` labels each *word* with a speaker, but a coarse whisper
    segment can span several speakers. Splitting the word stream wherever the speaker
    changes turns a single multi-speaker segment into one segment per speaker turn —
    without this, only the dominant speaker of each whisper segment survives and a
    multi-speaker recording collapses to one speaker.
    """
    turns: list[dict] = []
    cur: dict | None = None
    for w in words:
        speaker = w.get("speaker") or DEFAULT_SPEAKER
        text = w.get("word", "")
        if cur is not None and cur["speaker"] == speaker:
            cur["text"] += text
            cur["end"] = w.get("end", cur["end"])
        else:
            if cur is not None:
                cur["text"] = cur["text"].strip()
                turns.append(cur)
            cur = {
                "speaker": speaker,
                "text": text,
                "start": w.get("start"),
                "end": w.get("end", w.get("start")),
            }
    if cur is not None:
        cur["text"] = cur["text"].strip()
        turns.append(cur)
    return turns


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

    def transcribe(
        self,
        audio_path: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        num_speakers: int | None = None,
    ):
        """Transcribe + diarize ``audio_path``.

        ``min_speakers`` / ``max_speakers`` bound the diarization clustering and
        ``num_speakers`` pins it exactly — pass these when the speaker count is
        known, since similar-sounding voices can otherwise be merged into fewer
        clusters than are really present. Returns ``(segments, language,
        num_speakers)`` where ``segments`` is a list of
        ``{speaker, text, start, end}`` dicts.
        """
        if self._model is None or self._diarize_pipeline is None:
            raise RuntimeError("Pipeline not loaded; call load() first.")
        # Per-request args win; otherwise fall back to the configured hints. An
        # exact NUM_SPEAKERS pins the count, so MIN_SPEAKERS only applies as a
        # floor when no exact count is in play.
        if num_speakers is None:
            num_speakers = self.settings.NUM_SPEAKERS
        if max_speakers is None:
            max_speakers = self.settings.MAX_SPEAKERS
        if min_speakers is None and num_speakers is None:
            min_speakers = self.settings.MIN_SPEAKERS

        audio = whisperx.load_audio(audio_path)

        # whisperx's batched transcribe forces ``without_timestamps=True``, so its
        # segments carry NO word-level timing. ``assign_word_speakers`` then can only
        # attach one dominant speaker per coarse segment, collapsing a multi-speaker
        # recording to a single speaker. We instead drive the underlying
        # faster-whisper model directly with ``word_timestamps=True`` so each word
        # gets a timestamp the diarization can be matched against.
        fw_segments, info = self._model.model.transcribe(
            audio,
            language=self.settings.LANGUAGE,
            word_timestamps=True,
        )
        whisper_segments = []
        for seg in fw_segments:
            words = [
                {
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "score": w.probability,
                }
                for w in (seg.words or [])
                if w.start is not None
            ]
            whisper_segments.append(
                {"start": seg.start, "end": seg.end, "text": seg.text, "words": words}
            )

        result = {"segments": whisper_segments, "language": info.language}
        diarize_segments = self._diarize_pipeline(
            audio,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            num_speakers=num_speakers,
        )
        # fill_nearest=True labels words that fall in diarization gaps with the
        # nearest speaker instead of leaving them UNKNOWN.
        final_result = assign_word_speakers(
            diarize_segments, result, fill_nearest=True
        )

        # Re-segment by speaker. Words within one whisper segment can belong to
        # different speakers, so split each segment on speaker change; a segment
        # with no word timing falls back to its segment-level speaker label.
        segments: list[dict] = []
        for seg in final_result["segments"]:
            seg_words = seg.get("words") or []
            if seg_words:
                segments.extend(_split_words_by_speaker(seg_words))
            else:
                segments.append(
                    {
                        "speaker": seg.get("speaker", DEFAULT_SPEAKER),
                        "text": seg["text"].strip(),
                        "start": seg["start"],
                        "end": seg["end"],
                    }
                )

        language = final_result.get("language") or self.settings.LANGUAGE
        real_speakers = {
            s["speaker"] for s in segments if s["speaker"] != DEFAULT_SPEAKER
        }
        num_speakers = len(real_speakers) if real_speakers else None
        return segments, language, num_speakers
