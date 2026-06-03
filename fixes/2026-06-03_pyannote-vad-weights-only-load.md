# Quick Fix: Allowlist omegaconf globals so pyannote VAD checkpoint loads under torch>=2.6
**By:** @implementer
**Date:** 2026-06-03
**Commit:** 0b65c918c51dac242de52b162e5eee4576918f6b

## Change
Under PyTorch >= 2.6, `torch.load` defaults to `weights_only=True`. Loading the
local pyannote VAD checkpoint (via `whisperx.load_model` ->
`whisperx/vads/pyannote.py:load_vad_model` -> `pyannote.../Model.from_pretrained`
-> `torch.load`) then raised:

    _pickle.UnpicklingError: Weights only load failed. ... WeightsUnpickler error:
    Unsupported global: GLOBAL omegaconf.listconfig.ListConfig was not an allowed
    global by default.

Added a module-level `_allowlist_pyannote_globals()` in `app/transcription.py`
that runs once at import (before any model load). It calls
`torch.serialization.add_safe_globals(...)` to allowlist the symbols the trusted,
locally shipped pyannote checkpoints reference:
`omegaconf.listconfig.ListConfig`, `omegaconf.dictconfig.DictConfig`,
`omegaconf.base.ContainerMetadata`, `omegaconf.base.Metadata`,
`omegaconf.nodes.AnyNode`, plus `collections.defaultdict`, `typing.Any`, and the
`dict`/`list`/`int` builtins. Each import is guarded in try/except (and
`add_safe_globals` itself is feature-detected) so a symbol that moved or was
removed across omegaconf/torch versions cannot break startup — we register
whatever resolves. Deliberately avoided the blunt `weights_only=False` /
global `torch.load` monkeypatch so unrelated loads keep the safety check.

## Result
- `uv run python -c "import app.transcription"` -> `import OK` under
  `torch 2.6.0+cu124` (no syntax errors, allowlisting runs at import).
- Verified the registry via `torch.serialization.get_safe_globals()`: all six
  target omegaconf symbols plus `collections.defaultdict`, `typing.Any`,
  `dict`, `list`, `int` are present after import.
- Full model load not exercised here (needs the model files / download); the
  fix targets exactly the global that the reported traceback rejected.
