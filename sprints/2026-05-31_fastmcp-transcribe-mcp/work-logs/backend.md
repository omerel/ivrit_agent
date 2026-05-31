# Work Log — @backend

## 2026-05-31T19:14:56Z — Task T3

**Task ID:** T3 — Implement the FastMCP server and `transcribe` tool in `mcp_code/`, using the `mcp-rest-builder` skill.

**Attempted / Done:**
- Read context in order: `CLAUDE.md`, `plan.md` (T3 + Context), the architect's DESIGN SPEC (`work-logs/architect.md`), and `client_example.py` (reused its multipart request shape, lines 81-91).
- Invoked the `mcp-rest-builder` skill. Its generic interactive CLI workflow targets a different layout (`mcp_code/mcp_service_<name>/` + a JSON-body `query_<name>(input: QueryInput)` tool). The architect's DESIGN SPEC is the authoritative implementation contract for this task and mandates a divergent shape: flat `mcp_code/server.py`, a `transcribe(audio_path: str) -> dict` tool, multipart file upload (not JSON body), raw `resp.json()` pass-through, and an exact verbatim bilingual docstring. Implemented exactly to the architect's spec (the binding contract) while honoring the skill's intent of wrapping the existing REST `/transcribe` API.
- Created `mcp_code/__init__.py` (empty) and `mcp_code/server.py`:
  - `FastMCP("ivrit-transcribe")` instance; `@mcp.tool()`-decorated `transcribe(audio_path: str) -> dict`.
  - Validates `Path(audio_path).is_file()` FIRST; raises `FileNotFoundError(f"Audio file not found: {audio_path}")` and does NOT call the API on a bad path.
  - On valid path: reads `TRANSCRIBE_API_URL` from env INSIDE the tool (`os.environ.get("TRANSCRIBE_API_URL", DEFAULT_API_URL).rstrip("/")`), POSTs `files = {"file": (path.name, fileobj, "audio/m4a")}` to `{base}/transcribe`, `timeout=REQUEST_TIMEOUT` (600s).
  - `resp.raise_for_status()`; returns `resp.json()` raw. `requests.HTTPError` -> `RuntimeError` including `resp.status_code` + `resp.text[:500]`; `requests.RequestException` -> readable `RuntimeError`.
  - Module constants `DEFAULT_API_URL = "http://localhost:8000"`, `REQUEST_TIMEOUT = 600`.
  - Architect's exact bilingual (English + Hebrew) docstring pasted verbatim as real UTF-8.
  - `if __name__ == "__main__": mcp.run()` entrypoint.
  - No ML model load, no network/API call at import time.

**Verification (verification-before-completion discipline):**
- `env -u TRANSCRIBE_API_URL uv run python -c "import mcp_code.server"` → `IMPORT OK`, tool present `True`, mcp name `ivrit-transcribe`. Succeeds with no env vars and no network.
- Docstring check: both `"תמלל את קובץ האודיו"` (Hebrew) and `"transcribe this audio file"` (English) cues present; constants resolve to `http://localhost:8000` / `600`.
- `fastmcp 3.3.1` confirmed importable via `uv run`.

**Files touched:**
- `mcp_code/__init__.py` (new, empty)
- `mcp_code/server.py` (new)
- this work-log

**Commit:** `112af18` — `@backend: add FastMCP server with transcribe tool wrapping /transcribe API` (on branch `sprint/fastmcp-transcribe-mcp`; sprint folder NOT committed).

**Run / entrypoint command (for T1 / T5 to match):**
```
uv run python -m mcp_code.server
```
Claude registration form (for T5): `claude mcp add ivrit-transcribe -- uv run python -m mcp_code.server`. The MCP server name registered with FastMCP is `ivrit-transcribe`.

**Blockers:** none.

**Status:** done.
