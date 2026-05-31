"""Tests for the hebrew-transcript-review vocab helper.

The module under test is a plain script under
`.claude/skills/hebrew-transcript-review/scripts/vocab.py`. It is loaded via an
explicit path. Every test monkeypatches `vocab.VOCAB_PATH` to a tmp file so the
real repo-root VOCAB.md is NEVER touched.
"""
import importlib.util
import pathlib

import pytest

_VOCAB_PY = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".claude/skills/hebrew-transcript-review/scripts/vocab.py"
)
_spec = importlib.util.spec_from_file_location("vocab", _VOCAB_PY)
vocab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vocab)


@pytest.fixture
def vocab_file(tmp_path, monkeypatch):
    """Point vocab.VOCAB_PATH at a tmp file; return that Path."""
    target = tmp_path / "VOCAB.md"
    monkeypatch.setattr(vocab, "VOCAB_PATH", target)
    return target


EXPECTED_HEADER = "| מילה | פירוש | דוגמה מההקשר | תאריך |"
EXPECTED_SEPARATOR = "| --- | --- | --- | --- |"


# --- create-if-missing ---------------------------------------------------


def test_append_creates_file_with_exact_header(vocab_file):
    assert not vocab_file.exists()
    vocab.append("מליאה", "ישיבת המליאה", "נצביע במליאה", "2026-05-31")
    assert vocab_file.exists()
    lines = vocab_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == EXPECTED_HEADER
    assert lines[1] == EXPECTED_SEPARATOR
    # exactly one data row
    data_rows = [ln for ln in lines[2:] if ln.strip()]
    assert len(data_rows) == 1
    assert "מליאה" in data_rows[0]
    assert "ישיבת המליאה" in data_rows[0]
    assert "2026-05-31" in data_rows[0]


def test_lookup_missing_file_returns_none_and_no_write(vocab_file):
    assert not vocab_file.exists()
    assert vocab.lookup("מליאה") is None
    # lookup must NOT create the file
    assert not vocab_file.exists()


# --- lookup hit / miss ---------------------------------------------------


def test_lookup_hit_returns_row_dict(vocab_file):
    vocab.append("מליאה", "ישיבת המליאה", "נצביע במליאה", "2026-05-31")
    row = vocab.lookup("מליאה")
    assert row == {
        "word": "מליאה",
        "meaning": "ישיבת המליאה",
        "example": "נצביע במליאה",
        "date": "2026-05-31",
    }


def test_lookup_miss_returns_none(vocab_file):
    vocab.append("מליאה", "ישיבת המליאה", "נצביע במליאה", "2026-05-31")
    assert vocab.lookup("שולחן") is None


# --- normalization -------------------------------------------------------


def test_normalize_strips_niqqud(vocab_file):
    # מְלִיאָה (with niqqud) must match stored מליאה
    vocab.append("מליאה", "ישיבת המליאה", "ctx", "2026-05-31")
    row = vocab.lookup("מְלִיאָה")
    assert row is not None
    assert row["meaning"] == "ישיבת המליאה"


def test_normalize_strips_one_leading_prefix_letter(vocab_file):
    # ONE leading prefix is stripped: 'ודירה' -> strip 'ו' -> 'דירה'. The stem 'דירה'
    # does not begin with a prefix letter, so the stored bare 'דירה' normalizes to
    # itself and the prefixed surface form matches it.
    vocab.append("דירה", "apartment", "ctx", "2026-05-31")
    assert vocab.lookup("ודירה") is not None


def test_normalize_prefix_matches_bare_stem(vocab_file):
    # 'בדירה' (ב prefix) matches stored bare 'דירה'. (Per the DESIGN NOTE §3 limit, only
    # ONE prefix letter is stripped and the rule cannot disambiguate a root-initial
    # prefix-letter such as מ; this case deliberately uses a prefix-free stem.)
    vocab.append("דירה", "apartment", "ctx", "2026-05-31")
    assert vocab.lookup("בדירה") is not None


def test_normalize_does_not_overstrip_short_word(vocab_file):
    # 'בו' -> stripping 'ב' leaves 'ו' (1 char) which is < 2, so NO strip; stays 'בו'.
    assert vocab.normalize("בו") == "בו"


def test_normalize_folds_final_letter_forms(vocab_file):
    # ץ -> צ final-form fold: 'עץ' stored, lookup 'עצ' (medial) should match.
    vocab.append("עץ", "tree", "ctx", "2026-05-31")
    row = vocab.lookup("עצ")
    assert row is not None
    # and the reverse direction
    assert vocab.normalize("שלום") == vocab.normalize("שלום")
    assert vocab.normalize("ארץ") == vocab.normalize("ארצ")


# --- no-duplicate append -------------------------------------------------


def test_append_same_normalized_word_twice_yields_one_row(vocab_file):
    vocab.append("דירה", "meaning A", "ctx A", "2026-05-31")
    # second append with a niqqud+prefix variant that normalizes equal -> no-op
    vocab.append("בּדִירָה", "meaning B", "ctx B", "2026-06-01")
    lines = vocab_file.read_text(encoding="utf-8").splitlines()
    data_rows = [ln for ln in lines[2:] if ln.strip()]
    assert len(data_rows) == 1
    # original row preserved (not mutated)
    assert "meaning A" in data_rows[0]
    assert "meaning B" not in data_rows[0]


# --- pipe escaping -------------------------------------------------------


def test_append_escapes_pipe_in_fields(vocab_file):
    vocab.append("test", "a|b meaning", "x|y example", "2026-05-31")
    text = vocab_file.read_text(encoding="utf-8")
    assert r"a\|b meaning" in text
    assert r"x\|y example" in text
    # table stays well-formed: data row still has exactly 5 pipes (4 cols)
    data_rows = [
        ln for ln in text.splitlines()[2:] if ln.strip()
    ]
    assert data_rows[0].count("|") == data_rows[0].count(r"\|") + 5
