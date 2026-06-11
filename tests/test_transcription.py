"""Tests for the pyannote -> whisperx handoff logic in app.transcription.

The regression these guard against: word-level speaker labels were collapsed to a
single dominant speaker per coarse whisper segment, so a multi-speaker recording
reported only one speaker. `_split_words_by_speaker` must preserve every speaker
turn.
"""
import types

import pandas as pd

import app.transcription as transcription
from app.config import Settings
from app.transcription import (
    DEFAULT_SPEAKER,
    TranscriptionPipeline,
    _split_words_by_speaker,
)


def _w(word, start, end, speaker):
    return {"word": word, "start": start, "end": end, "speaker": speaker}


def test_alternating_speakers_split_into_turns():
    words = [
        _w(" שלום", 0.0, 0.5, "SPEAKER_00"),
        _w(" אוריה", 0.5, 1.0, "SPEAKER_00"),
        _w(" בסדר", 1.6, 2.0, "SPEAKER_01"),
        _w(" גמור", 2.0, 2.3, "SPEAKER_01"),
        _w(" מה", 2.4, 2.6, "SPEAKER_00"),
    ]
    segs = _split_words_by_speaker(words)
    assert [s["speaker"] for s in segs] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_00"]
    assert segs[0]["text"] == "שלום אוריה"
    assert segs[0]["start"] == 0.0 and segs[0]["end"] == 1.0
    assert segs[1]["text"] == "בסדר גמור"
    assert segs[2]["text"] == "מה"


def test_single_speaker_is_one_segment():
    words = [
        _w(" א", 0.0, 0.5, "SPEAKER_00"),
        _w(" ב", 0.5, 1.0, "SPEAKER_00"),
    ]
    segs = _split_words_by_speaker(words)
    assert len(segs) == 1
    assert segs[0]["speaker"] == "SPEAKER_00"


def test_words_without_speaker_fall_back_to_default():
    words = [_w(" א", 0.0, 0.5, None), _w(" ב", 0.5, 1.0, None)]
    segs = _split_words_by_speaker(words)
    assert len(segs) == 1
    assert segs[0]["speaker"] == DEFAULT_SPEAKER


def test_empty_words_returns_empty():
    assert _split_words_by_speaker([]) == []


# --- speaker-hint resolution -------------------------------------------------

class _FWWord:
    def __init__(self, word, start, end):
        self.word, self.start, self.end, self.probability = word, start, end, 0.9


class _FWSegment:
    def __init__(self, start, end, text, words):
        self.start, self.end, self.text, self.words = start, end, text, words


def _stub_pipeline(monkeypatch, settings, capture):
    """Build a TranscriptionPipeline with the model/diarizer/audio stubbed out."""
    monkeypatch.setattr(transcription.whisperx, "load_audio", lambda path: [0.0])

    def fake_transcribe(audio, language=None, word_timestamps=None):
        seg = _FWSegment(0.0, 1.0, "שלום", [_FWWord(" שלום", 0.0, 1.0)])
        return [seg], types.SimpleNamespace(language="he")

    def fake_diarize(audio, **kwargs):
        capture.update(kwargs)
        return pd.DataFrame(
            {"start": [0.0], "end": [1.0], "speaker": ["SPEAKER_00"]}
        )

    pipe = TranscriptionPipeline(settings)
    pipe._model = types.SimpleNamespace(model=types.SimpleNamespace(transcribe=fake_transcribe))
    pipe._diarize_pipeline = fake_diarize
    return pipe


def test_num_speakers_setting_reaches_diarizer(monkeypatch):
    capture = {}
    settings = Settings(_env_file=None, NUM_SPEAKERS=3)
    pipe = _stub_pipeline(monkeypatch, settings, capture)
    pipe.transcribe("x.m4a")
    assert capture["num_speakers"] == 3
    # An exact count is in play, so no min_speakers floor is forced.
    assert capture["min_speakers"] is None


def test_per_request_overrides_setting(monkeypatch):
    capture = {}
    settings = Settings(_env_file=None, NUM_SPEAKERS=3)
    pipe = _stub_pipeline(monkeypatch, settings, capture)
    pipe.transcribe("x.m4a", num_speakers=4)
    assert capture["num_speakers"] == 4


def test_min_speakers_floor_when_no_exact_count(monkeypatch):
    capture = {}
    settings = Settings(_env_file=None, MIN_SPEAKERS=2)  # NUM_SPEAKERS unset
    pipe = _stub_pipeline(monkeypatch, settings, capture)
    pipe.transcribe("x.m4a")
    assert capture["num_speakers"] is None
    assert capture["min_speakers"] == 2
