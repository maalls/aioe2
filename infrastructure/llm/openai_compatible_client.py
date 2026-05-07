import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass
class OpenAICompatibleClient:
    base_url: str
    model: str
    api_key: str = ""
    timeout_s: int = 120

    def __post_init__(self) -> None:
        self.base_url = self.base_url.strip()
        self.model = self.model.strip()
        if not self.base_url:
            raise ValueError("LLM base_url is required")
        if not self.model:
            raise ValueError("LLM model is required")

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        body = json.dumps(payload).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(endpoint, data=body, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"LLM connection error: {exc}") from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError("Unexpected LLM response format") from exc

        content = _strip_json_code_fence(content)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM did not return valid JSON") from exc


def _strip_json_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return text
