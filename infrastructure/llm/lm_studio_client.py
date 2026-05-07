import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class LMStudioClient:
    """Pure HTTP transport for LM Studio (OpenAI-compatible chat endpoint).

    Knows nothing about transcription quality or prompt content.
    Call chat() with pre-built messages; get back the raw assistant text.
    """

    base_url: str
    model: str
    timeout_s: int = 45
    temperature: float = 0.0
    max_tokens: int = 300

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send messages and return the assistant reply text.

        Raises RuntimeError on network or HTTP failure.
        """
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        try:
            response_data = self._post_json(payload)
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        return (
            response_data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw)
