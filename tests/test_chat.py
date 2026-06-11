"""Tests for app.chat — transcript flattening + chat-completion client."""
import app.chat as chat
from app.chat import ChatCompletionClient, build_transcript_text
from app.config import Settings


def test_build_transcript_text_flattens_speaker_lines():
    segs = [
        {"speaker": "SPEAKER_00", "text": " שלום ", "start": 0, "end": 1},
        {"speaker": "SPEAKER_01", "text": "תודה", "start": 1, "end": 2},
        {"speaker": "SPEAKER_00", "text": "   ", "start": 2, "end": 3},  # blank dropped
    ]
    out = build_transcript_text(segs)
    assert out == "SPEAKER_00: שלום\nSPEAKER_01: תודה"


def test_dummy_used_when_no_api_url():
    client = ChatCompletionClient(Settings(_env_file=None, CHAT_API_URL=""))
    answer, model = client.complete("סכם בבקשה", "SPEAKER_00: שלום")
    assert model == chat.DUMMY_MODEL
    assert isinstance(answer, str) and answer.strip()
    # The dummy echoes the user's instruction so the round-trip is visible.
    assert "סכם בבקשה" in answer


def test_remote_path_calls_openai_compatible_endpoint(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "TheAnswer"}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResp()

    monkeypatch.setattr(chat.httpx, "post", fake_post)
    client = ChatCompletionClient(
        Settings(
            _env_file=None,
            CHAT_API_URL="https://api.example/v1/chat/completions",
            CHAT_API_KEY="sk-test",
            CHAT_MODEL="gpt-4o-mini",
        )
    )
    answer, model = client.complete("summarize", "SPEAKER_00: hi")
    assert answer == "TheAnswer"
    assert model == "gpt-4o-mini"
    assert captured["url"] == "https://api.example/v1/chat/completions"
    assert captured["json"]["model"] == "gpt-4o-mini"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    # The system + user messages are present and carry the transcript.
    roles = [m["role"] for m in captured["json"]["messages"]]
    assert roles == ["system", "user"]
    assert "SPEAKER_00: hi" in captured["json"]["messages"][1]["content"]
