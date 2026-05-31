"""Example REST client for the ivrit_agent transcription service.

This script POSTs an audio file to the ``/transcribe`` endpoint as
``multipart/form-data`` and prints the diarized transcription.

PREREQUISITE: the server must already be running. Start it (from the repo
root) with the T5 run command::

    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

Then run this client (defaults to the bundled 1-minute sample)::

    uv run python client_example.py
    uv run python client_example.py "resource/audio smaples/audio_sample_1min.m4a"
    uv run python client_example.py --url http://localhost:8000

The endpoint contract (see app/main.py):

    POST {url}/transcribe
        multipart field name: "file"
        response JSON: {
            "segments": [{"speaker": str, "text": str,
                          "start": float, "end": float}, ...],
            "language": str | null,
            "num_speakers": int | null
        }
    GET {url}/health -> {"status": "ok"}
"""
import argparse
import json
import sys
from pathlib import Path

import requests

# Exact literal: the resource folder name has a space AND the "smaples" typo.
# Keep this as a plain string (no shell escaping) — requests/Path handle it.
DEFAULT_AUDIO = "resource/audio smaples/audio_sample_1min.m4a"
DEFAULT_URL = "http://localhost:8000"

# CPU transcription of ~1 minute of audio is slow; give it lots of headroom.
REQUEST_TIMEOUT = 600  # seconds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="POST an audio file to the ivrit_agent /transcribe endpoint.",
    )
    parser.add_argument(
        "audio",
        nargs="?",
        default=DEFAULT_AUDIO,
        help=f"Path to the audio file to transcribe (default: {DEFAULT_AUDIO!r}).",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Base URL of the transcription server (default: {DEFAULT_URL}).",
    )
    return parser


def format_segments(segments: list[dict]) -> list[str]:
    """Render segments as ``[speaker] text`` lines, mirroring main.py output."""
    return [
        f"[{seg.get('speaker', 'UNKNOWN')}] {seg.get('text', '')}"
        for seg in segments
    ]


def check_health(base_url: str) -> bool:
    """Best-effort health probe. Returns True if the server answers OK."""
    try:
        resp = requests.get(f"{base_url}/health", timeout=10)
        resp.raise_for_status()
        return resp.json().get("status") == "ok"
    except requests.RequestException:
        return False


def transcribe(base_url: str, audio_path: Path) -> dict:
    """POST the audio file and return the parsed JSON response."""
    with audio_path.open("rb") as fileobj:
        files = {"file": (audio_path.name, fileobj, "audio/m4a")}
        resp = requests.post(
            f"{base_url}/transcribe",
            files=files,
            timeout=REQUEST_TIMEOUT,
        )
    resp.raise_for_status()
    return resp.json()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_url = args.url.rstrip("/")
    audio_path = Path(args.audio)

    if not audio_path.is_file():
        print(f"Audio file not found: {audio_path}", file=sys.stderr)
        return 2

    if not check_health(base_url):
        print(
            f"Server at {base_url} is not responding on /health.\n"
            "Start it first with:\n"
            "    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000",
            file=sys.stderr,
        )
        return 1

    print(f"Uploading {audio_path} to {base_url}/transcribe ...")
    try:
        result = transcribe(base_url, audio_path)
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print("\n--- Transcription ---")
    for line in format_segments(result.get("segments", [])):
        print(line)

    print("\n--- Raw JSON ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
