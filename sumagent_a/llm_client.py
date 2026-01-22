from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    base_url: str
    model: str
    max_output_tokens: int
    temperature: float
    timeout_s: int


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def summarize(self, prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_s) as response:
            body = response.read()
        parsed = json.loads(body)
        return parsed["choices"][0]["message"]["content"]


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def summarize(self, prompt: str) -> str:
        self.calls.append(prompt)
        return json.dumps(
            {
                "schema": "FileSummary.v1",
                "relative_path": "unknown",
                "file_hash_sha256": "",
                "size_bytes": 0,
                "language": "unknown",
                "purpose": "Stub summary.",
                "key_entities": [],
                "public_entrypoints": [],
                "external_dependencies": [],
                "configs_env": [],
                "errors_and_exceptions": [],
                "todo_fixme": [],
                "risks": [],
                "evidence": [],
                "generated_at": "",
            }
        )
