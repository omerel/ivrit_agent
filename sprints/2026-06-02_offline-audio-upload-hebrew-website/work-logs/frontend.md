# Work Log — @frontend

## 2026-06-02T10:33:00Z — Task T3

**Task:** T3 — Build the beautiful offline RTL Hebrew upload + transcript UI in `app/static/index.html`.

**What was done:**
- Invoked the `frontend-design` skill before writing any markup. Chosen direction: an
  "editorial / archival broadcast-studio" aesthetic — deep warm-charcoal ink background,
  warm amber/ember accents, parchment-toned text, a serif display face (system serif stack)
  paired with a system sans body, a subtle CSS-only paper-grain overlay, and an animated
  audio-waveform loading state. Distinctiveness comes entirely from color/layout/motion/
  texture because the offline hard requirement forbids any web fonts.
- Replaced the T2 placeholder `app/static/index.html` with a single self-contained page:
  all CSS in one `<style>` block, all JS in one `<script>` block, **zero** remote refs.
  Fonts via a Hebrew-friendly system stack only. All icons are inline SVG.
- Preserved the contract literals: `<html lang="he" dir="rtl">` and the string `/transcribe`
  (the fetch target, relative URL, multipart field name `file`).
- Functionality implemented:
  - Upload via BOTH file picker and drag-and-drop; selected filename + human-readable size
    shown in a filebar with a clear/remove button.
  - Client-side guard: empty files and files > 25 MiB (`MAX_UPLOAD_BYTES = 26214400`) are
    blocked BEFORE sending, each with a specific Hebrew error.
  - Submit POSTs `multipart/form-data` (field `file`) to relative `/transcribe` via `fetch`,
    with a reassuring animated loading state and a live elapsed-time clock.
  - On 200: header summary of `language` and `num_speakers` (both null-safe, shown as "—"),
    plus a segment count. Segments grouped into consecutive-speaker "turns", each labelled
    with a Hebrew speaker name (SPEAKER_00 → "דובר/ת 1", UNKNOWN/null → "דובר/ת לא מזוהה"),
    a per-color avatar/rail, an mm:ss–mm:ss range, and RTL Hebrew text (HTML-escaped).
  - On HTTP 4xx/5xx: shows the server `{detail}` (or a generic Hebrew fallback) in a friendly
    error panel — no stack traces. Network failure and unparseable-JSON have dedicated Hebrew
    messages.
  - Accessibility: dropzone is keyboard-operable (role=button, Enter/Space), aria-live regions
    for loading/results/alert, and `prefers-reduced-motion` disables animations.
- Replaced an inline SVG noise `data:` URI with a pure-CSS grain texture so the mandated grep
  (which also matches the SVG xmlns `http://...` namespace) returns clean.

**Files touched:** `app/static/index.html` (only this file staged for commit);
`sprints/2026-06-02_offline-audio-upload-hebrew-website/work-logs/frontend.md`.

**Grep result (mandatory offline check):**
`grep -nE "https?:|//cdn|fonts.googleapis|fonts.gstatic|<script src|<link " app/static/index.html`
→ returned **nothing** (exit code 1). No remote refs, no external `<link>`/`<script src>`.
Confirmed preserved strings: `lang="he"` ×1, `dir="rtl"` ×1, `/transcribe` ×2.

**Pytest result:**
`python -m pytest tests/test_web.py -v` → **2 passed** in 4.13s
(`test_index_returns_html_with_rtl_and_transcribe`, `test_static_index_html_served`).

**Browser verification (not just type/string checks):**
Rendered the page in headless Google Chrome against a local fake `/transcribe` returning the
real JSON contract (incl. an `UNKNOWN` speaker and a segment past 60s). Captured screenshots:
- `/tmp/ivrit_initial.png` — initial upload card (clean dropzone, masthead, RTL).
- `/tmp/ivrit_results.png` — after upload: filebar shows `ישיבת_צוות.mp3 · 1.0 ק״ב`;
  summary שפה `he` / מספר דוברים `2` / מקטעים `4`; transcript grouped by speaker with
  colored rails (דובר/ת 1 amber, דובר/ת 2 blue, דובר/ת לא מזוהה purple) and mm:ss ranges
  incl. `01:19 – 01:15` confirming >60s mm:ss formatting; Hebrew RTL text renders correctly.
The loading state and oversize-file error path were also exercised in the same driven session.
(Temp screenshots and the throwaway fake server were cleaned up after verification.)

**Blockers:** none.
