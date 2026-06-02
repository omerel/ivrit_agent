"""Offline / contract guard tests for the served index.html.

These assertions protect three guarantees of the static page:
  1. It is fully offline — no remote references of any kind.
  2. The upload is wired to the same-origin POST /transcribe via a file input.
  3. The document root is RTL Hebrew (lang="he" dir="rtl").

Like tests/test_main.py and tests/test_web.py, we build TestClient(main.app)
directly (no context manager) so the lifespan/model load never runs. These are
pure static-string/regex assertions against the HTML returned by GET / — no
browser, no pipeline.
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


def test_index_has_no_remote_references():
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
            f"served index.html must be fully offline but matched {pattern!r}: "
            f"{match.group(0)!r}"
        )


def test_index_wires_file_upload_to_transcribe():
    body = _index_html()
    assert "/transcribe" in body
    assert 'type="file"' in body


def test_index_root_html_tag_is_rtl_hebrew():
    body = _index_html()
    match = re.search(r"<html\b[^>]*>", body)
    assert match is not None, "served index.html must contain an <html ...> tag"
    html_tag = match.group(0)
    assert 'lang="he"' in html_tag, f'<html> tag missing lang="he": {html_tag!r}'
    assert 'dir="rtl"' in html_tag, f'<html> tag missing dir="rtl": {html_tag!r}'
