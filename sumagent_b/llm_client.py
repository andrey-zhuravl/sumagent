from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import request


@dataclass
class LLMConfig:
    base_url: str
    model: str
    temperature: float = 0.2
    max_output_tokens: int = 1200
    timeout_s: int = 240


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.calls = 0

    def summarize(self, prompt: str) -> str:
        self.calls += 1
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            "messages": [
                {"role": "system", "content": "Ты помощник, который пишет проектные резюме."},
                {"role": "user", "content": prompt},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.config.base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=self.config.timeout_s) as response:
            body = response.read()
        decoded = json.loads(body.decode("utf-8"))
        return decoded["choices"][0]["message"]["content"]


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    def summarize(self, prompt: str) -> str:
        self.calls += 1
        return (
            "# Summary\n\n"
            "## Purpose\nunknown\n\n"
            "## Key Components\n- unknown\n\n"
            "## Entrypoints\n- unknown\n\n"
            "## Configs/Env\n- unknown\n\n"
            "## Data/Flow\n- unknown\n\n"
            "## Errors/Resilience\n- unknown\n\n"
            "## Risks\n- unknown\n\n"
            "## key_files\n- unknown\n"
        )
