# Work Log — @architect

## 2026-05-31 — Task T2

**Task ID:** T2 — Define `mcp_code/` module layout, the `transcribe` tool signature/return contract, env-var config, and bilingual tool-description strategy.

**Attempted / Done:** Produced the DESIGN SPEC below (the deliverable). Read the `/transcribe` contract (`app/main.py`), the reference HTTP call (`client_example.py:transcribe()` lines 81-91), the plan Context, and the existing `tests/` layout to ground the decisions. No code written — this note is the spec T3 implements and T4 tests against.

**Files touched:** this work-log only.

**Blockers:** none.

---

# DESIGN SPEC — FastMCP `transcribe` server (`mcp_code/`)

Minimal, single-file, single-tool. Forwards HTTP only — no ML model, no work at import time.

## 1. File layout

```
mcp_code/
  __init__.py          # empty (or version string); makes mcp_code an importable package
  server.py            # FastMCP instance + the single `transcribe` tool + run entrypoint
tests/
  test_mcp_server.py   # T4 tests (top-level tests/ package — see justification)
```

**Test location decision: `tests/test_mcp_server.py` (top-level `tests/` package).**
Justification: the repo already standardizes on a flat top-level `tests/` package
(`tests/__init__.py`, `test_client_example.py`, `test_config.py`, `test_main.py`,
`test_schemas.py`). Matching that convention means one pytest rootdir, one
discovery path, and consistency with how `client_example.py` (the module this
tool mirrors) is already tested in `tests/test_client_example.py`. Do NOT create
`mcp_code/tests/`. Name the file `test_mcp_server.py` to mirror `test_main.py`.

**`mcp_code/__init__.py`:** keep empty. The tool reads config from the
environment at call time (see §4), so there is nothing to initialize at package
import. Import of the package and of `mcp_code.server` must not touch the network
or start the server (acceptance T3.6).

## 2. Tool signature & return contract

```python
@mcp.tool()
def transcribe(audio_path: str) -> dict:
    ...
```

- **Input:** `audio_path: str` — a path on the **local filesystem** (the same
  machine the MCP server process runs on). Plain `str`, not `Path`, because MCP
  tool arguments arrive as JSON; convert to `Path` internally.
- **Output:** **raw pass-through of the API's JSON dict** — return `resp.json()`
  verbatim, i.e. `{"segments": [{"speaker", "text", "start", "end"}, ...],
  "language": str|null, "num_speakers": int|null}`.

**Decision: raw dict pass-through, NOT a wrapper.** Rationale:
- The plan mandates "output is the API's JSON dict passed through unchanged" and
  "Honor the existing `/transcribe` contract verbatim (do not invent fields)."
- A wrapper (e.g. `{"ok": true, "result": {...}}`) would invent fields and force
  T4 to assert on a shape that isn't the API's. Pass-through keeps the MCP a thin
  proxy: the contract has exactly one source of truth (`app/schemas.py` ->
  `TranscriptionResponse`). If the API contract changes, the tool needs no edit.
- T4's happy-path assertion (`tool returns that exact dict`) is only satisfiable
  with pass-through.

Do not re-validate or re-parse the API payload; trust `resp.json()` after
`raise_for_status()`.

## 3. Error behavior

Two distinct failure classes, both surfaced as clear, readable errors (never a
silent `None`/partial return — acceptance T4.3):

1. **Missing / non-file path (checked BEFORE any network call):**
   ```python
   path = Path(audio_path)
   if not path.is_file():
       raise FileNotFoundError(f"Audio file not found: {audio_path}")
   ```
   Use `Path.is_file()` (mirrors `client_example.py:99`), which is False for both
   nonexistent paths and directories. **The HTTP client must NOT be called in
   this case** (acceptance T3.2 / T4.2). Raising `FileNotFoundError` is the
   recommended form; FastMCP converts a raised exception into a tool error
   the model sees. (A returned error string is acceptable per the plan, but
   raising is cleaner and is what T4.2 will assert by checking the client was
   not called.)

2. **Non-2xx API response or transport failure:** wrap the POST so the message
   includes the HTTP status code when there is one:
   ```python
   try:
       resp = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)
       resp.raise_for_status()
   except requests.HTTPError as exc:
       raise RuntimeError(
           f"Transcription API returned HTTP {resp.status_code} for {url}: "
           f"{resp.text[:500]}"
       ) from exc
   except requests.RequestException as exc:
       raise RuntimeError(f"Transcription request to {url} failed: {exc}") from exc
   ```
   The status code MUST appear in the message for the `raise_for_status` path
   (acceptance: "readable error including status code"). Keep the body snippet
   short (`[:500]`) so a 500 HTML page doesn't flood the model context.
   `RequestException` is the base class for connection/timeout errors that have
   no status code — those get the second branch.

Mirror `client_example.py`'s file-handle pattern so the file is opened inside a
`with` block and the POST happens while the handle is open:
```python
with path.open("rb") as fileobj:
    files = {"file": (path.name, fileobj, "audio/m4a")}
    resp = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
return resp.json()
```
(The `raise_for_status` / error-wrapping from above applies; shown condensed here.)

## 4. Config

- **Base URL:** environment variable `TRANSCRIBE_API_URL`, default
  `http://localhost:8000`. Strip a trailing slash (`.rstrip("/")`) before
  appending `/transcribe`, matching `client_example.py:96`.
- **Timeout:** module-level constant `REQUEST_TIMEOUT = 600` (seconds), reusing
  `client_example.py`'s 600 s headroom for slow CPU transcription. This is a
  fixed constant, not env-driven.

**When is the env var read? Decision: read INSIDE the tool function at call
time** (not captured as a module constant at import).
```python
DEFAULT_API_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 600  # seconds — slow CPU transcription headroom

@mcp.tool()
def transcribe(audio_path: str) -> dict:
    base_url = os.environ.get("TRANSCRIBE_API_URL", DEFAULT_API_URL).rstrip("/")
    url = f"{base_url}/transcribe"
    ...
```
Rationale:
- T4 needs to override the base URL trivially. Reading inside the tool means a
  test does `monkeypatch.setenv("TRANSCRIBE_API_URL", "http://test")` (or just
  relies on the default and asserts the URL) with **no import-order gymnastics**.
  A constant captured at import would freeze whatever env was set when `server.py`
  was first imported — fragile across the test session.
- It satisfies T3.6: importing `mcp_code.server` with zero env vars must succeed.
  Reading inside the tool guarantees no env access at import.
- `DEFAULT_API_URL` and `REQUEST_TIMEOUT` stay as module constants so they are
  discoverable and (if ever needed) monkeypatchable, but the *resolved* URL is
  always computed per call from the live environment.

## 5. Bilingual description strategy (exact docstring for T3 to paste)

The tool's docstring IS its MCP description — it is what the model reads to decide
routing. It must carry BOTH English and Hebrew trigger cues so a Hebrew-phrased
request ("תמלל את קובץ האודיו ...") routes here, even though the build itself is
done in English per `mcp-rest-builder`.

**Paste this verbatim as the `transcribe` tool docstring (do not translate or
trim the Hebrew):**

```python
def transcribe(audio_path: str) -> dict:
    """Transcribe a local audio file into diarized, speaker-labeled text.

    Use this tool whenever the user asks to transcribe / get a transcript of an
    audio file that exists on the local filesystem, in EITHER English or Hebrew.
    English trigger examples: "transcribe this audio file", "get a transcript of
    /path/to/recording.m4a", "what is said in this recording".
    Hebrew trigger examples: "תמלל את קובץ האודיו", "תמלל את ההקלטה הזו",
    "מה נאמר בקובץ הקול הזה", "תן לי תמלול של קובץ השמע".

    Args:
        audio_path: Absolute or relative path to a local audio file
            (e.g. .m4a, .wav, .mp3) on this machine.

    Returns:
        A dict from the transcription API, passed through unchanged:
        {
            "segments": [{"speaker": str, "text": str,
                          "start": float, "end": float}, ...],
            "language": str | null,
            "num_speakers": int | null
        }

    Raises:
        FileNotFoundError: if audio_path does not point to an existing file
            (the API is NOT called in this case).
        RuntimeError: if the transcription API returns a non-2xx status
            (the HTTP status code is included in the message) or the request
            otherwise fails.
    """
```

The Hebrew lines must be stored as real UTF-8 Hebrew in the source file (the
file is plain `.py`, UTF-8 — only the `mcp-rest-builder` *CLI* renders Hebrew
poorly; the committed source is fine). Keep all Hebrew examples; they are the
routing signal.

## 6. Notes for T3 (implementation pointers, non-binding)

- Server construction: `from fastmcp import FastMCP; mcp = FastMCP("ivrit-transcribe")`,
  then `@mcp.tool()` on `transcribe`. Provide a `if __name__ == "__main__": mcp.run()`
  entrypoint so `uv run python -m mcp_code.server` works (coordinate exact
  wording with T1/T5).
- Imports needed: `os`, `pathlib.Path`, `requests`, `fastmcp.FastMCP`. Nothing
  from `app/` — this server must not import the FastAPI app or any ML code.
- Keep everything in `server.py`. One tool, one module.
