from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


Language = Literal[
    "python",
    "java",
    "kotlin",
    "js",
    "ts",
    "yaml",
    "json",
    "toml",
    "md",
    "sql",
    "shell",
    "other",
    "unknown",
]


@dataclass(frozen=True)
class FileSummary:
    schema: str
    relative_path: str
    file_hash_sha256: str
    size_bytes: int
    language: Language
    purpose: str
    key_entities: list[str]
    public_entrypoints: list[dict[str, Any]]
    external_dependencies: list[str]
    configs_env: list[str]
    errors_and_exceptions: list[str]
    todo_fixme: list[str]
    risks: list[str]
    evidence: list[dict[str, str]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "relative_path": self.relative_path,
            "file_hash_sha256": self.file_hash_sha256,
            "size_bytes": self.size_bytes,
            "language": self.language,
            "purpose": self.purpose,
            "key_entities": self.key_entities,
            "public_entrypoints": self.public_entrypoints,
            "external_dependencies": self.external_dependencies,
            "configs_env": self.configs_env,
            "errors_and_exceptions": self.errors_and_exceptions,
            "todo_fixme": self.todo_fixme,
            "risks": self.risks,
            "evidence": self.evidence,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class DirSummary:
    schema: str
    relative_path: str
    dir_hash_sha256: str
    purpose: str
    contents_overview: str
    key_components: list[str]
    entrypoints: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "relative_path": self.relative_path,
            "dir_hash_sha256": self.dir_hash_sha256,
            "purpose": self.purpose,
            "contents_overview": self.contents_overview,
            "key_components": self.key_components,
            "entrypoints": self.entrypoints,
            "generated_at": self.generated_at,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_empty_file_summary(
    *,
    relative_path: str,
    file_hash_sha256: str,
    size_bytes: int,
    language: Language,
    purpose: str,
) -> FileSummary:
    return FileSummary(
        schema="FileSummary.v1",
        relative_path=relative_path,
        file_hash_sha256=file_hash_sha256,
        size_bytes=size_bytes,
        language=language,
        purpose=purpose,
        key_entities=[],
        public_entrypoints=[],
        external_dependencies=[],
        configs_env=[],
        errors_and_exceptions=[],
        todo_fixme=[],
        risks=[],
        evidence=[],
        generated_at=utc_now_iso(),
    )


def build_empty_dir_summary(
    *,
    relative_path: str,
    dir_hash_sha256: str,
    purpose: str,
    contents_overview: str,
) -> DirSummary:
    return DirSummary(
        schema="DirSummary.v1",
        relative_path=relative_path,
        dir_hash_sha256=dir_hash_sha256,
        purpose=purpose,
        contents_overview=contents_overview,
        key_components=[],
        entrypoints=[],
        generated_at=utc_now_iso(),
    )
