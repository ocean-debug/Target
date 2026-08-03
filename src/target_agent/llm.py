"""Small OpenAI-compatible Step client with strict JSON-only boundaries."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests


class LLMUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class StepClient:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: int = 45

    @classmethod
    def from_env(cls) -> "StepClient | None":
        api_key = os.getenv("STEP_API_KEY", "").strip()
        model = os.getenv("STEP_MODEL", "").strip()
        if not api_key or not model:
            return None
        return cls(
            api_key=api_key,
            model=model,
            base_url=os.getenv("STEP_BASE_URL", "https://api.stepfun.com/v1").rstrip("/"),
            timeout_seconds=int(os.getenv("STEP_TIMEOUT_SECONDS", "45")),
        )

    def json_completion(self, system: str, user: str) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise LLMUnavailable(f"Step API returned HTTP {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMUnavailable("Step API did not return valid JSON") from exc

