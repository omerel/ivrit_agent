"""Render a transcribe-tool JSON dict into an RTL Hebrew Markdown transcript.

Implements the architect's §4 contract (DESIGN NOTE, sprint
2026-05-31_hebrew-transcript-vocab-skill):

- ``to_mmss(seconds)``  -> ``mm:ss`` (locked format; mm may exceed 59).
- ``output_path(audio_path, run_timestamp)`` -> the deterministic output Path
  ``output/hebrew-transcript-review/<slug(stem)>_<run_timestamp>_transcript.md``.
- ``render(result, audio_path, run_timestamp)`` -> writes the RTL table file and
  returns the written Path.

The rendered table has EXACTLY the columns ``זמן בדקות | דובר | מלל`` and is
wrapped in ``<div dir="rtl"> … </div>`` (the reliable RTL mechanism for rendered
Markdown — the CLI itself does not render Hebrew RTL, so the .md file is the
deliverable).
"""
import math
import re
from pathlib import Path

# Repo-root output dir for generated run artifacts (git-ignored). Tests
# monkeypatch this attribute to redirect writes into a tmp dir.
_REPO_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_DIR = _REPO_ROOT / "output" / "hebrew-transcript-review"

# Exact, locked table header (architect §4). T9 checks this triple verbatim.
HEADER_ROW = "| זמן בדקות | דובר | מלל |"
SEPARATOR_ROW = "| --- | --- | --- |"


def to_mmss(seconds: float) -> str:
    """Convert seconds to ``mm:ss``.

    Floors to whole seconds. ``m = total // 60``, ``s = total % 60``. No hours
    field — ``mm`` may exceed 59 for long audio (e.g. 3725s -> ``"62:05"``).
    167.0 -> ``"02:47"``, 5.0 -> ``"00:05"``, 0 -> ``"00:00"``.
    """
    total = math.floor(seconds)
    if total < 0:
        total = 0
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


def _slug(stem: str) -> str:
    """Slugify an audio filename stem.

    Lowercase; runs of disallowed chars become a single ``-``. Underscores are
    preserved (architect §1 worked example: ``audio_sample_1min.m4a`` ->
    ``audio_sample_1min``), so the allowed set is ``[a-z0-9_-]``.
    """
    s = stem.lower()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    return s.strip("-")


def output_path(audio_path: str, run_timestamp: str) -> Path:
    """Build the transcript output Path from the audio path and run timestamp.

    ``output/hebrew-transcript-review/<slug(stem)>_<run_timestamp>_transcript.md``.
    """
    stem = Path(audio_path).stem
    name = f"{_slug(stem)}_{run_timestamp}_transcript.md"
    return OUTPUT_DIR / name


def _cell(text: str) -> str:
    """Make a string safe for a Markdown table cell.

    Escapes ``|`` as ``\\|`` and collapses any whitespace/newlines to single
    spaces so a multi-line segment never breaks the table row.
    """
    collapsed = " ".join(str(text).split())
    return collapsed.replace("|", "\\|")


def render(result: dict, audio_path: str, run_timestamp: str) -> Path:
    """Write the RTL transcript Markdown file and return its Path.

    ``result`` is the transcribe tool JSON dict::

        {"segments": [{"speaker": str, "text": str, "start": float, "end": float}, ...],
         "language": str|null, "num_speakers": int|null}

    One row per segment in input (chronological) order. Empty ``segments`` still
    writes a valid file with header rows and zero data rows. Creates the output
    dir if missing.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = output_path(audio_path, run_timestamp)

    basename = Path(audio_path).name
    segments = result.get("segments", []) or []

    lines = [
        f"<!-- transcript for: {basename} · generated {run_timestamp} -->",
        '<div dir="rtl">',
        "",
        HEADER_ROW,
        SEPARATOR_ROW,
    ]
    for seg in segments:
        time = to_mmss(seg.get("start", 0))
        speaker = _cell(seg.get("speaker", ""))
        text = _cell(seg.get("text", ""))
        lines.append(f"| {time} | {speaker} | {text} |")
    lines += ["", "</div>", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
