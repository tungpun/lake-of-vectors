# Lake of Embeddings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local semantic search platform that indexes Obsidian notes, SQLite databases, and plaintext files into ChromaDB, exposed to Claude via an MCP server.

**Architecture:** Single Python package with four modules: publishers (crawl sources), sync engine (diff/chunk/embed/upsert), embedding backends (pluggable local/API), and MCP server (stdio, two tools). ChromaDB on-disk for storage.

**Tech Stack:** Python 3.10+, ChromaDB, sentence-transformers, MCP SDK (FastMCP), click, PyYAML, uv

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, `[project.scripts]` entry point |
| `config.example.yaml` | Example configuration |
| `src/lake_of_vectors/__init__.py` | Package version |
| `src/lake_of_vectors/config.py` | Load and validate YAML config |
| `src/lake_of_vectors/publishers/base.py` | `Document` dataclass, `Publisher` protocol |
| `src/lake_of_vectors/publishers/markdown.py` | `MarkdownPublisher` |
| `src/lake_of_vectors/publishers/plaintext.py` | `PlaintextPublisher` |
| `src/lake_of_vectors/publishers/sqlite.py` | `SqlitePublisher` |
| `src/lake_of_vectors/embeddings/base.py` | `Embedder` protocol |
| `src/lake_of_vectors/embeddings/local.py` | `LocalEmbedder` (sentence-transformers) |
| `src/lake_of_vectors/embeddings/api.py` | `APIEmbedder` (OpenAI) |
| `src/lake_of_vectors/sync/chunker.py` | Recursive text splitter |
| `src/lake_of_vectors/sync/engine.py` | Sync orchestrator (diff, chunk, embed, upsert) |
| `src/lake_of_vectors/mcp/server.py` | MCP server with `semantic_search` and `list_sources` |
| `src/lake_of_vectors/cli.py` | CLI commands (`sync`, `serve`, `status`) |
| `tests/test_config.py` | Config loading tests |
| `tests/publishers/test_markdown.py` | MarkdownPublisher tests |
| `tests/publishers/test_plaintext.py` | PlaintextPublisher tests |
| `tests/publishers/test_sqlite.py` | SqlitePublisher tests |
| `tests/test_chunker.py` | Chunker tests |
| `tests/test_engine.py` | Sync engine tests |
| `tests/test_mcp_server.py` | MCP server tool tests |
| `tests/test_cli.py` | CLI integration tests |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/lake_of_vectors/__init__.py`
- Create: `config.example.yaml`
- Create: all `__init__.py` files for subpackages

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lake-of-vectors"
version = "0.1.0"
description = "Local semantic search over personal knowledge bases"
requires-python = ">=3.10"
dependencies = [
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "mcp>=1.26.0",
    "click>=8.0.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
openai = ["openai>=1.0.0"]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.24.0"]

[project.scripts]
lake = "lake_of_vectors.cli:cli"
```

- [ ] **Step 2: Create package init**

```python
# src/lake_of_vectors/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 3: Create all __init__.py files**

Create empty `__init__.py` in:
- `src/lake_of_vectors/publishers/__init__.py`
- `src/lake_of_vectors/embeddings/__init__.py`
- `src/lake_of_vectors/sync/__init__.py`
- `src/lake_of_vectors/mcp/__init__.py`
- `tests/__init__.py`
- `tests/publishers/__init__.py`

- [ ] **Step 4: Create config.example.yaml**

```yaml
sources:
  - type: markdown
    name: security-notes
    path: ~/obsidian-vault/32.01. Security/
  - type: sqlite
    name: knowledge-db
    path: ~/knowledge.db
    table: notes
    content_column: body
    metadata_columns: [title, tags, created_at]
  - type: plaintext
    name: misc-notes
    path: ~/notes/

embedding:
  backend: local
  model: all-MiniLM-L6-v2
```

- [ ] **Step 5: Initialize git and install**

```bash
cd /Users/tungpun/Desktop/repos/lake-of-vectors && \
  git init && \
  uv pip install -e ".[dev]"
```

- [ ] **Step 6: Verify installation**

Run: `lake --help`
Expected: Will fail (cli.py doesn't exist yet), but the package should be importable:
```bash
python -c "import lake_of_vectors; print(lake_of_vectors.__version__)"
```
Expected output: `0.1.0`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml config.example.yaml src/ tests/ && \
  git commit -m "feat: scaffold project structure"
```

---

### Task 2: Config Loading

**Files:**
- Create: `src/lake_of_vectors/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config loading**

```python
# tests/test_config.py
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
    assert "~" not in str(config.sources[0].path)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lake_of_vectors.config'`

- [ ] **Step 3: Implement config.py**

```python
# src/lake_of_vectors/config.py
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

    sources = []
    for src in raw.get("sources", []):
        sources.append(SourceConfig(
            type=src["type"],
            name=src["name"],
            path=Path(src["path"]).expanduser(),
            table=src.get("table"),
            content_column=src.get("content_column"),
            metadata_columns=src.get("metadata_columns", []),
        ))

    emb_raw = raw.get("embedding", {})
    embedding = EmbeddingConfig(
        backend=emb_raw.get("backend", "local"),
        model=emb_raw.get("model", "all-MiniLM-L6-v2"),
        api_key=emb_raw.get("api_key"),
    )

    return Config(sources=sources, embedding=embedding)


def default_config_path() -> Path:
    return Path("~/.config/lake-of-vectors/config.yaml").expanduser()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/config.py tests/test_config.py && \
  git commit -m "feat: add config loading with YAML parsing"
```

---

### Task 3: Publisher Base and MarkdownPublisher

**Files:**
- Create: `src/lake_of_vectors/publishers/base.py`
- Create: `src/lake_of_vectors/publishers/markdown.py`
- Create: `tests/publishers/test_markdown.py`

- [ ] **Step 1: Create the base module**

```python
# src/lake_of_vectors/publishers/base.py
from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable
import hashlib


@dataclass
class Document:
    source_id: str
    content: str
    metadata: dict
    content_hash: str


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@runtime_checkable
class Publisher(Protocol):
    def crawl(self) -> Iterator[Document]:
        ...
```

- [ ] **Step 2: Write failing tests for MarkdownPublisher**

```python
# tests/publishers/test_markdown.py
import pytest
from pathlib import Path
from lake_of_vectors.publishers.markdown import MarkdownPublisher
from lake_of_vectors.publishers.base import Document, compute_hash


def test_crawl_finds_markdown_files(tmp_path):
    (tmp_path / "note1.md").write_text("# Hello\nThis is note 1.")
    (tmp_path / "note2.md").write_text("# World\nThis is note 2.")
    (tmp_path / "readme.txt").write_text("Not a markdown file.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)


def test_crawl_recursive(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    (tmp_path / "root.md").write_text("Root note.")
    (sub / "nested.md").write_text("Nested note.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2


def test_document_source_id_is_absolute_path(tmp_path):
    (tmp_path / "note.md").write_text("Content here.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].source_id == str(tmp_path / "note.md")


def test_document_content_hash(tmp_path):
    content = "# Test\nSome content."
    (tmp_path / "note.md").write_text(content)

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].content_hash == compute_hash(content)


def test_document_metadata_has_title_from_h1(tmp_path):
    (tmp_path / "note.md").write_text("# My Title\nBody text.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["title"] == "My Title"


def test_document_metadata_title_fallback_to_filename(tmp_path):
    (tmp_path / "note.md").write_text("No heading here, just text.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["title"] == "note"


def test_document_metadata_has_relative_path(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    (sub / "deep.md").write_text("# Deep\nContent.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["relative_path"] == "a/b/deep.md"


def test_crawl_empty_directory(tmp_path):
    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())
    assert docs == []


def test_crawl_skips_empty_files(tmp_path):
    (tmp_path / "empty.md").write_text("")
    (tmp_path / "real.md").write_text("Has content.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 1
    assert docs[0].metadata["title"] == "real"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/publishers/test_markdown.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement MarkdownPublisher**

```python
# src/lake_of_vectors/publishers/markdown.py
import re
from pathlib import Path
from typing import Iterator

from .base import Document, Publisher, compute_hash


class MarkdownPublisher:
    def __init__(self, path: Path):
        self.path = Path(path)

    def crawl(self) -> Iterator[Document]:
        for md_file in sorted(self.path.rglob("*.md")):
            if not md_file.is_file():
                continue
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                continue

            title = self._extract_title(content, md_file)
            relative_path = str(md_file.relative_to(self.path))

            yield Document(
                source_id=str(md_file),
                content=content,
                metadata={
                    "title": title,
                    "relative_path": relative_path,
                    "directory": str(md_file.parent.relative_to(self.path))
                    if md_file.parent != self.path
                    else "",
                },
                content_hash=compute_hash(content),
            )

    def _extract_title(self, content: str, file_path: Path) -> str:
        match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return file_path.stem
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/publishers/test_markdown.py -v`
Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/lake_of_vectors/publishers/base.py \
  src/lake_of_vectors/publishers/markdown.py \
  tests/publishers/test_markdown.py && \
  git commit -m "feat: add Document model and MarkdownPublisher"
```

---

### Task 4: PlaintextPublisher

**Files:**
- Create: `src/lake_of_vectors/publishers/plaintext.py`
- Create: `tests/publishers/test_plaintext.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/publishers/test_plaintext.py
import pytest
from pathlib import Path
from lake_of_vectors.publishers.plaintext import PlaintextPublisher
from lake_of_vectors.publishers.base import Document, compute_hash


def test_crawl_finds_txt_files(tmp_path):
    (tmp_path / "a.txt").write_text("File A content.")
    (tmp_path / "b.txt").write_text("File B content.")
    (tmp_path / "c.md").write_text("Not a txt file.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)


def test_crawl_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.txt").write_text("Root.")
    (sub / "nested.txt").write_text("Nested.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2


def test_source_id_is_absolute_path(tmp_path):
    (tmp_path / "note.txt").write_text("Content.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].source_id == str(tmp_path / "note.txt")


def test_metadata_has_filename_and_relative_path(tmp_path):
    sub = tmp_path / "dir"
    sub.mkdir()
    (sub / "file.txt").write_text("Content.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["filename"] == "file.txt"
    assert docs[0].metadata["relative_path"] == "dir/file.txt"


def test_content_hash_matches(tmp_path):
    content = "Some plaintext content."
    (tmp_path / "note.txt").write_text(content)

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].content_hash == compute_hash(content)


def test_skips_empty_files(tmp_path):
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "real.txt").write_text("Has content.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/publishers/test_plaintext.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement PlaintextPublisher**

```python
# src/lake_of_vectors/publishers/plaintext.py
from pathlib import Path
from typing import Iterator

from .base import Document, compute_hash


class PlaintextPublisher:
    def __init__(self, path: Path):
        self.path = Path(path)

    def crawl(self) -> Iterator[Document]:
        for txt_file in sorted(self.path.rglob("*.txt")):
            if not txt_file.is_file():
                continue
            content = txt_file.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                continue

            yield Document(
                source_id=str(txt_file),
                content=content,
                metadata={
                    "filename": txt_file.name,
                    "relative_path": str(txt_file.relative_to(self.path)),
                },
                content_hash=compute_hash(content),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/publishers/test_plaintext.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/publishers/plaintext.py \
  tests/publishers/test_plaintext.py && \
  git commit -m "feat: add PlaintextPublisher"
```

---

### Task 5: SqlitePublisher

**Files:**
- Create: `src/lake_of_vectors/publishers/sqlite.py`
- Create: `tests/publishers/test_sqlite.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/publishers/test_sqlite.py
import sqlite3
import pytest
from pathlib import Path
from lake_of_vectors.publishers.sqlite import SqlitePublisher
from lake_of_vectors.publishers.base import Document, compute_hash


@pytest.fixture
def sample_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            body TEXT,
            title TEXT,
            tags TEXT
        )
    """)
    conn.execute(
        "INSERT INTO notes (body, title, tags) VALUES (?, ?, ?)",
        ("SSRF attack techniques and mitigations.", "SSRF Guide", "security,web"),
    )
    conn.execute(
        "INSERT INTO notes (body, title, tags) VALUES (?, ?, ?)",
        ("SQL injection prevention strategies.", "SQLi Prevention", "security,db"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_crawl_returns_documents(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=["title", "tags"],
    )
    docs = list(publisher.crawl())

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)


def test_source_id_format(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=["title", "tags"],
    )
    docs = list(publisher.crawl())

    assert docs[0].source_id == f"{sample_db}:notes:1"
    assert docs[1].source_id == f"{sample_db}:notes:2"


def test_content_is_body_column(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=[],
    )
    docs = list(publisher.crawl())

    assert docs[0].content == "SSRF attack techniques and mitigations."


def test_metadata_includes_configured_columns(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=["title", "tags"],
    )
    docs = list(publisher.crawl())

    assert docs[0].metadata["title"] == "SSRF Guide"
    assert docs[0].metadata["tags"] == "security,web"
    assert docs[0].metadata["table"] == "notes"


def test_content_hash_matches(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=[],
    )
    docs = list(publisher.crawl())

    expected = compute_hash("SSRF attack techniques and mitigations.")
    assert docs[0].content_hash == expected


def test_skips_rows_with_null_content(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO notes (body) VALUES (NULL)")
    conn.execute("INSERT INTO notes (body) VALUES ('Real content.')")
    conn.commit()
    conn.close()

    publisher = SqlitePublisher(
        path=db_path, table="notes", content_column="body", metadata_columns=[]
    )
    docs = list(publisher.crawl())

    assert len(docs) == 1


def test_skips_rows_with_empty_content(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO notes (body) VALUES ('')")
    conn.execute("INSERT INTO notes (body) VALUES ('Real content.')")
    conn.commit()
    conn.close()

    publisher = SqlitePublisher(
        path=db_path, table="notes", content_column="body", metadata_columns=[]
    )
    docs = list(publisher.crawl())

    assert len(docs) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/publishers/test_sqlite.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement SqlitePublisher**

```python
# src/lake_of_vectors/publishers/sqlite.py
import sqlite3
from pathlib import Path
from typing import Iterator

from .base import Document, compute_hash


class SqlitePublisher:
    def __init__(
        self,
        path: Path,
        table: str,
        content_column: str,
        metadata_columns: list[str],
    ):
        self.path = Path(path)
        self.table = table
        self.content_column = content_column
        self.metadata_columns = metadata_columns

    def crawl(self) -> Iterator[Document]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            columns = ["rowid", self.content_column] + self.metadata_columns
            query = f"SELECT {', '.join(columns)} FROM {self.table}"
            for row in conn.execute(query):
                content = row[self.content_column]
                if not content or not str(content).strip():
                    continue

                content = str(content)
                metadata = {"table": self.table}
                for col in self.metadata_columns:
                    metadata[col] = row[col]

                yield Document(
                    source_id=f"{self.path}:{self.table}:{row['rowid']}",
                    content=content,
                    metadata=metadata,
                    content_hash=compute_hash(content),
                )
        finally:
            conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/publishers/test_sqlite.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/publishers/sqlite.py \
  tests/publishers/test_sqlite.py && \
  git commit -m "feat: add SqlitePublisher"
```

---

### Task 6: Text Chunker

**Files:**
- Create: `src/lake_of_vectors/sync/chunker.py`
- Create: `tests/test_chunker.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_chunker.py
import pytest
from lake_of_vectors.sync.chunker import chunk_text


def test_short_text_returns_single_chunk():
    text = "This is a short sentence."
    chunks = chunk_text(text, max_tokens=500, overlap_tokens=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_is_split_into_multiple_chunks():
    # Create text that's clearly longer than 500 tokens (~2000 words)
    paragraphs = []
    for i in range(40):
        paragraphs.append(f"Paragraph {i}. " + "word " * 50)
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=500, overlap_tokens=50)
    assert len(chunks) > 1


def test_chunks_have_overlap():
    paragraphs = []
    for i in range(20):
        paragraphs.append(f"Unique marker {i}. " + "filler " * 80)
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_tokens=200, overlap_tokens=50)
    assert len(chunks) >= 2

    # Check that there's some shared content between consecutive chunks
    for i in range(len(chunks) - 1):
        words_current = set(chunks[i].split()[-30:])
        words_next = set(chunks[i + 1].split()[:30])
        overlap = words_current & words_next
        assert len(overlap) > 0, f"No overlap between chunk {i} and {i+1}"


def test_splits_on_double_newline_first():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, max_tokens=5, overlap_tokens=0)
    # Should split on paragraph boundaries
    assert any("First paragraph." in c for c in chunks)
    assert any("Second paragraph." in c for c in chunks)


def test_empty_text_returns_empty_list():
    chunks = chunk_text("", max_tokens=500, overlap_tokens=50)
    assert chunks == []


def test_whitespace_only_returns_empty_list():
    chunks = chunk_text("   \n\n  ", max_tokens=500, overlap_tokens=50)
    assert chunks == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chunker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement chunker**

```python
# src/lake_of_vectors/sync/chunker.py


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


def chunk_text(
    text: str, max_tokens: int = 500, overlap_tokens: int = 50
) -> list[str]:
    if not text or not text.strip():
        return []

    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    # If the whole text fits, return it as a single chunk
    if _estimate_tokens(text) <= max_tokens:
        return [text]

    # Try splitting by separators in order of preference
    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, separators, max_chars, overlap_chars)


def _recursive_split(
    text: str, separators: list[str], max_chars: int, overlap_chars: int
) -> list[str]:
    if not text.strip():
        return []

    if len(text) <= max_chars:
        return [text]

    # Find the best separator that produces splits
    sep = separators[0] if separators else " "
    remaining_seps = separators[1:] if len(separators) > 1 else separators

    parts = text.split(sep)
    if len(parts) == 1:
        # This separator doesn't help, try the next one
        if remaining_seps and remaining_seps != separators:
            return _recursive_split(text, remaining_seps, max_chars, overlap_chars)
        # Last resort: hard split by character
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunks.append(text[start:end])
            start = end - overlap_chars if end < len(text) else end
        return chunks

    # Merge parts into chunks that fit within max_chars
    chunks = []
    current_parts: list[str] = []
    current_len = 0

    for part in parts:
        part_len = len(part) + (len(sep) if current_parts else 0)

        if current_len + part_len > max_chars and current_parts:
            chunk_text_str = sep.join(current_parts)
            chunks.append(chunk_text_str)

            # Calculate overlap: keep trailing parts that fit in overlap_chars
            overlap_parts: list[str] = []
            overlap_len = 0
            for p in reversed(current_parts):
                if overlap_len + len(p) + len(sep) > overlap_chars:
                    break
                overlap_parts.insert(0, p)
                overlap_len += len(p) + len(sep)

            current_parts = overlap_parts
            current_len = sum(len(p) for p in current_parts) + len(sep) * max(
                0, len(current_parts) - 1
            )

        current_parts.append(part)
        current_len += part_len

    if current_parts:
        final = sep.join(current_parts)
        if final.strip():
            chunks.append(final)

    # Recursively split any chunk that's still too large
    result = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            result.extend(
                _recursive_split(chunk, remaining_seps, max_chars, overlap_chars)
            )
        else:
            result.append(chunk)

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_chunker.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/sync/chunker.py tests/test_chunker.py && \
  git commit -m "feat: add recursive text chunker"
```

---

### Task 7: Embedding Backends

**Files:**
- Create: `src/lake_of_vectors/embeddings/base.py`
- Create: `src/lake_of_vectors/embeddings/local.py`
- Create: `src/lake_of_vectors/embeddings/api.py`

- [ ] **Step 1: Create the base protocol**

```python
# src/lake_of_vectors/embeddings/base.py
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    def model_name(self) -> str:
        ...
```

- [ ] **Step 2: Implement LocalEmbedder**

```python
# src/lake_of_vectors/embeddings/local.py
from sentence_transformers import SentenceTransformer


class LocalEmbedder:
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self._model_name = model
        self._model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def model_name(self) -> str:
        return f"local:{self._model_name}"
```

- [ ] **Step 3: Implement APIEmbedder**

```python
# src/lake_of_vectors/embeddings/api.py
from openai import OpenAI


class APIEmbedder:
    def __init__(self, model: str = "text-embedding-3-small", api_key: str = ""):
        self._model_name = model
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(input=texts, model=self._model_name)
        return [item.embedding for item in response.data]

    @property
    def model_name(self) -> str:
        return f"openai:{self._model_name}"
```

- [ ] **Step 4: Quick smoke test for LocalEmbedder**

Run: `python -c "from lake_of_vectors.embeddings.local import LocalEmbedder; e = LocalEmbedder(); r = e.embed(['test']); print(len(r), len(r[0]))"`
Expected: `1 384` (one embedding, 384 dimensions)

Note: First run downloads the model (~80MB). Subsequent runs are instant.

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/embeddings/ && \
  git commit -m "feat: add embedding backends (local + OpenAI API)"
```

---

### Task 8: Sync Engine

**Files:**
- Create: `src/lake_of_vectors/sync/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_engine.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from lake_of_vectors.sync.engine import SyncEngine
from lake_of_vectors.publishers.base import Document, compute_hash


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    @property
    def model_name(self) -> str:
        return "fake:test"


@pytest.fixture
def engine(tmp_path):
    return SyncEngine(
        chromadb_path=str(tmp_path / "chromadb"),
        embedder=FakeEmbedder(),
    )


def test_sync_new_documents(engine):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
        Document(
            source_id="/notes/b.md",
            content="Content B",
            metadata={"title": "B"},
            content_hash=compute_hash("Content B"),
        ),
    ]
    report = engine.sync("test-source", iter(docs))

    assert report.added == 2
    assert report.updated == 0
    assert report.deleted == 0
    assert report.unchanged == 0


def test_sync_unchanged_documents(engine):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
    ]
    engine.sync("test-source", iter(docs))

    # Sync again with same content
    report = engine.sync("test-source", iter(docs))

    assert report.added == 0
    assert report.unchanged == 1


def test_sync_updated_document(engine):
    doc_v1 = Document(
        source_id="/notes/a.md",
        content="Content v1",
        metadata={"title": "A"},
        content_hash=compute_hash("Content v1"),
    )
    engine.sync("test-source", iter([doc_v1]))

    doc_v2 = Document(
        source_id="/notes/a.md",
        content="Content v2 updated",
        metadata={"title": "A"},
        content_hash=compute_hash("Content v2 updated"),
    )
    report = engine.sync("test-source", iter([doc_v2]))

    assert report.updated == 1
    assert report.added == 0


def test_sync_deleted_document(engine):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
        Document(
            source_id="/notes/b.md",
            content="Content B",
            metadata={"title": "B"},
            content_hash=compute_hash("Content B"),
        ),
    ]
    engine.sync("test-source", iter(docs))

    # Second sync with only doc A — doc B should be detected as deleted
    remaining = [docs[0]]
    report = engine.sync("test-source", iter(remaining))

    assert report.deleted == 1
    assert report.unchanged == 1


def test_sync_rebuild_deletes_all_first(engine):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
    ]
    engine.sync("test-source", iter(docs))
    report = engine.sync("test-source", iter(docs), rebuild=True)

    assert report.added == 1
    assert report.unchanged == 0


def test_sync_embedding_mismatch_raises(engine, tmp_path):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
    ]
    engine.sync("test-source", iter(docs))

    # Create a new engine with a different embedder name
    class OtherEmbedder:
        def embed(self, texts):
            return [[0.1, 0.2, 0.3] for _ in texts]

        @property
        def model_name(self):
            return "other:model"

    engine2 = SyncEngine(
        chromadb_path=str(tmp_path / "chromadb"),
        embedder=OtherEmbedder(),
    )
    with pytest.raises(ValueError, match="mismatch"):
        engine2.sync("test-source", iter(docs))


def test_get_source_stats(engine):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
    ]
    engine.sync("test-source", iter(docs))

    stats = engine.get_source_stats("test-source")
    assert stats["chunk_count"] > 0
    assert stats["embedding_model"] == "fake:test"


def test_list_sources_empty(engine):
    assert engine.list_sources() == []


def test_list_sources_after_sync(engine):
    docs = [
        Document(
            source_id="/notes/a.md",
            content="Content A",
            metadata={"title": "A"},
            content_hash=compute_hash("Content A"),
        ),
    ]
    engine.sync("my-source", iter(docs))

    sources = engine.list_sources()
    assert "my-source" in sources
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement sync engine**

```python
# src/lake_of_vectors/sync/engine.py
from dataclasses import dataclass
from typing import Iterator

import chromadb

from lake_of_vectors.embeddings.base import Embedder
from lake_of_vectors.publishers.base import Document
from lake_of_vectors.sync.chunker import chunk_text


@dataclass
class SyncReport:
    source_name: str
    added: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0

    def __str__(self) -> str:
        return (
            f"synced {self.source_name}: "
            f"{self.added} added, {self.updated} updated, "
            f"{self.deleted} deleted, {self.unchanged} unchanged"
        )


class SyncEngine:
    def __init__(self, chromadb_path: str, embedder: Embedder):
        self._client = chromadb.PersistentClient(path=chromadb_path)
        self._embedder = embedder

    def sync(
        self,
        source_name: str,
        documents: Iterator[Document],
        rebuild: bool = False,
    ) -> SyncReport:
        report = SyncReport(source_name=source_name)

        if rebuild:
            try:
                self._client.delete_collection(source_name)
            except ValueError:
                pass  # Collection doesn't exist yet

        collection = self._client.get_or_create_collection(
            name=source_name,
            metadata={"embedding_model": self._embedder.model_name},
        )

        # Check embedding model mismatch (unless rebuilding)
        if not rebuild:
            stored_model = collection.metadata.get("embedding_model")
            if (
                stored_model
                and stored_model != self._embedder.model_name
                and collection.count() > 0
            ):
                raise ValueError(
                    f"Embedding model mismatch for '{source_name}': "
                    f"stored={stored_model}, configured={self._embedder.model_name}. "
                    f"Run 'lake sync --rebuild --source {source_name}' to re-embed."
                )

        # Collect all current documents
        current_docs = {doc.source_id: doc for doc in documents}

        # Get all stored source_ids and their hashes from ChromaDB
        stored = self._get_stored_docs(collection)

        # Determine diff
        current_ids = set(current_docs.keys())
        stored_ids = set(stored.keys())

        new_ids = current_ids - stored_ids
        deleted_ids = stored_ids - current_ids
        common_ids = current_ids & stored_ids

        # Handle deletions
        for source_id in deleted_ids:
            self._delete_chunks(collection, source_id)
            report.deleted += 1

        # Handle new documents
        for source_id in new_ids:
            doc = current_docs[source_id]
            self._upsert_document(collection, source_name, doc)
            report.added += 1

        # Handle updates vs unchanged
        for source_id in common_ids:
            doc = current_docs[source_id]
            if stored[source_id] != doc.content_hash:
                self._delete_chunks(collection, source_id)
                self._upsert_document(collection, source_name, doc)
                report.updated += 1
            else:
                report.unchanged += 1

        return report

    def _get_stored_docs(self, collection) -> dict[str, str]:
        """Return {source_id: content_hash} for all stored chunks."""
        if collection.count() == 0:
            return {}

        results = collection.get(include=["metadatas"])
        doc_hashes: dict[str, str] = {}
        for meta in results["metadatas"]:
            sid = meta.get("source_id", "")
            h = meta.get("content_hash", "")
            if sid and sid not in doc_hashes:
                doc_hashes[sid] = h
        return doc_hashes

    def _delete_chunks(self, collection, source_id: str) -> None:
        """Delete all chunks belonging to a source_id."""
        results = collection.get(
            where={"source_id": source_id}, include=["metadatas"]
        )
        if results["ids"]:
            collection.delete(ids=results["ids"])

    def _upsert_document(self, collection, source_name: str, doc: Document) -> None:
        """Chunk, embed, and insert a document."""
        chunks = chunk_text(doc.content)
        if not chunks:
            return

        embeddings = self._embedder.embed(chunks)

        ids = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.source_id}::chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadata = {
                "source_id": doc.source_id,
                "source_name": source_name,
                "content_hash": doc.content_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            # Flatten document metadata (ChromaDB requires flat metadata)
            for k, v in doc.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    metadata[k] = v
            metadatas.append(metadata)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def get_source_stats(self, source_name: str) -> dict:
        """Get stats for a synced source."""
        try:
            collection = self._client.get_collection(source_name)
        except ValueError:
            return {"chunk_count": 0, "embedding_model": "none"}

        return {
            "chunk_count": collection.count(),
            "embedding_model": collection.metadata.get(
                "embedding_model", "unknown"
            ),
        }

    def list_sources(self) -> list[str]:
        """List all synced source names."""
        collections = self._client.list_collections()
        return [c.name for c in collections]

    def search(
        self,
        query: str,
        source: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Semantic search across one or all sources."""
        query_embedding = self._embedder.embed([query])[0]

        if source:
            collections = [self._client.get_collection(source)]
        else:
            collections = self._client.list_collections()

        all_results = []
        for collection in collections:
            if collection.count() == 0:
                continue
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(limit, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            for i, doc_id in enumerate(results["ids"][0]):
                all_results.append({
                    "chunk_text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "source_name": collection.name,
                })

        # Sort by distance (lower = more similar) and take top limit
        all_results.sort(key=lambda r: r["distance"])
        return all_results[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_engine.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/sync/engine.py tests/test_engine.py && \
  git commit -m "feat: add sync engine with diff, chunk, embed, upsert"
```

---

### Task 9: MCP Server

**Files:**
- Create: `src/lake_of_vectors/mcp/server.py`
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mcp_server.py
import pytest
from unittest.mock import MagicMock, patch
from lake_of_vectors.mcp.server import create_mcp_server


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.list_sources.return_value = ["security-notes", "knowledge-db"]
    engine.search.return_value = [
        {
            "chunk_text": "SSRF is a vulnerability where...",
            "metadata": {
                "source_id": "/notes/ssrf.md",
                "title": "SSRF Guide",
                "chunk_index": 0,
                "total_chunks": 3,
            },
            "distance": 0.25,
            "source_name": "security-notes",
        },
    ]
    engine.get_source_stats.return_value = {
        "chunk_count": 42,
        "embedding_model": "local:all-MiniLM-L6-v2",
    }
    return engine


def test_create_mcp_server_returns_fastmcp(mock_engine):
    mcp = create_mcp_server(mock_engine)
    assert mcp is not None
    assert mcp.name == "lake-of-vectors"


def test_server_has_semantic_search_tool(mock_engine):
    mcp = create_mcp_server(mock_engine)
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "semantic_search" in tool_names


def test_server_has_list_sources_tool(mock_engine):
    mcp = create_mcp_server(mock_engine)
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "list_sources" in tool_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mcp_server.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement MCP server**

```python
# src/lake_of_vectors/mcp/server.py
from mcp.server.fastmcp import FastMCP

from lake_of_vectors.sync.engine import SyncEngine


def create_mcp_server(engine: SyncEngine) -> FastMCP:
    mcp = FastMCP("lake-of-vectors")

    @mcp.tool()
    def semantic_search(
        query: str, source: str = "", limit: int = 10
    ) -> str:
        """Search the user's personal knowledge base. Use this BEFORE answering
        questions about security testing, vulnerabilities, or techniques, to
        supplement your knowledge with the user's notes and documentation."""
        results = engine.search(
            query=query,
            source=source if source else None,
            limit=limit,
        )

        if not results:
            return "No results found."

        output_parts = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            source_id = meta.get("source_id", "unknown")
            title = meta.get("title", "")
            chunk_idx = meta.get("chunk_index", 0)
            total = meta.get("total_chunks", 1)
            distance = r["distance"]
            similarity = max(0.0, 1.0 - distance)

            header = f"### Result {i}"
            if title:
                header += f": {title}"
            header += f" (similarity: {similarity:.2f})"

            output_parts.append(
                f"{header}\n"
                f"**Source:** {source_id} (chunk {chunk_idx + 1}/{total})\n"
                f"**Collection:** {r['source_name']}\n\n"
                f"{r['chunk_text']}"
            )

        return "\n\n---\n\n".join(output_parts)

    @mcp.tool()
    def list_sources() -> str:
        """List all available knowledge base sources that have been indexed."""
        sources = engine.list_sources()
        if not sources:
            return "No sources have been synced yet. Run 'lake sync' first."

        lines = []
        for name in sources:
            stats = engine.get_source_stats(name)
            lines.append(
                f"- **{name}**: {stats['chunk_count']} chunks "
                f"(model: {stats['embedding_model']})"
            )
        return "\n".join(lines)

    return mcp
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mcp_server.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/lake_of_vectors/mcp/server.py tests/test_mcp_server.py && \
  git commit -m "feat: add MCP server with semantic_search and list_sources tools"
```

---

### Task 10: CLI

**Files:**
- Create: `src/lake_of_vectors/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import pytest
from click.testing import CliRunner
from lake_of_vectors.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def config_file(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("""
sources:
  - type: markdown
    name: test-notes
    path: {notes_dir}

embedding:
  backend: local
  model: all-MiniLM-L6-v2
""".format(notes_dir=str(tmp_path / "notes")))
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "test.md").write_text("# Test Note\nSome content here.")
    return str(config)


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "lake" in result.output.lower() or "sync" in result.output.lower()


def test_sync_command_exists(runner):
    result = runner.invoke(cli, ["sync", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output
    assert "--rebuild" in result.output


def test_serve_command_exists(runner):
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0


def test_status_command_exists(runner):
    result = runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0


def test_sync_with_missing_config(runner, tmp_path):
    result = runner.invoke(cli, ["sync", "--config", str(tmp_path / "nope.yaml")])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# src/lake_of_vectors/cli.py
import sys
from pathlib import Path

import click

from lake_of_vectors.config import load_config, default_config_path, Config
from lake_of_vectors.sync.engine import SyncEngine


def _make_publisher(source_config):
    if source_config.type == "markdown":
        from lake_of_vectors.publishers.markdown import MarkdownPublisher
        return MarkdownPublisher(path=source_config.path)
    elif source_config.type == "plaintext":
        from lake_of_vectors.publishers.plaintext import PlaintextPublisher
        return PlaintextPublisher(path=source_config.path)
    elif source_config.type == "sqlite":
        from lake_of_vectors.publishers.sqlite import SqlitePublisher
        return SqlitePublisher(
            path=source_config.path,
            table=source_config.table,
            content_column=source_config.content_column,
            metadata_columns=source_config.metadata_columns,
        )
    else:
        raise click.ClickException(f"Unknown source type: {source_config.type}")


def _make_embedder(config: Config):
    if config.embedding.backend == "local":
        from lake_of_vectors.embeddings.local import LocalEmbedder
        return LocalEmbedder(model=config.embedding.model)
    elif config.embedding.backend == "openai":
        from lake_of_vectors.embeddings.api import APIEmbedder
        if not config.embedding.api_key:
            raise click.ClickException("OpenAI backend requires api_key in config.")
        return APIEmbedder(
            model=config.embedding.model, api_key=config.embedding.api_key
        )
    else:
        raise click.ClickException(
            f"Unknown embedding backend: {config.embedding.backend}"
        )


def _chromadb_path() -> str:
    path = Path("~/.local/share/lake-of-vectors/chromadb").expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@click.group()
def cli():
    """Lake of Embeddings — semantic search over your personal knowledge."""
    pass


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
@click.option("--source", default=None, help="Sync only this source name")
@click.option("--rebuild", is_flag=True, help="Delete and re-embed all vectors")
def sync(config_path, source, rebuild):
    """Sync data sources into the vector database."""
    try:
        cfg_path = Path(config_path) if config_path else default_config_path()
        config = load_config(cfg_path)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {cfg_path}")

    embedder = _make_embedder(config)
    engine = SyncEngine(chromadb_path=_chromadb_path(), embedder=embedder)

    sources = config.sources
    if source:
        sources = [s for s in sources if s.name == source]
        if not sources:
            raise click.ClickException(f"Source '{source}' not found in config.")

    for src_config in sources:
        click.echo(f"Syncing {src_config.name}...")
        publisher = _make_publisher(src_config)
        try:
            report = engine.sync(src_config.name, publisher.crawl(), rebuild=rebuild)
            click.echo(f"  {report}")
        except ValueError as e:
            raise click.ClickException(str(e))

    click.echo("Done.")


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
def serve(config_path):
    """Start the MCP server (stdio mode)."""
    from lake_of_vectors.mcp.server import create_mcp_server

    try:
        cfg_path = Path(config_path) if config_path else default_config_path()
        config = load_config(cfg_path)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {cfg_path}")

    embedder = _make_embedder(config)
    engine = SyncEngine(chromadb_path=_chromadb_path(), embedder=embedder)
    mcp = create_mcp_server(engine)
    mcp.run()


@cli.command()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
def status(config_path):
    """Show sync status for all sources."""
    try:
        cfg_path = Path(config_path) if config_path else default_config_path()
        config = load_config(cfg_path)
    except FileNotFoundError:
        raise click.ClickException(f"Config file not found: {cfg_path}")

    embedder = _make_embedder(config)
    engine = SyncEngine(chromadb_path=_chromadb_path(), embedder=embedder)

    synced = engine.list_sources()
    if not synced:
        click.echo("No sources synced yet. Run 'lake sync' first.")
        return

    for name in synced:
        stats = engine.get_source_stats(name)
        click.echo(
            f"  {name}: {stats['chunk_count']} chunks "
            f"(model: {stats['embedding_model']})"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Verify the CLI works end-to-end**

```bash
lake --help
lake sync --help
lake status --help
```

- [ ] **Step 6: Commit**

```bash
git add src/lake_of_vectors/cli.py tests/test_cli.py && \
  git commit -m "feat: add CLI commands (sync, serve, status)"
```

---

### Task 11: End-to-End Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import pytest
from pathlib import Path
from lake_of_vectors.publishers.markdown import MarkdownPublisher
from lake_of_vectors.sync.engine import SyncEngine


class FakeEmbedder:
    """Deterministic embedder for integration tests."""
    def embed(self, texts: list[str]) -> list[list[float]]:
        # Simple hash-based embedding for deterministic results
        results = []
        for text in texts:
            h = hash(text) % 1000
            results.append([h / 1000.0, (h + 1) / 1000.0, (h + 2) / 1000.0])
        return results

    @property
    def model_name(self) -> str:
        return "fake:integration"


@pytest.fixture
def setup(tmp_path):
    # Create test markdown files
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "ssrf.md").write_text(
        "# SSRF\nServer-Side Request Forgery allows an attacker to make "
        "requests from the server to internal resources."
    )
    (notes_dir / "sqli.md").write_text(
        "# SQL Injection\nSQL injection is a code injection technique that "
        "exploits security vulnerabilities in database queries."
    )
    (notes_dir / "xss.md").write_text(
        "# Cross-Site Scripting\nXSS attacks inject malicious scripts into "
        "web pages viewed by other users."
    )

    engine = SyncEngine(
        chromadb_path=str(tmp_path / "chromadb"),
        embedder=FakeEmbedder(),
    )
    return notes_dir, engine


def test_full_sync_and_search(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)

    # Sync
    report = engine.sync("security-notes", publisher.crawl())
    assert report.added == 3
    assert report.deleted == 0

    # Search
    results = engine.search("server request forgery", limit=3)
    assert len(results) > 0
    assert all("chunk_text" in r for r in results)


def test_sync_detects_changes(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)

    # Initial sync
    engine.sync("security-notes", publisher.crawl())

    # Modify a file
    (notes_dir / "ssrf.md").write_text(
        "# SSRF Updated\nNew content about SSRF with blind techniques."
    )

    # Re-sync
    publisher2 = MarkdownPublisher(path=notes_dir)
    report = engine.sync("security-notes", publisher2.crawl())
    assert report.updated == 1
    assert report.unchanged == 2


def test_sync_detects_deletions(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)

    # Initial sync
    engine.sync("security-notes", publisher.crawl())

    # Delete a file
    (notes_dir / "xss.md").unlink()

    # Re-sync
    publisher2 = MarkdownPublisher(path=notes_dir)
    report = engine.sync("security-notes", publisher2.crawl())
    assert report.deleted == 1
    assert report.unchanged == 2


def test_list_sources_and_stats(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)
    engine.sync("security-notes", publisher.crawl())

    sources = engine.list_sources()
    assert "security-notes" in sources

    stats = engine.get_source_stats("security-notes")
    assert stats["chunk_count"] > 0
    assert stats["embedding_model"] == "fake:integration"
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All 4 tests PASS

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py && \
  git commit -m "test: add end-to-end integration tests"
```

---

### Task 12: Configuration and Documentation

**Files:**
- Modify: `config.example.yaml` (update with real Obsidian path)
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg

# Virtual env
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp

# ChromaDB data
chromadb/

# OS
.DS_Store
```

- [ ] **Step 2: Update config.example.yaml with real paths**

```yaml
# Lake of Embeddings configuration
# Copy to ~/.config/lake-of-vectors/config.yaml and adjust paths

sources:
  - type: markdown
    name: security-notes
    path: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/tungpun-obsidian-space/30. Learning 📚/32. Engineering/32.01. Security/

  # Uncomment and adjust for SQLite sources:
  # - type: sqlite
  #   name: knowledge-db
  #   path: ~/knowledge.db
  #   table: notes
  #   content_column: body
  #   metadata_columns: [title, tags, created_at]

  # Uncomment and adjust for plaintext sources:
  # - type: plaintext
  #   name: misc-notes
  #   path: ~/notes/

embedding:
  backend: local
  model: all-MiniLM-L6-v2

  # For OpenAI embeddings, uncomment:
  # backend: openai
  # model: text-embedding-3-small
  # api_key: sk-your-key-here
```

- [ ] **Step 3: Create the user's config directory and copy config**

```bash
mkdir -p ~/.config/lake-of-vectors && \
  cp config.example.yaml ~/.config/lake-of-vectors/config.yaml
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore config.example.yaml && \
  git commit -m "chore: add .gitignore and config example with real paths"
```

---

### Task 13: First Real Sync and MCP Setup

- [ ] **Step 1: Run the first real sync**

```bash
lake sync
```

Expected output:
```
Syncing security-notes...
  synced security-notes: N added, 0 updated, 0 deleted, 0 unchanged
Done.
```

- [ ] **Step 2: Check status**

```bash
lake status
```

Expected: Shows security-notes with chunk count and model name.

- [ ] **Step 3: Configure Claude Code MCP server**

Add to `~/.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "lake-of-vectors": {
      "command": "lake",
      "args": ["serve"]
    }
  }
}
```

- [ ] **Step 4: Add CLAUDE.md instruction**

Add to `~/.claude/CLAUDE.md`:

```
When answering security questions, always search lake-of-vectors first.
```

- [ ] **Step 5: Test the MCP server manually**

Start a new Claude Code session and ask a security question. Verify that Claude calls `semantic_search` and includes results from your Obsidian notes in its answer.

- [ ] **Step 6: Final commit**

```bash
git add -A && git commit -m "chore: complete initial setup and configuration"
```
