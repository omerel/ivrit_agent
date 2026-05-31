# Work Log — @planner

## 2026-05-31T22:02:47+0300 — Task PLAN

**Attempted:** Decompose the sprint goal (FastMCP server under `mcp_code/` exposing a `transcribe` tool that wraps the existing FastAPI `/transcribe` endpoint) into an executable `plan.md`.

**What I did:**
- Read `CLAUDE.md` (§5 plan format), `.claude/team.md` (valid nicknames), and the active sprint marker (`sprints/.active` -> `2026-05-31_fastmcp-transcribe-mcp`).
- Listed `resource/` and read only what's relevant: `resource/README.md` and noted the audio sample folder (`audio smaples/audio_sample_1min.m4a`, has a space + "smaples" typo).
- Verified the existing API contract by reading `app/main.py`, `app/schemas.py`, `app/config.py`: `POST /transcribe` takes multipart field `file`, returns `{segments:[{speaker,text,start,end}], language, num_speakers}`; `GET /health`. Default `http://localhost:8000`.
- Read `client_example.py` — it already implements the exact HTTP request shape the MCP tool must reproduce (`files = {"file": (name, fileobj, "audio/m4a")}`, `requests.post(.../transcribe, files=...)`). Pointed T3 at it to avoid re-deriving the contract.
- Confirmed `pyproject.toml`: `uv`, Python >=3.11, `requests` already present, `pytest`+`httpx` in dev group. `fastmcp` must be added (T1).

**Decomposition:** 6 tasks, each independently verifiable.
- T1 @devops — add `fastmcp` dep + record run/register command.
- T2 @architect — design `mcp_code/` layout, tool signature/return, env-var config (`TRANSCRIBE_API_URL` default localhost:8000), and the bilingual (EN+HE) tool-description strategy.
- T3 @backend — implement `mcp_code/server.py` + tool using the `mcp-rest-builder` skill (English build workflow; Hebrew cues live in the shipped docstring). Validates path, POSTs file, returns API JSON.
- T4 @qa — tests with HTTP mocked: happy path, missing file, API error.
- T5 @documenter — `mcp_code/README.md` with running prerequisite, `TRANSCRIBE_API_URL`, copy-pasteable Claude registration command + EN & HE example requests.
- T6 @reviewer — independent close-gate review of T1–T5.

**Key planning decisions:**
- Separated the `mcp-rest-builder` "English-only at the CLI" build constraint from the end-user requirement: the *build* is English; the *shipped docstring* carries Hebrew + English trigger phrasing so the model routes Hebrew requests. Encoded this explicitly in T2/T3 acceptance.
- Left the exact test-file location to @architect (T2) to choose between top-level `tests/` (matches repo convention) vs `mcp_code/tests/`, then T4 follows that choice.
- Sequencing note: T1's dependency add is independent, but the *run command wording* should match T3's entrypoint; flagged for the Orchestrator.

**Files touched:** `sprints/2026-05-31_fastmcp-transcribe-mcp/plan.md` (created), this work-log.

**Blockers:** None. The goal was concrete and the API contract was already verified by the prior sprint.

**Open questions for the guide:** None blocking. Minor: whether the MCP registration in T5 should target a specific Claude surface (Claude Code CLI via `claude mcp add` vs. Claude Desktop JSON config) — T5 defaults to the `claude mcp add` CLI form but can add the Desktop JSON snippet if preferred.
