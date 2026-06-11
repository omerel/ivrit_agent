"""Chat-completion client used by the ``/summarize`` endpoint.

When ``CHAT_API_URL`` is configured the client POSTs an OpenAI-compatible
chat-completion request to it; otherwise it returns a deterministic **dummy**
answer so the summarize feature works end-to-end with no external LLM service
configured (the chat backend can be wired in later by setting the env vars).
"""
import logging

import httpx

from app.config import Settings, settings as default_settings

logger = logging.getLogger("ivrit_agent")

DUMMY_MODEL = "dummy"

_SYSTEM_PROMPT = (
    "You are a helpful assistant. The user gives a request and a transcript of a "
    "conversation. Answer the request based on the transcript, replying in the "
    "same language as the transcript."
)


def build_transcript_text(segments: list[dict]) -> str:
    """Flatten transcription segments into ``"Speaker: text"`` lines.

    Blank segments are skipped and surrounding whitespace trimmed so the prompt
    sent to the chat model is compact.
    """
    lines = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        speaker = seg.get("speaker") or "?"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


class ChatCompletionClient:
    """Sends a request + transcript to a chat-completion API (or a dummy)."""

    def __init__(self, settings: Settings = default_settings):
        self.settings = settings

    def complete(self, instruction: str, transcript_text: str) -> tuple[str, str]:
        """Return ``(answer, model)`` for ``instruction`` over ``transcript_text``."""
        user = f"{instruction}\n\n---\nTranscript:\n{transcript_text}"
        if not self.settings.CHAT_API_URL:
            return self._dummy(instruction, transcript_text), DUMMY_MODEL
        return self._remote(_SYSTEM_PROMPT, user), self.settings.CHAT_MODEL

    def _remote(self, system: str, user: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.settings.CHAT_API_KEY:
            headers["Authorization"] = f"Bearer {self.settings.CHAT_API_KEY}"
        payload = {
            "model": self.settings.CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        resp = httpx.post(
            self.settings.CHAT_API_URL,
            json=payload,
            headers=headers,
            timeout=self.settings.CHAT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _dummy(self, instruction: str, transcript_text: str) -> str:
        """A canned, network-free answer that reflects the inputs.

        Deterministic so it is easy to test and obviously a placeholder.
        """
        lines = [ln for ln in transcript_text.splitlines() if ln.strip()]
        speakers = {ln.split(":", 1)[0] for ln in lines if ":" in ln}
        words = sum(len(ln.split(":", 1)[-1].split()) for ln in lines)
        return (
            "[תשובת הדגמה — לא חובר מנוע צ׳אט אמיתי]\n"
            f"בקשה: {instruction}\n"
            f"התמלול כולל {len(lines)} מקטעים, {len(speakers)} דוברים ו־{words} מילים בקירוב.\n"
            "כדי לקבל סיכום אמיתי, הגדירו CHAT_API_URL ו־CHAT_API_KEY."
        )
