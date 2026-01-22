from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class RunMetrics:
    modules_total: int = 0
    modules_dirty: int = 0
    modules_built: int = 0
    views_total: int = 0
    views_dirty: int = 0
    views_built: int = 0
    errors_count: int = 0
    llm_calls_count: int = 0


@dataclass
class RunLogger:
    out_dir: Path
    run_id: str = field(default_factory=lambda: str(uuid4()))
    log_path: Path | None = None
    metrics: RunMetrics = field(default_factory=RunMetrics)

    def __post_init__(self) -> None:
        runs_dir = self.out_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = runs_dir / f"{self.run_id}.jsonl"

    def log(
        self,
        *,
        level: str,
        event: str,
        scope: str,
        id: str,
        message: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        if self.log_path is None:
            return
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "level": level,
            "event": event,
            "scope": scope,
            "id": id,
            "message": message,
            "metrics": metrics or {},
        }
        self.log_path.write_text(
            (self.log_path.read_text(encoding="utf-8") if self.log_path.exists() else "")
            + json.dumps(payload, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    def info(self, *, event: str, scope: str, id: str, message: str, metrics: dict[str, Any] | None = None) -> None:
        self.log(level="info", event=event, scope=scope, id=id, message=message, metrics=metrics)

    def warning(self, *, event: str, scope: str, id: str, message: str, metrics: dict[str, Any] | None = None) -> None:
        self.log(level="warning", event=event, scope=scope, id=id, message=message, metrics=metrics)

    def error(self, *, event: str, scope: str, id: str, message: str, metrics: dict[str, Any] | None = None) -> None:
        self.metrics.errors_count += 1
        self.log(level="error", event=event, scope=scope, id=id, message=message, metrics=metrics)
