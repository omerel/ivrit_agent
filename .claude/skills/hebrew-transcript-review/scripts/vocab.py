"""VOCAB.md lookup/append + Hebrew word normalization.

Deterministic helper for the `hebrew-transcript-review` skill. Reads and writes
ONLY the repo-root `VOCAB.md` (never `resource/`). `VOCAB_PATH` is a module-level
attribute so tests can monkeypatch it to a tmp file.

Contract (architect DESIGN NOTE §3):
  normalize(word) -> str        # NFC, strip niqqud/punct/marks, strip one prefix, fold finals
  lookup(word)    -> dict|None  # first matching row by normalized key; no write if file missing
  append(word, meaning, example, date) -> None  # create-if-missing, idempotent on normalized key
"""
import pathlib
import unicodedata

# Repo-root VOCAB.md (this file is at <root>/.claude/skills/hebrew-transcript-review/scripts/vocab.py).
VOCAB_PATH = pathlib.Path(__file__).resolve().parents[4] / "VOCAB.md"

HEADER = "| מילה | פירוש | דוגמה מההקשר | תאריך |"
SEPARATOR = "| --- | --- | --- | --- |"

# Leading prefix letters strippable when the remaining stem is >= 2 chars.
_PREFIXES = set("והבכלמש")

# Final-letter form -> medial form.
_FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}

# Punctuation / marks to strip during normalization.
_STRIP_CHARS = set("־׳״\"'.,") | {"‎", "‏"}


def normalize(word: str) -> str:
    """Return the lookup key for `word` per the DESIGN NOTE §3 rule.

    Limit (documented per §3): at most ONE leading prefix letter is stripped, and
    the rule is lexical only -- it cannot tell a root-initial prefix letter (e.g.
    the מ of מליאה) from a genuine prefix, so a stored base beginning with a prefix
    letter will itself be stripped. Matching is reliable for stems that do not
    begin with one of ו/ה/ב/כ/ל/מ/ש.
    """
    # 1. NFC, then strip niqqud / cantillation (U+0591–U+05C7).
    s = unicodedata.normalize("NFC", word)
    s = "".join(ch for ch in s if not ("֑" <= ch <= "ׇ"))
    # 2. Strip maqaf / geresh / quotes / periods / commas / directional marks.
    s = "".join(ch for ch in s if ch not in _STRIP_CHARS)
    s = s.strip()
    # 3. Strip ONE leading prefix letter iff the remaining stem is >= 2 chars.
    if len(s) >= 1 and s[0] in _PREFIXES and len(s) - 1 >= 2:
        s = s[1:]
    # 4. Fold final-letter forms to medial.
    s = "".join(_FINALS.get(ch, ch) for ch in s)
    # 5. Trim surrounding whitespace.
    return s.strip()


def _escape(value: str) -> str:
    """Escape a literal pipe so the Markdown table stays well-formed."""
    return value.replace("|", r"\|")


def _parse_cell(cell: str) -> str:
    """Reverse the pipe-escaping for a single cell value."""
    return cell.replace(r"\|", "|").strip()


def _split_row(line: str) -> list[str]:
    """Split a Markdown table row into its cell values, honoring `\\|` escapes."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    cells = []
    buf = ""
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner) and inner[i + 1] == "|":
            buf += "\\|"
            i += 2
            continue
        if inner[i] == "|":
            cells.append(buf)
            buf = ""
            i += 1
            continue
        buf += inner[i]
        i += 1
    cells.append(buf)
    return cells


def _iter_rows():
    """Yield {word,meaning,example,date} dicts for each data row in VOCAB.md."""
    if not VOCAB_PATH.exists():
        return
    lines = VOCAB_PATH.read_text(encoding="utf-8").splitlines()
    for line in lines[2:]:  # skip header + separator
        if not line.strip():
            continue
        cells = _split_row(line)
        if len(cells) < 4:
            continue
        yield {
            "word": _parse_cell(cells[0]),
            "meaning": _parse_cell(cells[1]),
            "example": _parse_cell(cells[2]),
            "date": _parse_cell(cells[3]),
        }


def lookup(word: str):
    """Return the first row whose col-1 word normalizes equal to `word`, else None.

    No write occurs if VOCAB.md is missing.
    """
    key = normalize(word)
    for row in _iter_rows():
        if normalize(row["word"]) == key:
            return row
    return None


def append(word: str, meaning: str, example: str, date: str) -> None:
    """Append one well-formed row; create VOCAB.md with the header if missing.

    Idempotent on the normalized key: a no-op if `word` already normalizes to an
    existing row (no second row, no mutation of the existing row).
    """
    if lookup(word) is not None:
        return

    row = "| {} | {} | {} | {} |".format(
        _escape(word), _escape(meaning), _escape(example), _escape(date)
    )

    if not VOCAB_PATH.exists():
        VOCAB_PATH.parent.mkdir(parents=True, exist_ok=True)
        VOCAB_PATH.write_text(
            HEADER + "\n" + SEPARATOR + "\n" + row + "\n", encoding="utf-8"
        )
        return

    text = VOCAB_PATH.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    VOCAB_PATH.write_text(text + row + "\n", encoding="utf-8")
