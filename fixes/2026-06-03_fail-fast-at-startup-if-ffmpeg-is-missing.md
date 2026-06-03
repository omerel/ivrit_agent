# Quick Fix: Fail fast at startup if ffmpeg is missing; document ffmpeg install
**By:** @implementer
**Date:** 2026-06-03
**Commit:** ba3583f72289813753bfa04a3a3872b0c8ecf42a

## Change
Added `_require_ffmpeg()` to `app/main.py` (uses `shutil.which("ffmpeg")` and
raises `RuntimeError` with install instructions when ffmpeg is not on PATH),
and call it at the top of the `lifespan` handler so the app refuses to start
without ffmpeg instead of failing later at transcode time. Added `import shutil`.
Added two tests in `tests/test_main.py`
(`test_require_ffmpeg_passes_when_present`, `test_require_ffmpeg_raises_when_missing`).
Documented ffmpeg installation (apt/brew/conda) in the README Install section.

## Result
`uv run pytest tests/test_main.py -q` → 9 passed, 2 warnings. Both new ffmpeg
tests pass; the missing-ffmpeg case raises a clear `RuntimeError`.
