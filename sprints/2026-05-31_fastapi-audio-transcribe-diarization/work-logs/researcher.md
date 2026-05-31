# Work Log — @researcher

## 2026-05-31T19:15:00 — Task T1

**Task:** Confirm and document the exact runtime contract of `resource/main.py` (whisperx call signatures, post-diarization segment schema, local config path resolution, offline/env settings) as the verified contract for downstream FastAPI tasks (T4, T6).

**Attempted:** Read `resource/main.py`; located installed whisperx at
`/Users/omer/Documents/ivrit_agent/.venv/lib/python3.11/site-packages/whisperx`
(via `python -c "import whisperx, os; print(os.path.dirname(whisperx.__file__))"`).
Grepped/read source (NO heavy models run): `__init__.py`, `asr.py`
(`load_model`, `transcribe`), `audio.py` (`load_audio`), `diarize.py`
(`DiarizationPipeline`, `assign_word_speakers`), `schema.py` (segment TypedDicts).
Inspected `models/pyannote-diarization/` tree and `config.yaml`.

### Findings

**1. Exact call signatures (as used by main.py, confirmed against source):**
- `whisperx.load_model(model_path, device_str, compute_type=compute_type)`
  -> `load_model(whisper_arch, device, ..., compute_type="default", ...)`. main.py
  passes device positionally and `compute_type="int8"`. Returns a
  `FasterWhisperPipeline`. Note: `language` is NOT passed at load time in main.py
  (it is passed to `transcribe`), which is valid.
- `model.transcribe(audio, batch_size=4, language="he")`
  -> `transcribe(self, audio, batch_size=None, ..., language=None, ...) -> TranscriptionResult`.
  `audio` may be an ndarray (main.py passes the loaded ndarray) or a path str.
- `whisperx.load_audio(path)` -> `load_audio(file: str, sr: int = 16000) -> np.ndarray`.
  Takes a FILE PATH (uses ffmpeg); returns 16 kHz mono float ndarray. Confirms the
  plan's note that uploaded bytes must be written to a temp file first.
- `DiarizationPipeline(model_name=local_diarization_path, device=device)` then
  called as `diarize_pipeline(audio, min_speakers=2)`.
  -> `__init__(self, model_name=None, token=None, device="cpu", cache_dir=None)`;
  internally `Pipeline.from_pretrained(model_config, token=..., cache_dir=...)`.
  `model_name` may be a local config path (main.py passes
  `./models/pyannote-diarization/config.yaml`). `device` accepts a `torch.device`
  or str. `__call__(audio, num_speakers=None, min_speakers=None, max_speakers=None,
  return_embeddings=False, ...)`. With `return_embeddings=False` (the default,
  used by main.py) it returns a single pandas DataFrame
  (cols: `segment`, `label`, `speaker`, `start`, `end`).
- `whisperx.assign_word_speakers(diarize_segments, result)`
  -> `assign_word_speakers(diarize_df, transcript_result, speaker_embeddings=None,
  fill_nearest=False) -> transcript_result` (mutates segments in place and returns
  the same dict). main.py uses positional `(diarize_df, result)`,
  so `fill_nearest=False`.

**2. CONFIRMED segment schema — the deliverable contract.**
main.py does NOT call `whisperx.align`, so segments are raw `transcribe` output
(`SingleSegment`), NOT aligned segments. Each item in `final_result["segments"]`:
```
{
  "start": float,        # always present (seconds, rounded to 3 decimals)
  "end": float,          # always present (seconds, rounded to 3 decimals)
  "text": str,           # always present
  "avg_logprob": float,  # always present (added by transcribe; ignore downstream)
  "speaker": str         # CONDITIONAL — present ONLY when a diarization segment
                         #   overlaps this segment's [start,end]. With fill_nearest
                         #   =False (main.py's case), non-overlapping segments have
                         #   NO "speaker" key.
}
```
- `final_result` top level: `{"segments": [...], "language": str}` (TranscriptionResult).
- There is NO `words` key on segments in this pipeline (words/`SingleWordSegment`
  only appear after `whisperx.align`, which main.py skips). In `assign_word_speakers`
  the per-word loop is guarded by `if 'words' in seg`, so its absence is harmless.
- **`speaker` may be MISSING — confirmed in source.** `diarize.assign_word_speakers`
  sets `seg['speaker']` only inside `if overlaps:` (or the `fill_nearest` branch).
  main.py's `segment.get('speaker', 'UNKNOWN')` is the correct fallback and MUST be
  mirrored in T4 (map missing speaker -> `"UNKNOWN"` or a configured default).

**3. Local diarization config path.**
main.py uses the RELATIVE path `./models/pyannote-diarization/config.yaml`, resolved
against the process CWD (repo root). The directory exists with: `config.yaml`,
`embedding/`, `plda/`, `segmentation/`, plus `README.md`, `.gitattributes`,
`diarization.gif`, and a `.cache/huggingface/` tree. `config.yaml` references
`$model/segmentation`, `$model/embedding`, `$model/plda` (resolved relative to the
config file's own directory by pyannote), clustering `VBxClustering`, and declares
`pyannote.audio: 4.0.0`. ACTION for T4: the relative path is CWD-dependent and
brittle for a server; resolve `DIARIZATION_CONFIG` to an absolute path from repo root.

**4. Offline / env settings.**
main.py sets `os.environ["HF_HUB_OFFLINE"] = "1"` BEFORE constructing the pipeline.
This must be set at import/startup (before any HF download is attempted). Device is
CPU (`torch.device("cpu")`), `compute_type="int8"`, `language="he"`, `min_speakers=2`,
`batch_size=4`. No HF token is used (offline + local config).

### Discrepancies flagged vs. plan Context
- **`words` key:** Plan T1 acceptance lists segment keys as
  `start, end, text, speaker, words`. In THIS pipeline there is NO `words` key
  (no alignment step). The real keys are `start, end, text, avg_logprob` plus a
  CONDITIONAL `speaker`. Downstream schema (T2/T4) should be
  `{speaker, text, start, end}` and treat `speaker` as defaulted to `"UNKNOWN"`.
- **Audio file:** main.py actually loads
  `resource/audio smaples/chosen.wav 06-46-07-986.wav`, not the
  `audio_sample_1min.m4a` named in the plan. Not a contract issue (the sample for
  T6/T8 is correct per guide decision), just noted.

**Files touched:** created
`sprints/2026-05-31_fastapi-audio-transcribe-diarization/work-logs/researcher.md`.
No source code modified. Updated T1 status in `plan.md` to done.

**Blockers:** None.
