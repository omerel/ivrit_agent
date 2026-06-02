"""Tests for app.config — env-driven Settings with main.py-matching defaults."""
import importlib
import os
from pathlib import Path


def _fresh_config():
    """Import a fresh copy of app.config so env changes take effect."""
    import app.config as config
    return importlib.reload(config)


def test_defaults_match_main_py(monkeypatch):
    # Ensure no env vars leak into the defaults check.
    for var in [
        "WHISPER_MODEL", "DEVICE", "COMPUTE_TYPE", "LANGUAGE",
        "DIARIZATION_CONFIG", "MIN_SPEAKERS", "BATCH_SIZE",
        "MAX_UPLOAD_BYTES", "HOST", "PORT", "HF_HUB_OFFLINE",
    ]:
        monkeypatch.delenv(var, raising=False)
    cfg = _fresh_config()
    # Disable .env-file loading so this asserts the CODE defaults only,
    # independent of any local .env that overrides values (e.g. WHISPER_MODEL
    # pointing at a local model snapshot).
    s = cfg.Settings(_env_file=None)
    assert s.WHISPER_MODEL == "ivrit-ai/whisper-large-v3-turbo-ct2"
    assert s.DEVICE == "cpu"
    assert s.COMPUTE_TYPE == "int8"
    assert s.LANGUAGE == "he"
    assert s.DIARIZATION_CONFIG == "models/pyannote-diarization/config.yaml"
    assert s.MIN_SPEAKERS == 2
    assert s.BATCH_SIZE == 4
    assert s.MAX_UPLOAD_BYTES == 26_214_400
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 8000
    assert s.HF_HUB_OFFLINE == "1"


def test_env_override(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("DEVICE", "cuda")
    cfg = _fresh_config()
    s = cfg.Settings()
    assert s.PORT == 9000
    assert s.DEVICE == "cuda"


def test_hf_hub_offline_exported_at_import(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    _fresh_config()
    assert os.environ["HF_HUB_OFFLINE"] == "1"


def test_diarization_config_resolves_to_absolute_repo_root(monkeypatch):
    monkeypatch.delenv("DIARIZATION_CONFIG", raising=False)
    cfg = _fresh_config()
    p = cfg.settings.diarization_config_path
    assert isinstance(p, Path)
    assert p.is_absolute()
    # Resolved against repo root (parent of app/), not CWD.
    repo_root = Path(cfg.__file__).resolve().parent.parent
    assert p == (repo_root / "models/pyannote-diarization/config.yaml").resolve()


def test_diarization_config_absolute_override_honored(monkeypatch):
    monkeypatch.setenv("DIARIZATION_CONFIG", "/tmp/custom/config.yaml")
    cfg = _fresh_config()
    s = cfg.Settings()
    assert s.diarization_config_path == Path("/tmp/custom/config.yaml")
