from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SourceConfig:
    type: str
    name: str
    path: Path
    # SQLite-specific fields
    table: Optional[str] = None
    content_column: Optional[str] = None
    metadata_columns: list[str] = field(default_factory=list)


@dataclass
class EmbeddingConfig:
    backend: str = "local"
    model: str = "all-MiniLM-L6-v2"
    api_key: Optional[str] = None


@dataclass
class Config:
    sources: list[SourceConfig]
    embedding: EmbeddingConfig


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    sources = []
    for i, src in enumerate(raw.get("sources", [])):
        try:
            sources.append(SourceConfig(
                type=src["type"],
                name=src["name"],
                path=Path(src["path"]).expanduser(),
                table=src.get("table"),
                content_column=src.get("content_column"),
                metadata_columns=src.get("metadata_columns", []),
            ))
        except KeyError as e:
            raise ValueError(
                f"Source entry {i} in {path} is missing required field: {e}"
            ) from e

    emb_raw = raw.get("embedding", {})
    embedding = EmbeddingConfig(
        backend=emb_raw.get("backend", "local"),
        model=emb_raw.get("model", "all-MiniLM-L6-v2"),
        api_key=emb_raw.get("api_key"),
    )

    return Config(sources=sources, embedding=embedding)


def default_config_path() -> Path:
    return Path("~/.config/lake-of-embeddings/config.yaml").expanduser()
