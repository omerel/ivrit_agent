"""Tests for app.main endpoint behavior, using a fake pipeline (no model load)."""
import glob
import tempfile

import pytest
from fastapi.testclient import TestClient

import app.main as main


class FakePipeline:
    """Stand-in for TranscriptionPipeline — records the path it was given."""

    def __init__(self, result=None, raises=None):
        self._result = result if result is not None else ([], None, None)
        self._raises = raises
        self.seen_paths = []

    def transcribe(self, audio_path, min_speakers=2):
        self.seen_paths.append(audio_path)
        if self._raises:
            raise self._raises
        return self._result


def make_client(pipeline):
    """Build a TestClient without triggering the real lifespan/model load."""
    client = TestClient(main.app)
    client.app.state.pipeline = pipeline
    return client


def test_health():
    client = TestClient(main.app)
    client.app.state.pipeline = FakePipeline()
    assert client.get("/health").json() == {"status": "ok"}


def test_transcribe_success_returns_segments():
    segments = [
        {"speaker": "SPEAKER_00", "text": "שלום", "start": 0.0, "end": 1.2},
        {"speaker": "SPEAKER_01", "text": "תודה", "start": 1.2, "end": 2.4},
    ]
    pipe = FakePipeline(result=(segments, "he", 2))
    client = make_client(pipe)
    resp = client.post("/transcribe", files={"file": ("a.m4a", b"abc", "audio/m4a")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "he"
    assert body["num_speakers"] == 2
    assert body["segments"][0] == {
        "speaker": "SPEAKER_00", "text": "שלום", "start": 0.0, "end": 1.2,
    }


def test_transcribe_empty_upload_400():
    client = make_client(FakePipeline())
    resp = client.post("/transcribe", files={"file": ("a.m4a", b"", "audio/m4a")})
    assert resp.status_code == 400


def test_transcribe_oversized_upload_rejected():
    pipe = FakePipeline()
    client = make_client(pipe)
    main.app.state.pipeline = pipe
    big = b"x" * (main.settings.MAX_UPLOAD_BYTES + 1)
    resp = client.post("/transcribe", files={"file": ("a.m4a", big, "audio/m4a")})
    assert resp.status_code in (400, 413)
    # Oversized upload must never reach the pipeline.
    assert pipe.seen_paths == []


def test_transcribe_pipeline_error_returns_500():
    pipe = FakePipeline(raises=RuntimeError("boom"))
    client = make_client(pipe)
    resp = client.post("/transcribe", files={"file": ("a.m4a", b"abc", "audio/m4a")})
    assert resp.status_code == 500
    # Clean message, no internal stack/text leaked.
    assert "boom" not in resp.text


def test_transcribe_deletes_temp_file(monkeypatch):
    before = set(glob.glob(tempfile.gettempdir() + "/*"))
    pipe = FakePipeline(result=([], "he", None))
    client = make_client(pipe)
    client.post("/transcribe", files={"file": ("a.m4a", b"abc", "audio/m4a")})
    # The path handed to the pipeline must no longer exist after the request.
    import os
    assert pipe.seen_paths, "pipeline was never called"
    for p in pipe.seen_paths:
        assert not os.path.exists(p), f"temp file leaked: {p}"


def test_require_ffmpeg_passes_when_present(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    main._require_ffmpeg()  # must not raise


def test_require_ffmpeg_raises_when_missing(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError) as exc:
        main._require_ffmpeg()
    # Error must name the missing binary and how to install it.
    assert "ffmpeg" in str(exc.value)
    assert "install" in str(exc.value).lower()


def test_import_does_not_load_models():
    # Importing app.main must not have constructed a real pipeline on app.state.
    import importlib
    mod = importlib.import_module("app.main")
    # app.state.pipeline is only set inside lifespan, never at import.
    assert not hasattr(mod.app.state, "pipeline") or mod.app.state.pipeline is None \
        or isinstance(getattr(mod.app.state, "pipeline", None), FakePipeline)
