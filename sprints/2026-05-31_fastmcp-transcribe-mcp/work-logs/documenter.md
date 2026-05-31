# Work Log — @documenter

## 2026-05-31T19:40:00Z — Task T5

**Task ID:** T5 — Write usage docs for the `transcribe` MCP tool and how to register the server with Claude.

**Attempted / Done:**
- Read context: `CLAUDE.md` (§3, §7), `plan.md` (T5 + Context), `mcp_code/server.py`, and `work-logs/backend.md`.
- Verified the entrypoint/commands against `server.py` before writing: `if __name__ == "__main__": mcp.run()` matches `uv run python -m mcp_code.server`; FastMCP server name is `ivrit-transcribe`; tool name `transcribe`; env var `TRANSCRIBE_API_URL` default `http://localhost:8000`; output shape `{segments:[{speaker,text,start,end}], language, num_speakers}`.
- Created `mcp_code/README.md` covering: (1) what `transcribe` does (local audio path in -> diarized JSON out) with input/output shapes and error behavior; (2) prerequisite FastAPI service (`uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`) and pointing the MCP at it via `TRANSCRIBE_API_URL`; (3) run command, the exact `claude mcp add ivrit-transcribe -- uv run python -m mcp_code.server` register command, and a copy-pasteable Claude Desktop `mcpServers` JSON snippet with `cwd` + optional `env`; (4) one English and one Hebrew example request, quoting the sample audio path `resource/audio smaples/audio_sample_1min.m4a` (space + "smaples" typo preserved).

**Files touched:**
- `mcp_code/README.md` (new)
- this work-log

**Commit:** `530c843` — `@documenter: add mcp_code/README usage and registration docs` (branch `sprint/fastmcp-transcribe-mcp`; only README staged, sprint folder NOT committed).

**Blockers:** none.

**Status:** done.
