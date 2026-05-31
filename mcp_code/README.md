# ivrit-transcribe — MCP server

A [FastMCP](https://github.com/jlowin/fastmcp) server that exposes a single
`transcribe` tool. The tool forwards a local audio file to the project's
FastAPI `/transcribe` service and returns its diarized result.

## The `transcribe` tool

- **Input:** `audio_path` — a path (absolute or relative) to a local audio
  file on this machine (`.m4a`, `.wav`, `.mp3`, …).
- **Output:** the transcription API's JSON, passed through unchanged:

```json
{
  "segments": [
    {"speaker": "SPEAKER_00", "text": "...", "start": 0.0, "end": 3.2}
  ],
  "language": "he",
  "num_speakers": 1
}
```

If the path is not an existing file, the tool raises `FileNotFoundError` and
does **not** call the API. A non-2xx API response surfaces a `RuntimeError`
that includes the HTTP status code.

## Prerequisite: start the FastAPI service

The MCP server is a thin HTTP forwarder — the FastAPI transcription service
must be running first:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

By default the MCP forwards to `http://localhost:8000`. To point it at a
different host/port, set `TRANSCRIBE_API_URL`:

```bash
export TRANSCRIBE_API_URL=http://my-host:9000
```

## Run the server

```bash
uv run python -m mcp_code.server
```

## Register with Claude Code

```bash
claude mcp add ivrit-transcribe -- uv run python -m mcp_code.server
```

## Register with Claude Desktop

Add this entry to your `claude_desktop_config.json` (set `cwd` to the repo
root on your machine):

```json
{
  "mcpServers": {
    "ivrit-transcribe": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_code.server"],
      "cwd": "/path/to/ivrit_agent",
      "env": {
        "TRANSCRIBE_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

The `env` block is optional — omit it to use the default
`http://localhost:8000`.

## Example requests

Once registered, type a request like one of these to trigger the tool:

- **English:** `Transcribe the audio file at resource/audio smaples/audio_sample_1min.m4a`
- **Hebrew:** `תמלל את קובץ האודיו ב-resource/audio smaples/audio_sample_1min.m4a`
