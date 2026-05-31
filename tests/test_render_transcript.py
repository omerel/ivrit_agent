"""Tests for render_transcript.py (T5).

Validates the architect's §4 contract:
- to_mmss: seconds -> mm:ss (locked format)
- output_path: output/hebrew-transcript-review/<slug>_<ts>_transcript.md
- render: writes RTL Hebrew table with exactly the columns
  `זמן בדקות | דובר | מלל`, one row per segment in input order.
"""
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".claude/skills/hebrew-transcript-review/scripts/render_transcript.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("render_transcript", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_transcript = _load_module()


# --- to_mmss ---------------------------------------------------------------

@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "00:00"),
        (0.0, "00:00"),
        (12, "00:12"),
        (5.0, "00:05"),
        (167.0, "02:47"),
        (605.4, "10:05"),
        (3725, "62:05"),  # >59 min: mm can exceed 59, no hours field
    ],
)
def test_to_mmss_conversion(seconds, expected):
    assert render_transcript.to_mmss(seconds) == expected


def test_to_mmss_floors_fractional_seconds():
    assert render_transcript.to_mmss(59.9) == "00:59"


# --- output_path -----------------------------------------------------------

def test_output_path_naming():
    p = render_transcript.output_path("audio_sample_1min.m4a", "20260531-231012")
    assert p.parent.as_posix().endswith("output/hebrew-transcript-review")
    assert p.name == "audio_sample_1min_20260531-231012_transcript.md"


def test_output_path_slugifies_spaces_and_case():
    p = render_transcript.output_path(
        "/some/dir/Audio Smaples Clip.m4a", "20260531-231012"
    )
    assert p.name == "audio-smaples-clip_20260531-231012_transcript.md"


# --- render ----------------------------------------------------------------

SAMPLE = {
    "segments": [
        {"speaker": "SPEAKER_00", "text": "שלום וברוכים הבאים", "start": 0.0, "end": 4.2},
        {"speaker": "SPEAKER_01", "text": "תודה רבה לכם", "start": 12.0, "end": 15.0},
        {"speaker": "SPEAKER_00", "text": "נתחיל בנושא הראשון", "start": 167.0, "end": 170.0},
    ],
    "language": "he",
    "num_speakers": 2,
}


def _render_to_tmp(tmp_path, monkeypatch, result):
    # Redirect the output dir into tmp_path so we never write under the repo.
    monkeypatch.setattr(render_transcript, "OUTPUT_DIR", tmp_path / "out")
    return render_transcript.render(result, "audio_sample_1min.m4a", "20260531-231012")


def test_render_returns_written_path(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, SAMPLE)
    assert isinstance(path, Path)
    assert path.exists()
    assert path.name == "audio_sample_1min_20260531-231012_transcript.md"


def test_render_header_row_is_exact(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, SAMPLE)
    text = path.read_text(encoding="utf-8")
    assert "| זמן בדקות | דובר | מלל |" in text
    assert "| --- | --- | --- |" in text


def test_render_wraps_table_in_rtl_div(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, SAMPLE)
    text = path.read_text(encoding="utf-8")
    assert '<div dir="rtl">' in text
    assert "</div>" in text


def test_render_row_count_equals_segment_count(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, SAMPLE)
    text = path.read_text(encoding="utf-8")
    data_rows = [
        ln
        for ln in text.splitlines()
        if ln.startswith("|")
        and "זמן בדקות" not in ln
        and not ln.replace("|", "").replace("-", "").strip() == ""
    ]
    assert len(data_rows) == len(SAMPLE["segments"])


def test_render_converts_start_seconds_to_mmss(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, SAMPLE)
    text = path.read_text(encoding="utf-8")
    assert "| 00:00 | SPEAKER_00 |" in text
    assert "| 00:12 | SPEAKER_01 |" in text
    assert "| 02:47 | SPEAKER_00 |" in text


def test_render_preserves_input_order(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, SAMPLE)
    text = path.read_text(encoding="utf-8")
    i0 = text.index("שלום וברוכים הבאים")
    i1 = text.index("תודה רבה לכם")
    i2 = text.index("נתחיל בנושא הראשון")
    assert i0 < i1 < i2


def test_render_escapes_pipe_and_collapses_newlines(tmp_path, monkeypatch):
    result = {
        "segments": [
            {"speaker": "SPEAKER_00", "text": "שורה אחת\nשורה שתיים | עם קו", "start": 0.0, "end": 1.0},
        ],
    }
    path = _render_to_tmp(tmp_path, monkeypatch, result)
    text = path.read_text(encoding="utf-8")
    assert "שורה אחת שורה שתיים \\| עם קו" in text
    # The cell must not contain a raw newline that would break the row.
    cell_line = [ln for ln in text.splitlines() if "שורה אחת" in ln][0]
    assert "\n" not in cell_line


def test_render_empty_segments_writes_valid_table(tmp_path, monkeypatch):
    path = _render_to_tmp(tmp_path, monkeypatch, {"segments": []})
    text = path.read_text(encoding="utf-8")
    assert "| זמן בדקות | דובר | מלל |" in text
    assert "| --- | --- | --- |" in text


def test_render_creates_output_dir(tmp_path, monkeypatch):
    out = tmp_path / "out"
    assert not out.exists()
    monkeypatch.setattr(render_transcript, "OUTPUT_DIR", out)
    render_transcript.render(SAMPLE, "audio_sample_1min.m4a", "20260531-231012")
    assert out.exists()
