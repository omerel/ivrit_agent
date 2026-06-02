# Quick Fix: Isolate config defaults test from local .env file
**By:** @backend
**Date:** 2026-06-02
**Commit:** 4c14f44

## Change
`tests/test_config.py::test_defaults_match_main_py` is meant to verify the code
defaults in `app/config.py`, independent of any local environment. It
monkeypatched `delenv` for the relevant env vars, but pydantic-settings still
reads the repo's local `.env` file, where `WHISPER_MODEL` is overridden to a
local model snapshot path. That made the `WHISPER_MODEL` default assertion fail.

Fixed by constructing the test's `Settings` with `_env_file=None`
(`cfg.Settings(_env_file=None)`), which tells pydantic-settings to skip
env-file loading so the test asserts the true code defaults only. No change to
`app/config.py` and no change to `.env`. The sibling tests were left untouched:
they either intentionally exercise env/`.env` behavior or assert path-resolution
logic unaffected by the `.env` override.

## Result
Ran the full suite with the project venv:
`.venv/bin/python -m pytest -v` → `59 passed, 2 warnings in 4.82s`.
The previously failing `test_defaults_match_main_py` now passes and the suite is
fully green.
