"""Small OpenAI-compatible Step client with strict JSON-only boundaries."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import requests

from .settings import Settings, load_settings


class LLMUnavailable(RuntimeError):
    pass


@dataclass
class StepClient:
    api_key: str
    model: str
    base_url: str
    connect_timeout_seconds: int = 10
    read_timeout_seconds: int = 90
    max_retries: int = 3
    session: requests.Session | None = None
    last_request_meta: dict[str, Any] | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "StepClient | None":
        if not settings.step_configured:
            return None
        return cls(
            api_key=settings.step_api_key.get_secret_value(),
            model=settings.step_model,
            base_url=settings.step_base_url.rstrip("/"),
            connect_timeout_seconds=settings.step_connect_timeout_seconds,
            read_timeout_seconds=settings.step_read_timeout_seconds,
            max_retries=settings.step_max_retries,
        )

    @classmethod
    def from_env(cls) -> "StepClient | None":
        return cls.from_settings(load_settings())

    def json_completion(self, system: str, user: str) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        session = self.session or requests.Session()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        started = time.perf_counter()
        response = None
        for attempt in range(self.max_retries + 1):
            try:
                response = session.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=(self.connect_timeout_seconds, self.read_timeout_seconds),
                )
            except requests.RequestException as exc:
                if attempt >= self.max_retries:
                    raise LLMUnavailable(f"Step API request failed: {exc.__class__.__name__}") from exc
                time.sleep(2 ** attempt)
                continue
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                break
            time.sleep(2 ** attempt)
        if response is None:
            raise LLMUnavailable("Step API request did not produce a response")
        try:
            body = response.json()
        except ValueError:
            body = None
        request_id = (
            response.headers.get("x-request-id")
            or response.headers.get("request-id")
            or (body.get("id") if isinstance(body, dict) else None)
        )
        self.last_request_meta = {
            "model": self.model,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "request_id": request_id,
            "status_code": response.status_code,
        }
        if response.status_code >= 400:
            suffix = f" (request_id={request_id})" if request_id else ""
            raise LLMUnavailable(f"Step API returned HTTP {response.status_code}{suffix}")
        try:
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMUnavailable("Step API did not return valid JSON") from exc
