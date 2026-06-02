"""Static-string guard tests for the four sprint features in the served page.

This sprint added four things to the single self-contained offline page
(`app/static/index.html`): a more professional theme, in-browser audio
recording, post-transcription speaker renaming, and client-side Markdown
export. These tests lock in the *markers* of features 2-4 (and re-assert the
offline + contract invariants against the new markup) so a future edit cannot
silently drop a feature or reintroduce a remote reference.

Like tests/test_main.py, tests/test_web.py and tests/test_web_offline.py, we
build TestClient(main.app) directly (no context manager) so the lifespan/model
load never runs. These are pure static-string assertions against the HTML
returned by GET / — no browser, no pipeline, no model.

Only stable IDs / inlined-script tokens that were confirmed present in the
shipped index.html are asserted here; CSS / visual details are intentionally
NOT asserted (too brittle).
"""
import re

from fastapi.testclient import TestClient

import app.main as main


def _index_html() -> str:
    client = TestClient(main.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    return resp.text


# --- Offline + contract invariants re-asserted against the new markup --------

def test_index_still_offline_after_feature_work():
    body = _index_html()
    forbidden = [
        r"https?://",
        r"fonts\.googleapis",
        r"fonts\.gstatic",
        r"//cdn",
    ]
    for pattern in forbidden:
        match = re.search(pattern, body)
        assert match is None, (
            f"served index.html must stay fully offline but matched "
            f"{pattern!r}: {match.group(0)!r}"
        )


def test_index_still_has_contract_invariants():
    body = _index_html()
    assert '<html lang="he" dir="rtl">' in body
    assert "/transcribe" in body
    assert 'type="file"' in body


# --- Feature 2: in-browser audio recording ----------------------------------

def test_record_panel_controls_present():
    body = _index_html()
    for marker in (
        'id="recordPanel"',
        'id="recordBtn"',
        'id="stopBtn"',
        'id="recPreview"',
        'id="recSave"',
        'id="recUse"',
        'id="recStatus"',
    ):
        assert marker in body, f"record control marker missing: {marker}"


def test_record_uses_browser_media_apis():
    body = _index_html()
    assert "getUserMedia" in body, "record feature must reference getUserMedia"
    assert "MediaRecorder" in body, "record feature must reference MediaRecorder"


# --- Feature 3: post-transcription speaker renaming -------------------------

def test_speaker_rename_legend_present():
    body = _index_html()
    assert 'id="speakerLegend"' in body, "speaker-rename legend container missing"
    assert "speakerNames" in body, "speaker-rename state token missing"


# --- Feature 4: client-side Markdown export ---------------------------------

def test_markdown_download_present():
    body = _index_html()
    assert 'id="downloadMdBtn"' in body, "Markdown download button missing"
    assert "text/markdown" in body, "Markdown export must build a text/markdown blob"
