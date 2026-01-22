from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class RunMetrics:
    files_total: int = 0
    files_summarized: int = 0
    files_skipped_cached: int = 0
    files_skipped_excluded: int = 0
    errors_count: int = 0
    llm_calls_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_total": self.files_total,
            "files_summarized": self.files_summarized,
            "files_skipped_cached": self.files_skipped_cached,
            "files_skipped_excluded": self.files_skipped_excluded,
            "errors_count": self.errors_count,
            "llm_calls_count": self.llm_calls_count,
        }


@dataclass
class RunLogger:
    out_dir: Path
    run_id: str = field(default_factory=lambda: str(uuid4()))
    metrics: RunMetrics = field(default_factory=RunMetrics)
    records: list[dict[str, Any]] = field(default_factory=list)

    def log(
        self,
        *,
        level: str,
        event: str,
        relative_path: str | None,
        message: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            "timestamp": timestamp,
            "run_id": self.run_id,
            "level": level,
            "event": event,
            "relative_path": relative_path,
            "message": message,
            "metrics": metrics or {},
        }
        self.records.append(record)

    def flush(self) -> Path:
        runs_dir = self.out_dir / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        run_path = runs_dir / f"{self.run_id}.jsonl"
        with run_path.open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return run_path
