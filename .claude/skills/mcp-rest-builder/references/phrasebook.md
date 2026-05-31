# English Phrasebook for mcp-rest-builder

Use these strings verbatim when talking to the user. They are tuned for clarity and consistency. Do not paraphrase.

The user-facing language is English because the Claude Code CLI does not render RTL text (Hebrew) correctly — it appears reversed. Data captured *from* the user (example questions, descriptions stored in `spec.json`) may still be in any language.

## Greetings & flow

- Greeting: `Hi! I'll help you build an MCP server with fastmcp. I'll ask a few short questions and then build the server.`
- Step transition: `Moving to the next step — {{STEP_NAME}}.`
- Done: `The MCP server is ready. Restart Claude Code and run \`claude mcp list\` to verify it's registered.`

## Gathering questions

- Folder: `Which folder contains your REST API example code?`
- MCP name: `What name do you want for the MCP server? (e.g. taxi, weather)`
- Invocation name: `What name should we use to invoke the MCP server from Claude? (appears in .mcp.json)`
- DB: `What database does your API run against?`
- Table: `Which table are we pulling data from?`
- Required fields: `Which fields are required in the request payload?`
- Expected user questions: `How would a typical user phrase a question that requires calling this API? (give 1-3 examples — any language is fine)`

## Probing reports

- Probe report (per call): `Probe {{N}}/{{TOTAL}} — {{MUTATION_DESC}} | status: {{STATUS}} | rows: {{ROWS}} | fields: {{FIELDS}}`
- Probing complete: `Finished {{N}} probes. Inferred the following schema:`
- Schema uncertainty: `Field {{FIELD}} appeared in {{X}}/{{N}} responses — I'll treat it as optional.`

## Plan approval (Step 7)

- Present plan: `Here is the plan I intend to implement. If it looks correct, reply "approve" and I'll start writing the code.`
- Awaiting approval: `Waiting for approval before writing files.`

## Tests (Step 9)

- All pass: `{{N}}/{{N}} tests passed ✓`
- Some failed: `Test {{N}} failed — fixing and retrying.`
- Cannot fix: `Failed to fix the tests after 3 attempts. The error: {{ERR}}. I'd appreciate guidance.`

## Errors

- Network: `Could not connect to the API. Make sure the server is running and try again.`
- All probes failed: `All probes returned errors. I'll need help to understand the schema.`
- Folder empty: `The folder contains no Python files. Please point to a specific file.`
- Name collision: `The folder mcp_code/mcp_service_{{NAME}}/ already exists. Do you want to: 1) delete and rewrite, 2) add a suffix, 3) cancel?`
