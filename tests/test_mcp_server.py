"""Tests for the FastMCP `transcribe` tool (mcp_code/server.py).

All HTTP is mocked over `requests.post` in the server module — no live FastAPI
server is started and no ML model is loaded. The `@mcp.tool()` decorator returns
the underlying plain function, so we import and call `transcribe` directly.
"""
from unittest.mock import MagicMock

import pytest
import requests

from mcp_code import server
from mcp_code.server import transcribe

# Representative payload mirroring the FastAPI /transcribe contract
# ({segments:[{speaker,text,start,end}], language, num_speakers}).
SAMPLE_RESULT = {
    "segments": [
        {"speaker": "SPEAKER_00", "text": "שלום", "start": 0.0, "end": 1.0}
    ],
    "language": "he",
    "num_speakers": 1,
}


def _make_audio_file(tmp_path):
    """Create a small dummy audio file and return its path as a str."""
    audio = tmp_path / "sample.m4a"
    audio.write_bytes(b"fake audio bytes")
    return str(audio)


def test_happy_path_returns_api_json_and_posts_file(tmp_path, monkeypatch):
    audio_path = _make_audio_file(tmp_path)

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = SAMPLE_RESULT
    fake_resp.raise_for_status.return_value = None

    mock_post = MagicMock(return_value=fake_resp)
    monkeypatch.setattr(server.requests, "post", mock_post)

    result = transcribe(audio_path)

    # The tool passes the API JSON through unchanged.
    assert result == SAMPLE_RESULT

    # It POSTed exactly once to the /transcribe endpoint with a `file` field.
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    posted_url = call_args[0] if call_args else call_kwargs["url"]
    assert posted_url.endswith("/transcribe")
    assert "files" in call_kwargs
    assert "file" in call_kwargs["files"]


def test_missing_file_raises_and_does_not_call_api(tmp_path, monkeypatch):
    missing_path = str(tmp_path / "does_not_exist.m4a")

    mock_post = MagicMock()
    monkeypatch.setattr(server.requests, "post", mock_post)

    with pytest.raises(FileNotFoundError):
        transcribe(missing_path)

    # The bad path must short-circuit before any network call.
    mock_post.assert_not_called()


def test_api_error_surfaces_runtime_error_with_status_code(tmp_path, monkeypatch):
    audio_path = _make_audio_file(tmp_path)

    fake_resp = MagicMock()
    fake_resp.status_code = 500
    fake_resp.text = "Internal Server Error"
    fake_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    mock_post = MagicMock(return_value=fake_resp)
    monkeypatch.setattr(server.requests, "post", mock_post)

    with pytest.raises(RuntimeError) as excinfo:
        transcribe(audio_path)

    # Readable error, not a silent None/partial, and includes the status code.
    assert "500" in str(excinfo.value)
