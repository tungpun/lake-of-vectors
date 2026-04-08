import pytest
from pathlib import Path
from lake_of_vectors.config import load_config, Config, SourceConfig, EmbeddingConfig


def test_load_config_from_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
sources:
  - type: markdown
    name: my-notes
    path: /tmp/notes

embedding:
  backend: local
  model: all-MiniLM-L6-v2
""")
    config = load_config(config_file)
    assert isinstance(config, Config)
    assert len(config.sources) == 1
    assert config.sources[0].type == "markdown"
    assert config.sources[0].name == "my-notes"
    assert config.sources[0].path == Path("/tmp/notes")
    assert config.embedding.backend == "local"
    assert config.embedding.model == "all-MiniLM-L6-v2"


def test_load_config_sqlite_source(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
sources:
  - type: sqlite
    name: knowledge-db
    path: /tmp/knowledge.db
    table: notes
    content_column: body
    metadata_columns: [title, tags]

embedding:
  backend: local
  model: all-MiniLM-L6-v2
""")
    config = load_config(config_file)
    src = config.sources[0]
    assert src.type == "sqlite"
    assert src.table == "notes"
    assert src.content_column == "body"
    assert src.metadata_columns == ["title", "tags"]


def test_load_config_expands_tilde(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
sources:
  - type: plaintext
    name: notes
    path: ~/notes

embedding:
  backend: local
  model: all-MiniLM-L6-v2
""")
    config = load_config(config_file)
    assert config.sources[0].path == Path.home() / "notes"


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


def test_load_config_default_embedding(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
sources:
  - type: markdown
    name: notes
    path: /tmp/notes
""")
    config = load_config(config_file)
    assert config.embedding.backend == "local"
    assert config.embedding.model == "all-MiniLM-L6-v2"


def test_load_config_openai_embedding(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
sources:
  - type: markdown
    name: notes
    path: /tmp/notes

embedding:
  backend: openai
  model: text-embedding-3-small
  api_key: sk-test-key
""")
    config = load_config(config_file)
    assert config.embedding.backend == "openai"
    assert config.embedding.api_key == "sk-test-key"
