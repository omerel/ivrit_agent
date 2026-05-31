# Work Log — @qa

## 2026-05-31T00:00:00 — Task T4

**Task ID:** T4 — Write tests for the `transcribe` tool with the HTTP call mocked.

**Attempted / Done:** Created `tests/test_mcp_server.py` (top-level `tests/`
package per the T2 architect spec) with three characterization tests against the
already-implemented `mcp_code/server.py`, all with the network fully mocked
(`monkeypatch.setattr(server.requests, "post", ...)`) — no live server, no model
load. Inspected the FastMCP wrapper first: `@mcp.tool()` returns the underlying
plain function, so `from mcp_code.server import transcribe` yields a directly
callable function (verified: `inspect.isfunction` True, docstring intact, no
`.fn` attribute needed). Tests:
1. **Happy path** — dummy file via `tmp_path`; mocked 200 response whose `.json()`
   returns `{segments:[{speaker:"SPEAKER_00",text:"שלום",start:0.0,end:1.0}],
   language:"he", num_speakers:1}`; asserts the tool returns that exact dict AND
   that `requests.post` was called once with a URL ending in `/transcribe` and a
   `files` kwarg containing key `"file"`.
2. **Missing file** — non-existent path raises `FileNotFoundError` and asserts
   `requests.post` was NOT called.
3. **API error** — mocked 500 response whose `raise_for_status()` raises
   `requests.HTTPError`; asserts the tool raises `RuntimeError` whose message
   includes the status code `"500"`.

Ran a mutation sanity check (broke the happy-path expected dict → confirmed
FAILED, then restored) to prove the assertions are load-bearing.

**Verification:** `uv run pytest tests/test_mcp_server.py -v` →
`3 passed, 1 warning in 0.60s`. The single warning is an upstream
`opentelemetry` `DeprecationWarning` (a fastmcp transitive dependency), not from
test code.

**Files touched:** `tests/test_mcp_server.py` (new); `plan.md` (T4 → done);
this work-log.

**Commit:** see `@qa:` commit on branch `sprint/fastmcp-transcribe-mcp`.

**Blockers:** none.
</content>
</invoke>
