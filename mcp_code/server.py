"""FastMCP server exposing a `transcribe` tool that wraps the FastAPI

`/transcribe` endpoint built in the previous sprint. The tool takes a local
audio file path, POSTs the file as ``multipart/form-data`` (field name
``file``) to ``{TRANSCRIBE_API_URL}/transcribe``, and returns the API's JSON
result unchanged.

This module does NOT load any ML model and performs NO network access at
import time — it only forwards HTTP when the tool is invoked.
"""
import os
from pathlib import Path

import requests
from fastmcp import FastMCP

# Default base URL of the FastAPI transcription service (FastAPI defaults to
# host 0.0.0.0, port 8000). Overridable per call via the TRANSCRIBE_API_URL
# env var (read inside the tool so tests can monkeypatch it).
DEFAULT_API_URL = "http://localhost:8000"

# CPU transcription of even ~1 minute of audio is slow; give generous headroom
# (mirrors client_example.py's 600 s timeout). Fixed constant, not env-driven.
REQUEST_TIMEOUT = 600  # seconds

mcp = FastMCP("ivrit-transcribe")


@mcp.tool()
def transcribe(audio_path: str) -> dict:
    """Transcribe a local audio file into diarized, speaker-labeled text.

    Use this tool whenever the user asks to transcribe / get a transcript of an
    audio file that exists on the local filesystem, in EITHER English or Hebrew.
    English trigger examples: "transcribe this audio file", "get a transcript of
    /path/to/recording.m4a", "what is said in this recording".
    Hebrew trigger examples: "תמלל את קובץ האודיו", "תמלל את ההקלטה הזו",
    "מה נאמר בקובץ הקול הזה", "תן לי תמלול של קובץ השמע".

    Args:
        audio_path: Absolute or relative path to a local audio file
            (e.g. .m4a, .wav, .mp3) on this machine.

    Returns:
        A dict from the transcription API, passed through unchanged:
        {
            "segments": [{"speaker": str, "text": str,
                          "start": float, "end": float}, ...],
            "language": str | null,
            "num_speakers": int | null
        }

    Raises:
        FileNotFoundError: if audio_path does not point to an existing file
            (the API is NOT called in this case).
        RuntimeError: if the transcription API returns a non-2xx status
            (the HTTP status code is included in the message) or the request
            otherwise fails.
    """
    # Validate FIRST — do not touch the network for a bad path.
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Resolve the base URL from the live environment at call time so tests can
    # override it via monkeypatch.
    base_url = os.environ.get("TRANSCRIBE_API_URL", DEFAULT_API_URL).rstrip("/")
    url = f"{base_url}/transcribe"

    try:
        with path.open("rb") as fileobj:
            files = {"file": (path.name, fileobj, "audio/m4a")}
            resp = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Transcription API returned HTTP {resp.status_code} for {url}: "
            f"{resp.text[:500]}"
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Transcription request to {url} failed: {exc}") from exc

    return resp.json()


if __name__ == "__main__":
    mcp.run()
