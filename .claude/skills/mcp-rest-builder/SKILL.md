---
name: mcp-rest-builder
description: Use when the user wants to build a FastMCP server that wraps an existing REST API and exposes its data through Claude Code. Triggers on requests like "build an MCP", "fastmcp", "wrap REST as MCP". The skill conducts the entire workflow in English (CLI does not render Hebrew correctly).
---

# mcp-rest-builder

Build a FastMCP server that wraps an existing REST API. The user interacts in English throughout (the CLI does not render Hebrew correctly — it appears reversed).

## How to use this skill

**Announce at start:** "I'll build an MCP server with you — we'll go through 10 steps together."

Create one TodoWrite todo per step below. Mark each `in_progress` when you start it and `completed` when its hard gate is satisfied. Do NOT skip ahead.

All text shown to the user MUST be in English. Files written MUST be UTF-8. JSON dumps MUST use `ensure_ascii=False` (data captured from the user — example questions, descriptions — may contain Hebrew even though the conversation is English).

Reusable English strings are in `references/phrasebook.md`. Templates are in `references/*.template`.

Template placeholders in `spec.json.template`, `tools.py.template`, and `test_mcp.py.template` use plain names (no `_HE` suffix) — values you substitute should be English: `DESCRIPTION_EN`, `TOOL_DOCSTRING`, `HAPPY_DESCRIPTION`, `EDGE_DESCRIPTION`, `VALIDATION_DESCRIPTION`. `EXAMPLES_JSON` may still contain Hebrew (or any language) inside the `question` field — that is data captured from the user.

## The 10 steps

### Step 1 — Greet & confirm scope

Send the user (verbatim from `references/phrasebook.md`):
> Hi! I'll help you build an MCP server with fastmcp. I'll ask a few short questions and then build the server.

Wait for any acknowledgment (even a single character) before continuing. Do NOT batch with Step 2.

### Step 2 — Get example folder path

Ask: `Which folder contains your REST API example code?`

When the user answers, validate with Bash:
- Folder exists: `ls -la <path>` should succeed.
- At least one `.py` file present.

If the folder is empty of Python files, ask: `The folder contains no Python files. Please point to a specific file.` and treat the answer as a single file path.

Read every `.py` file in the folder with the Read tool. Pay attention to: any `requests.post(...)` / `requests.get(...)` calls — they reveal `url`, `headers`, and `payload` literals. Save the first such triple as `SEED_URL`, `SEED_HEADERS`, `SEED_PAYLOAD` in the working context for use in Step 6.

If the folder contains more than one `.py` file, ask the user: `Which Python file should I run as the API example? (e.g. main.py)` and save the answer as `EXAMPLE_FILE_PATH`. If exactly one `.py` file exists, set `EXAMPLE_FILE_PATH` to its path automatically. Step 6a uses `EXAMPLE_FILE_PATH` for the baseline run.

Also detect and save `SEED_METHOD`: examine the example file — if it calls `requests.post(...)`, set `SEED_METHOD = "POST"`. If it calls `requests.get(...)`, set `SEED_METHOD = "GET"`. Default to `"POST"` if ambiguous.

### Step 3 — Get MCP server name

Ask: `What name do you want for the MCP server? (e.g. taxi, weather)`

Validate the answer is a single lowercase ASCII word (`[a-z][a-z0-9_]*`). If not, ask again with an English explanation. Save as `NAME`.

Derive and save one further name from `NAME` for use by Steps 7-9:
- `TOOL_NAME = "query_" + NAME` (e.g. `query_taxi`) — Python function name; must match `[a-z][a-z0-9_]*`.

Then check: does `mcp_code/mcp_service_<NAME>/` already exist?
- If yes, ask: `The folder mcp_code/mcp_service_{{NAME}}/ already exists. Do you want to: 1) delete and rewrite, 2) add a suffix, 3) cancel?` Handle accordingly (option 2 → suffix `_v2`, `_v3`, etc.).
- If no, proceed.

### Step 4 — Get MCP invocation name

Ask: `What name should we use to invoke the MCP server from Claude? (appears in .mcp.json, e.g. taxi-mcp)`

Validate it matches `[a-z][a-z0-9-]*`. Save as `INVOCATION_NAME`.

### Step 5 — Interview about data

Ask these questions one at a time (do NOT batch). Do NOT ask the user which fields are required — that is discovered in Step 6 by running the example and then confirmed with the user in Step 6a-bis.

1. `What database does your API run against?` → save as `DB`
2. `Which table are we pulling data from?` → save as `TABLE`
3. `How would a typical user phrase a question that requires calling this API? Give 1-3 examples (in whatever language your users speak).` → save as `EXAMPLE_QUESTIONS` (used in `spec.json.tools[].examples` — may be Hebrew or any other language; preserve as-is)

Echo the collected answers back in a short English summary before moving on, so the user can catch mistakes early.

### Step 6 — Probe API ≥5 times

**Goal:** ≥5 HTTP exchanges. Any status code counts as "successful" — the server merely needs to respond.

#### 6a. Baseline run
Execute the user's example as-is via Bash subprocess:
```
python <example_file_path>
```
- If the script exits 0 and prints a JSON-looking body → record status, row count, field names. Count as probe 1/5.
- If the script fails with a connection error → halt, send `Could not connect to the API. Make sure the server is running and try again.` Do NOT retry silently.

#### 6a-bis. Confirm parameters with the user

**This step must happen before any mutations (6b) and before asking the user about anything else.** Goal: surface every parameter the example actually uses, and have the user explicitly tell us which are mandatory vs optional.

1. Build `DISCOVERED_PARAMS`: the union of keys in `SEED_PAYLOAD` (from Step 2) and any query-string / body keys actually sent during the baseline run. For each key, record the example value and infer the type (`int`, `str`, `float`, `bool`, `datetime`).
2. Send the user a numbered English list, one parameter per line, in this exact shape:
   > Here are the parameters I found by running your example:
   > 1. `<name>` (type: `<type>`, example: `<value>`)
   > 2. ...
   >
   > For each one, tell me if it is **mandatory** or **optional**. You can answer like: `1 mandatory, 2 optional, 3 mandatory` or `all mandatory except 3`. If you want to add a parameter I missed, tell me its name, type, and whether it is mandatory.
3. Parse the user's reply into a dict `USER_REQUIRED_MAP: {name: bool}`. If the reply is ambiguous (does not cover every parameter, or uses words you can't map to mandatory/optional), ask once more: `I couldn't map your answer to every parameter. Please answer mandatory/optional for each of: <list of unresolved names>.` Hard cap 2 clarification rounds; then halt and ask the user to restate.
4. Echo the final mapping back as a short English summary, e.g. `Got it — mandatory: [a, b]; optional: [c, d]. I'll use this to build QueryInput.` and treat `USER_REQUIRED_MAP` as the authoritative source for `required=` in Step 6c (the probing in 6b only refines descriptions and constraints, it does not override the user's choice).

#### 6b. Run 4 mutations
For each mutation, build a Python one-liner that calls `requests.request(SEED_METHOD, SEED_URL, headers=SEED_HEADERS, json=<mutated_payload>)` and prints `status_code` + `len(response.json())` + `list(response.json()[0].keys()) if response.json() else []`. Execute via Bash. The 4 mutations:

| # | Mutation |
|---|---|
| M1 | Change one field's value to another plausible same-type value |
| M2 | Change one field to an edge value (boundary date, very large number) |
| M3 | Omit one required-looking field |
| M4 | Send wrong type for one field (string where int expected) |

After each call, send the user:
> Probe {N}/{TOTAL} — <mutation description> | status: <status> | rows: <count> | fields: <fields[:5]>

Do NOT dump full response bodies to the user.

#### 6c. Synthesize schema
Build in memory:
- `QUERY_INPUT_FIELDS`: list of `(name, type, required, description, constraints)` tuples for each input field. Set `required` from `USER_REQUIRED_MAP` (Step 6a-bis) — the user's choice is authoritative. Constraints: `ge`/`le` from observed numeric range, enum if ≤5 distinct values observed. Field descriptions should be in English.
- `FIELD_CONSTRAINTS_JSON` and `EDGE_CASES_JSON` for `spec.json`.

The tool returns the raw `resp.json()` payload from the REST API, so no response-row Pydantic model is generated. Still capture observed response field names/types for `OUTPUT_SCHEMA_JSON` and the plan summary in Step 7.

#### 6d. Surface uncertainty
For any field whose probe-observed required-ness disagrees with the user's choice in `USER_REQUIRED_MAP`, send: `Note: field <name> was marked <user_choice> but the API <accepted/rejected> requests without it. Keeping your choice.` Do NOT override the user.

#### 6e. Guardrails
- Hard cap 8 total probes (5 + 3 retries on transient errors).
- If all 5 probes return 4xx/5xx → halt with `All probes returned errors. I'll need help to understand the schema.` and ask user.
- Raw HTTP bodies never written to disk.

**HARD GATE:** Do not begin Step 7 until ≥5 HTTP exchanges have completed (any status code counts). If fewer than 5 completed, run additional probes within the cap of 8, or halt with `All probes returned errors. I'll need help to understand the schema.`

### Step 7 — Present plan

Send the user a plan summary with these exact sections:

```
Build plan:
- MCP name: {{INVOCATION_NAME}}
- Folder: mcp_code/mcp_service_{{NAME}}/
- Tool: {{TOOL_NAME}}(input: QueryInput) -> Any  # returns resp.json() as-is
- Input fields: <list of (name, type, required) from probing>
- Output fields (observed from probing, not enforced): <list of (name, type) from probing>
- 3 tests: happy / edge / validation
```

Then ask: `Here is the plan I intend to implement. If it looks correct, reply "approve" and I'll start writing the code.`

**HARD GATE:** Do not proceed to Step 8 until the user responds with one of: `approve`, `approved`, `ok`, `yes`, `y`. Any other response → ask for clarification, do not write files.

### Step 8 — Generate code

Render each template in `references/` by reading it and replacing `{{PLACEHOLDER}}` tokens with computed values. Use the Write tool to create:

1. `mcp_code/mcp_service_{{NAME}}/__init__.py` — empty file
2. `mcp_code/mcp_service_{{NAME}}/pydantic_models.py` — from `pydantic_models.py.template`
3. `mcp_code/mcp_service_{{NAME}}/tools.py` — from `tools.py.template`
4. `mcp_code/mcp_service_{{NAME}}/server.py` — from `server.py.template`
5. `mcp_code/mcp_service_{{NAME}}/spec.json` — from `spec.json.template`
6. `mcp_code/__init__.py` — empty if it does not exist

Substitution rules:
- All user-supplied strings (descriptions, example questions): pass through unchanged (UTF-8) — may contain Hebrew or any other language.
- All `*_JSON` placeholders in `spec.json.template`: pre-serialize the Python value with `json.dumps(value, ensure_ascii=False)` before substitution.
- `{{QUERY_INPUT_FIELDS}}`: emit one line per field, 4-space indented, ending with `\n`.
- `INPUT_SCHEMA_JSON`: build a JSON Schema object from `QUERY_INPUT_FIELDS`. Shape: `{"type": "object", "properties": {<field>: {<type+constraints>}, ...}, "required": [<names of required fields>]}`. Map Pydantic types to JSON Schema: `int` → `"integer"`, `str` → `"string"`, `float` → `"number"`, `bool` → `"boolean"`, `datetime` → `{"type": "string", "format": "date-time"}`. Include `ge`/`le`/enum constraints if observed during probing. Pre-serialize with `json.dumps(schema, ensure_ascii=False)` before substitution.
- `OUTPUT_SCHEMA_JSON`: describes the observed response shape only (not enforced by the tool). Build `{"type": "array", "items": <object schema built from observed response field names/types using the same type mapping>}` when the API returned a list of objects; otherwise emit a minimal schema (e.g. `{"type": "object"}` or `{}`). Pre-serialize with `json.dumps(..., ensure_ascii=False)`.
- `BASE_URL` ← `SEED_URL` (extracted in Step 2).
- `HEADERS_JSON` ← `json.dumps(SEED_HEADERS, ensure_ascii=False)`.
- `EXAMPLES_JSON` ← `json.dumps([{"question": q, "input": SEED_PAYLOAD} for q in EXAMPLE_QUESTIONS], ensure_ascii=False)`.
- `DESCRIPTION_EN` ← a short English description Claude composes from `DB`+`TABLE` collected in Step 5 (e.g. `f"MCP for querying data from table {TABLE} in database {DB}"`).

After writing, send English confirmation: `Wrote {N} files under mcp_code/mcp_service_{{NAME}}/.`

Then verify the generated Python files compile:
```
python -m py_compile mcp_code/mcp_service_{{NAME}}/pydantic_models.py mcp_code/mcp_service_{{NAME}}/tools.py mcp_code/mcp_service_{{NAME}}/server.py
```
If `py_compile` fails: do NOT proceed. Read the error, fix the rendered file (or the substitution), re-run. Hard cap 3 attempts; then halt and report.

### Step 9 — Write & run 3 tests

Render `references/test_mcp.py.template` to `mcp_code/mcp_service_{{NAME}}/tests/test_{{NAME}}_mcp.py`. Also create `mcp_code/mcp_service_{{NAME}}/tests/__init__.py` (empty).

Substitution sources:
- `HAPPY_PAYLOAD_JSON` ← `repr(SEED_PAYLOAD)` (the original example payload, which we know returned data)
- `EDGE_PAYLOAD_JSON` ← `repr(<the mutation from Step 6 that returned 200 with notable shape>)`. If no notable edge case was observed, use M1's payload.
- `INVALID_PAYLOAD_JSON` ← `repr(<a payload guaranteed to violate QueryInput>)` (e.g. send a string where an `int` is required)

Run from the project root:
```
pytest mcp_code/mcp_service_{{NAME}}/tests/ -v
```

Parse the output:
- All 3 pass → send `3/3 tests passed ✓`, proceed to Step 10.
- Any failure → send `Test N failed — fixing and retrying.` Identify the failing test from pytest output, fix the relevant file (`tools.py` for HTTP issues, `pydantic_models.py` for schema mismatches, the test file for bad fixtures), re-run.

**HARD GATE:** Hard cap 3 fix attempts. After 3 consecutive failures, halt and send `Failed to fix the tests after 3 attempts. The error: <ERR>. I'd appreciate guidance.` Do NOT mark the skill complete.

### Step 10 — Wire config & verify

**10a. Merge into .mcp.json**

Read `references/mcp_json.template`, substitute `{{INVOCATION_NAME}}` and `{{NAME}}`, parse as JSON → call it `new_entry` (a dict with one key).

Check if `.mcp.json` exists at the project root:
- **Does not exist:** Write `{"mcpServers": new_entry}` to `.mcp.json`.
- **Exists:** Read it, parse as JSON. If it has a `mcpServers` key, merge: `existing["mcpServers"].update(new_entry)`. If not, add the key. Write back with `json.dump(..., ensure_ascii=False, indent=2)`.

**10b. Enable in .claude/settings.json**

Read `.claude/settings.json` (create empty `{}` if missing). Ensure it contains:
```json
{
  "enabledMcpjsonServers": ["{{INVOCATION_NAME}}", ...other_existing]
}
```
Merge the new invocation name into the list (do not duplicate). Write back UTF-8 with `ensure_ascii=False, indent=2`.

Do NOT touch `.claude/settings.local.json` — it's user-local.

**10c. Final message**

Send:
> The MCP server is ready. Restart Claude Code and run `claude mcp list` to verify it's registered.

Mark the skill complete.

## Hard gates (enforced)

- Step 6 must complete ≥5 probes (any status code is "successful" — server responded) before Step 7.
- Step 7 must receive explicit English approval from the user before Step 8 writes any file.
- Step 9 must show all 3 tests passing before Step 10.

## Error handling

- Network unreachable on a probe → halt, send English error, do not retry silently.
- User's example folder has no `.py` file → ask for an explicit file path.
- `mcp_code/mcp_service_<name>/` already exists → ask in English: overwrite / suffix / cancel.
- `.mcp.json` already exists → parse it, merge the new server entry, preserve existing entries.
- Test failure → fix and re-run, hard cap 3 attempts, then halt and ask user.

## Out of scope

- Multi-MCP-per-run generation.
- HTTP transports other than stdio.
- Auth flows beyond a single static header copied from the example.
- Streaming responses.
