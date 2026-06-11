"""Pydantic response models for the /transcribe endpoint."""
from pydantic import BaseModel


class Segment(BaseModel):
    speaker: str  # "UNKNOWN" when no diarization segment overlapped this span
    text: str
    start: float  # seconds
    end: float  # seconds


class TranscriptionResponse(BaseModel):
    segments: list[Segment]
    language: str | None = None  # echoed from final_result["language"]
    num_speakers: int | None = None  # distinct speaker labels, excluding "UNKNOWN"


class SummarizeRequest(BaseModel):
    instruction: str  # the user's custom request, e.g. "summarize in bullets"
    transcription: TranscriptionResponse  # the JSON transcript to act on


class SummarizeResponse(BaseModel):
    answer: str
    model: str  # which chat model produced the answer ("dummy" when unconfigured)
