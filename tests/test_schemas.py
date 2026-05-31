"""Tests for app.schemas response models."""
from app.schemas import Segment, TranscriptionResponse


def test_segment_fields():
    seg = Segment(speaker="SPEAKER_00", text="שלום", start=0.0, end=1.5)
    assert seg.speaker == "SPEAKER_00"
    assert seg.text == "שלום"
    assert seg.start == 0.0
    assert seg.end == 1.5


def test_transcription_response_optional_defaults():
    resp = TranscriptionResponse(segments=[])
    assert resp.segments == []
    assert resp.language is None
    assert resp.num_speakers is None


def test_transcription_response_full():
    resp = TranscriptionResponse(
        segments=[Segment(speaker="UNKNOWN", text="x", start=0.0, end=1.0)],
        language="he",
        num_speakers=2,
    )
    assert resp.language == "he"
    assert resp.num_speakers == 2
    assert resp.segments[0].speaker == "UNKNOWN"
