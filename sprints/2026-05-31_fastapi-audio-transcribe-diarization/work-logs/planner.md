# Work Log — @planner

## 2026-05-31T19:30 — Sprint planning (FastAPI audio transcribe + diarization)

**Task:** Decompose the sprint goal into an executable `plan.md`.

**What I read:** `CLAUDE.md`, `.claude/team.md`, `sprints/.active`, `resource/` listing, `resource/main.py` (key reference), `resource/README.md`, `models/pyannote-diarization/` tree, `pyproject.toml`.

**Key facts driving the plan:**
- `main.py` pipeline = whisperx `ivrit-ai/whisper-large-v3-turbo-ct2` (CPU, int8, language="he") → local `DiarizationPipeline` from `models/pyannote-diarization/config.yaml` → `assign_word_speakers` → per-segment `[speaker] text`.
- Offline is mandatory (`HF_HUB_OFFLINE=1`, local diarization config). Must be preserved.
- `whisperx.load_audio` needs a file path → uploaded bytes must go to a temp file.
- Model loading is expensive → load once at FastAPI startup (lifespan), store on `app.state`.
- Sample file `resource/audio smaples/audio_sample_1min.m4a` (note typo "smaples" + space → quote paths).

**Decomposition (8 tasks):**
- T1 @researcher — verify main.py runtime contract + segment JSON schema (the contract for T4/T6).
- T2 @architect — module layout + response schema + startup-load + temp-file strategy.
- T3 @architect — recommend audio-send mechanism (multipart/form-data, justified) [goal requirement (a)].
- T4 @backend — implement app (config/transcription/schemas/main, lifespan load, POST /transcribe).
- T5 @devops — add deps (fastapi, uvicorn, python-multipart, requests) + run command.
- T6 @backend — Python REST client example calling endpoint with sample audio [goal requirement (b)].
- T7 @documenter — README: setup/run/contract/recommendation/client.
- T8 @qa — end-to-end validation gate (with documented mock fallback if CPU run infeasible).

**Assignments:** all nicknames validated against `.claude/team.md` (@researcher, @architect, @backend, @devops, @documenter, @qa). No @frontend/@ml/@security tasks — no UI, model code is reuse not new ML, and security concern (SSRF via URL) is folded into T3's recommendation rather than a standalone audit this sprint.

**Open questions for the guide:**
1. Should T8 attempt a real CPU transcription run (slow, requires the whisper model to be downloadable/cached), or is a mocked-pipeline validation acceptable for this sprint? Plan allows either with explicit documentation.
2. Confirm there are no auth/rate-limit/file-size requirements for the endpoint this sprint (none assumed).
