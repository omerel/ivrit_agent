"""Tests for client_example.py that need no live server.

These cover the parse-able / importable surface: the default audio path
literal (with its space + "smaples" typo), the argparse CLI defaults, and the
[speaker] text formatting helper.
"""
import ast
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_PATH = REPO_ROOT / "client_example.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("client_example", CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_parses():
    ast.parse(CLIENT_PATH.read_text())


def test_default_audio_path_literal():
    mod = _load_module()
    # Exact literal: note the space and the "smaples" typo must be preserved.
    assert mod.DEFAULT_AUDIO == "resource/audio smaples/audio_sample_1min.m4a"


def test_default_url():
    mod = _load_module()
    assert mod.DEFAULT_URL == "http://localhost:8000"


def test_argparser_defaults():
    mod = _load_module()
    parser = mod.build_parser()
    args = parser.parse_args([])
    assert args.audio == mod.DEFAULT_AUDIO
    assert args.url == mod.DEFAULT_URL


def test_argparser_overrides():
    mod = _load_module()
    parser = mod.build_parser()
    args = parser.parse_args(["some/other.m4a", "--url", "http://example.com:9000"])
    assert args.audio == "some/other.m4a"
    assert args.url == "http://example.com:9000"


def test_format_segments():
    mod = _load_module()
    segments = [
        {"speaker": "SPEAKER_00", "text": " shalom", "start": 0.0, "end": 1.0},
        {"text": "no speaker key", "start": 1.0, "end": 2.0},
    ]
    lines = mod.format_segments(segments)
    assert lines == ["[SPEAKER_00]  shalom", "[UNKNOWN] no speaker key"]
