"""Tests for the static offline web page served by app.main.

These routes (GET / and the /static mount) must not trigger a real model load,
so we mirror tests/test_main.py: build TestClient(main.app) directly (no context
manager, so the lifespan/model load never runs) and never touch the pipeline.
"""
from fastapi.testclient import TestClient

import app.main as main


def test_index_returns_html_with_rtl_and_transcribe():
    client = TestClient(main.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert 'dir="rtl"' in resp.text
    assert "/transcribe" in resp.text


def test_static_index_html_served():
    client = TestClient(main.app)
    resp = client.get("/static/index.html")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
