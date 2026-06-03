# ivrit_agent — Hebrew Speech Transcription + Diarization Service

A  FastAPI service that accepts an uploaded audio file and returns structured JSON
of a **speaker-diarized Hebrew transcription**. It wraps a
[whisperx](https://github.com/m-bain/whisperX) speech-to-text model
(`ivrit-ai/whisper-large-v3-turbo-ct2`) together with a local
[pyannote](https://github.com/pyannote/pyannote-audio) diarization pipeline, so
each transcribed segment is labeled with the speaker who said it.

The whisper model and the diarization pipeline are loaded **once at startup**
(FastAPI lifespan) and reused across requests. All models run **fully offline** —
no network model fetch at request time.

## Requirements

- Python `>=3.11`
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- `ffmpeg` on the system path (whisperx shells out to it to decode audio)
- The local diarization models under `models/pyannote-diarization/` (see
  [Offline model requirements](#offline-model-requirements))

## Install

First install the `ffmpeg` system binary (whisperx shells out to it to decode
audio). The service refuses to start without it:

```bash
sudo apt-get install -y ffmpeg       # Debian/Ubuntu
brew install ffmpeg                  # macOS
conda install -c conda-forge ffmpeg  # no root / conda env
```

Then sync Python dependencies:

```bash
uv sync
```

This installs `whisperx`, `fastapi`, `uvicorn[standard]`, `python-multipart`,
`pydantic-settings`, and `requests` from the locked `uv.lock`.

## Run

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The app reads `HOST` and `PORT` from the environment (defaults `0.0.0.0` /
`8000`), so when those env vars are set you can omit the flags:

```bash
uv run uvicorn app.main:app
```

On startup the service loads the whisper model and the diarization pipeline
(this is the slow step and runs exactly once). Once you see the "Models loaded"
log line, the service is ready.

## Endpoints

| Method | Path          | Description                                            |
|--------|---------------|--------------------------------------------------------|
| `GET`  | `/`           | Browser upload page (see [Web UI](#web-ui)).           |
| `POST` | `/transcribe` | Transcribe + diarize an uploaded audio file.           |
| `GET`  | `/health`     | Liveness probe. Returns `{"status": "ok"}`.            |

### `POST /transcribe` contract

- **Request:** `multipart/form-data` with a single file part named **`file`**.
- **Response:** `200 OK` with the JSON schema below.
- **Errors:** `400` for an empty upload, rejection for an upload larger than
  `MAX_UPLOAD_BYTES` (default 25 MiB), `500` for a pipeline/transcription failure.

Sample request with `curl`:

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "file=@resource/audio smaples/audio_sample_1min.m4a"
```

Sample response:

```json
{
  "segments": [
    {"speaker": "SPEAKER_00", "text": "שלום וברוכים הבאים", "start": 0.008, "end": 2.531},
    {"speaker": "SPEAKER_01", "text": "תודה שאירחתם אותי", "start": 2.6, "end": 4.92},
    {"speaker": "UNKNOWN",    "text": "מוזיקת רקע",        "start": 4.92, "end": 5.4}
  ],
  "language": "he",
  "num_speakers": 2
}
```

Response schema:

| Field          | Type              | Notes                                                                 |
|----------------|-------------------|-----------------------------------------------------------------------|
| `segments`     | array of objects  | One entry per transcribed segment (see below). Ordered by start time. |
| `segments[].speaker` | string      | Speaker label, e.g. `SPEAKER_00`. `"UNKNOWN"` when no diarization segment overlapped this span. |
| `segments[].text`    | string      | Transcribed text for the segment.                                     |
| `segments[].start`   | float       | Segment start time, in seconds.                                       |
| `segments[].end`     | float       | Segment end time, in seconds.                                         |
| `language`     | string or null    | Detected/configured language code (e.g. `he`).                        |
| `num_speakers` | integer or null   | Number of distinct speaker labels found (excluding `"UNKNOWN"`); `null` if none could be determined. |

## Web UI

The service also serves a browser-based upload page so you can transcribe audio
without writing any client code.

Start the server (see [Run](#run)):

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open the page in a browser at `GET /`:

```
http://localhost:8000/
```

What it does:

- **Fully offline.** The page is a single self-contained `app/static/index.html`
  with all CSS and JS inlined — no CDNs, no Google Fonts, no remote assets, no
  libraries. It works with no internet connection (it only talks to this
  same-origin service). The clean, professional RTL Hebrew theme is plain inline
  CSS using the system font stack.
- **Upload an audio file** via file picker or drag-and-drop. Uploads are capped
  at **25 MiB** (`MAX_UPLOAD_BYTES`); larger files are rejected client-side with
  a Hebrew error before they are sent.
- **Listen to the uploaded file in the page.** As soon as you select (or drag in)
  a file — or feed in a recording — an inline audio player appears so you can play
  the audio back **before and after** transcribing. Playback is fully client-side:
  the player is fed a local object URL (`URL.createObjectURL`) of the selected
  file, so nothing is uploaded just to listen and it works with no network. The
  object URL is released when you pick a different file, clear the selection, or
  leave the page. This is separate from the recorder's own preview player, so an
  uploaded file and a recorded clip never clobber each other.
- **Record from your microphone** as an alternative to uploading a file. Use the
  in-page recorder to start/stop a recording, preview it with the built-in audio
  player, optionally **save (keep) the recording** to your computer as a local
  download, and **use the recording for transcription**. A used recording is fed
  into the *same* `POST /transcribe` flow as an uploaded file, so it is subject
  to the identical **25 MiB** limit and contract. Recording uses only the
  browser's built-in `getUserMedia` / `MediaRecorder` Web APIs — no libraries and
  no network. If the browser lacks microphone support or permission is denied,
  the recorder shows a Hebrew message and file upload still works.
- **RTL Hebrew results.** On success the transcript renders right-to-left, with
  segments grouped and labelled by speaker and per-segment timestamps shown as
  `mm:ss`. A header summary shows the detected `language` and the
  `num_speakers` count.
- **Rename a speaker (change a display name).** After a transcript renders, a
  small editable per-speaker legend lets you give each distinct speaker a custom
  name. A rename changes that speaker's **display name everywhere** — it applies
  **live** across the whole transcript and the legend, and resets when you
  transcribe a new recording. This does *not* move any turn from one speaker to
  another; it only relabels.
- **Reassign a turn (fix a wrong attribution).** Diarization sometimes credits a
  turn to the wrong person. To correct that, each turn has its own control that
  lets you **move that turn to a different speaker** — or to a brand-new speaker.
  This is distinct from renaming: renaming changes a speaker's *name*, whereas
  reassigning changes *which speaker a turn belongs to*. After a reassignment the
  transcript re-renders live (avatar, color, and name all update) while the
  **turn structure is preserved** — each turn stays its own block, so reassigning
  never merges turns together or unites their text. Any
  custom name you already gave a speaker still applies after a reassignment, since
  both features key off the same speaker identity. Reassignment is entirely
  client-side (it edits a working copy of the segments in the browser; no server
  round-trip) and resets when you transcribe a new recording.
- **Download as Markdown.** Export the transcript as a `.md` file with one click.
  The Markdown is generated entirely client-side (a `Blob` download — no server
  round-trip, no libraries) and reflects both your **renamed speaker names** and
  any **turn reassignments** at the time you click.

Under the hood the page POSTs the audio (uploaded or recorded) to the
same-origin `POST /transcribe` endpoint described above, so it respects the exact
same contract and limits.

## How to send audio

The `/transcribe` endpoint accepts audio as a `multipart/form-data` file upload
(FastAPI `UploadFile`). This is the recommended and idiomatic mechanism for
sending binary audio to the service, for four reasons:

1. **Payload efficiency.** `multipart/form-data` transmits the audio as raw
   bytes. Base64-encoding the same audio inside a JSON body inflates the payload
   by roughly 33% (4 encoded bytes per 3 source bytes) and adds CPU cost on both
   client and server to encode and decode. For a 1-minute sample that is minor,
   but for longer recordings the overhead grows linearly and is pure waste.

2. **Native streaming and large-file support.** `UploadFile` is backed by a
   spooled temporary file: small uploads stay in memory, larger ones spill to
   disk, so the whole file is never forced fully into RAM the way a base64 JSON
   string would be. This maps cleanly onto our pipeline, which needs the bytes
   written to a real file path anyway (`whisperx.load_audio()` takes a path and
   shells out to ffmpeg). Multipart lets us stream the upload straight to a
   temporary file and hand that path to whisperx.

3. **Idiomatic FastAPI.** `file: UploadFile` is the framework's first-class
   pattern for file intake: automatic content handling, filename/content-type
   metadata, and clean OpenAPI docs (a file-picker in `/docs`). It is the least
   surprising contract for any HTTP client (`curl -F`, `requests` `files=`,
   browsers).

4. **No SSRF / network-fetch surface.** Having the server fetch a
   client-supplied URL turns the service into an HTTP client against arbitrary
   destinations, which is a Server-Side Request Forgery (SSRF) risk — a caller
   could point it at internal/cloud-metadata endpoints — and adds timeout,
   retry, redirect, and content-type-validation concerns plus an unpredictable
   external dependency. A direct upload keeps the request self-contained and the
   trust boundary simple.

### Secondary options

- **base64-in-JSON** makes sense when the client genuinely cannot send multipart
  (e.g., a constrained JSON-only API gateway, a webhook integration, or an
  environment where every request must be a single JSON document), accepting the
  ~33% size penalty for protocol uniformity.
- **remote URL** makes sense when the audio is already hosted (e.g., in object
  storage / a signed S3 URL) so re-uploading bytes through the API is redundant,
  and especially in an async/queued architecture where a worker pulls the object
  out-of-band. That is out of scope for this single-process service, but it is
  the natural mechanism if it later grows a job queue. If adopted, it must be
  paired with URL allow-listing / egress controls to mitigate the SSRF concern
  above.

## Client example

[`client_example.py`](client_example.py) is a self-contained Python client that
POSTs an audio file to `/transcribe` as `multipart/form-data`, then prints the
returned segments as `[speaker] text` lines followed by the raw JSON.

**Start the server first** (see [Run](#run)), then in another terminal:

```bash
# Uses the default sample audio: resource/audio smaples/audio_sample_1min.m4a
uv run python client_example.py

# Or pass your own audio file and/or a custom server URL:
uv run python client_example.py /path/to/your/audio.m4a --url http://localhost:8000
```

Arguments:

- `audio` (positional, optional) — path to the audio file to transcribe.
  Defaults to `resource/audio smaples/audio_sample_1min.m4a`.
- `--url` (optional) — base URL of the transcription server. Defaults to
  `http://localhost:8000`.

The client probes `GET /health` first and prints a friendly message if the
server is not running. CPU transcription of even short audio can take a while,
so the client uses a generous request timeout.

## Hebrew transcript review skill

A Claude Code skill, **`hebrew-transcript-review`**, builds on this service: it
transcribes a Hebrew recording via the `ivrit-transcribe` MCP, walks the
transcript with you word by word to learn unfamiliar words (backed by a root-level
`VOCAB.md`), and writes an RTL transcript plus a Hebrew summary. See
[`.claude/skills/hebrew-transcript-review/README.md`](.claude/skills/hebrew-transcript-review/README.md).
It requires this FastAPI service to be running (see [Run](#run)).

## Offline model requirements

The service runs Hugging Face libraries in **offline mode** (`HF_HUB_OFFLINE=1`,
set automatically at import). It does **not** fetch diarization models over the
network. Before running, the local diarization model folder **must** be present:

```
models/pyannote-diarization/
├── config.yaml
├── embedding/
├── plda/
└── segmentation/
```

The path is configurable via `DIARIZATION_CONFIG` (default
`models/pyannote-diarization/config.yaml`). A relative value is resolved against
the repository root, so the server works regardless of the directory uvicorn is
launched from; an absolute path is honored as-is. If this folder is missing the
service will fail to load the diarization pipeline at startup.

## Configuration

All settings are read from **environment variables**, each with a default that
matches the reference pipeline. The app runs with **zero env vars set**. Copy
[`.env.example`](.env.example) to `.env` and edit to override any value.

| Env var              | Default                                     | Description                                                        |
|----------------------|---------------------------------------------|--------------------------------------------------------------------|
| `WHISPER_MODEL`      | `ivrit-ai/whisper-large-v3-turbo-ct2`       | Whisper model id (ctranslate2 / faster-whisper format).            |
| `DEVICE`             | `cpu`                                        | Compute device: `cpu` or `cuda`.                                   |
| `COMPUTE_TYPE`       | `int8`                                       | whisperx compute type (`int8` keeps CPU memory/latency low).       |
| `LANGUAGE`           | `he`                                         | Transcription language (ISO code); `he` = Hebrew.                  |
| `DIARIZATION_CONFIG` | `models/pyannote-diarization/config.yaml`    | Local pyannote diarization config; relative paths resolve against the repo root. |
| `MIN_SPEAKERS`       | `2`                                          | Minimum number of speakers the diarizer should assume.             |
| `BATCH_SIZE`         | `4`                                          | Batch size passed to `model.transcribe()`.                         |
| `MAX_UPLOAD_BYTES`   | `26214400` (25 MiB)                          | Reject uploads larger than this many bytes.                        |
| `HOST`               | `0.0.0.0`                                    | uvicorn bind host.                                                 |
| `PORT`               | `8000`                                       | uvicorn bind port.                                                 |
| `HF_HUB_OFFLINE`     | `1`                                          | Force Hugging Face libraries offline (`1` = offline). Exported at import time. |

## Project layout

```
app/
  config.py          # env-driven Settings (pydantic-settings) + offline flag export
  schemas.py         # Pydantic response models (Segment, TranscriptionResponse)
  transcription.py   # TranscriptionPipeline: load() once, transcribe(path) per request
  main.py            # FastAPI app, lifespan model loading, POST /transcribe, GET /health
client_example.py    # REST client example
.env.example         # every env var with its default
models/              # local offline diarization models (must be present)
resource/            # reference pipeline + sample audio (read-only knowledge)
```
