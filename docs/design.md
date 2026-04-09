# Lake of Embeddings — Design Spec

## Problem

When working with Claude to find security issues (or other domain knowledge), Claude can only find information in local sources (Obsidian notes, SQLite databases) via exact string matching. Semantic search over personal knowledge is not available, so relevant notes are missed when the wording doesn't match exactly.

## Solution

A local Python platform that:

1. Crawls configured data sources (Markdown directories, SQLite tables, plaintext files)
2. Chunks and embeds content into a local ChromaDB vector database
3. Exposes semantic search to Claude via an MCP server

## Architecture

```
┌─────────────────────────────────────────────────┐
│                lake-of-vectors                │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌─────────────┐  │
│  │Publishers │──▶│  Sync    │──▶│  ChromaDB   │  │
│  │          │   │  Engine   │   │  (on-disk)  │  │
│  │• Markdown │   │• Chunking │   │             │  │
│  │• SQLite   │   │• Hashing  │   │             │  │
│  │• Plaintext│   │• Diffing  │   │             │  │
│  └──────────┘   │• Embedding│   └──────┬──────┘  │
│                  └──────────┘          │         │
│                                        │         │
│                  ┌──────────┐          │         │
│                  │MCP Server│◀─────────┘         │
│                  │(stdio)   │                    │
│                  │• search  │                    │
│                  │• lookup  │                    │
│                  └──────────┘                    │
│                                                  │
│  ┌──────────────────────────────┐               │
│  │  Embedding Backend (pluggable)│               │
│  │  • LocalEmbedder (default)    │               │
│  │  • APIEmbedder (OpenAI, etc.) │               │
│  └──────────────────────────────┘               │
└─────────────────────────────────────────────────┘
```

**Data flow:**

1. `lake sync` → Publishers crawl configured sources → yield Documents
2. Sync engine computes content hashes, diffs against stored state in ChromaDB
3. New/changed docs get chunked → embedded → upserted into ChromaDB
4. Deleted docs get removed from ChromaDB
5. `lake serve` → MCP server reads from ChromaDB → returns semantic search results to Claude

## Publishers

Each publisher implements a simple protocol:

```python
class Publisher(Protocol):
    def crawl(self) -> Iterator[Document]:
        """Yield all documents from this source."""
        ...

@dataclass
class Document:
    source_id: str      # unique ID (e.g. file path, db:table:row_id)
    content: str        # raw text content
    metadata: dict      # source-specific metadata (title, tags, path, etc.)
    content_hash: str   # SHA-256 of content
```

### Publisher Types

| Publisher | Source | `source_id` format | Metadata |
|-----------|--------|-------------------|----------|
| `MarkdownPublisher` | Directory of `.md` files (recursive) | file path | title (from H1 or filename), relative path, directory |
| `SqlitePublisher` | SQLite DB + configured table/columns | `db_path:table:rowid` | table name, column names |
| `PlaintextPublisher` | Directory of `.txt` files | file path | filename, relative path |

Publishers only crawl and yield documents. They have no knowledge of embeddings or ChromaDB.

## Sync Engine

### Sync Algorithm (per source)

```
1. Publisher.crawl() → all current Documents (with content_hash)
2. Query ChromaDB for all stored source_ids for this source name
3. Diff:
   - NEW: source_id in crawl but not in ChromaDB → chunk, embed, insert
   - CHANGED: source_id in both but content_hash differs → delete old chunks, re-chunk, embed, insert
   - DELETED: source_id in ChromaDB but not in crawl → delete all chunks
   - UNCHANGED: same source_id and hash → skip
4. Report: "synced security-notes: 3 added, 1 updated, 2 deleted, 148 unchanged"
```

### Chunking

- Split documents into chunks of ~500 tokens with ~50 token overlap
- Each chunk gets its own vector in ChromaDB
- Chunk metadata includes: `source_id`, `source_name`, `content_hash`, `chunk_index`, plus original document metadata
- Recursive text splitter: split on `\n\n`, then `\n`, then sentence boundaries, then word boundaries

### ChromaDB Layout

- One collection per source name (e.g. `security-notes`, `knowledge-db`)
- Each collection stores vectors, chunk text, and metadata
- Sync state is derived from ChromaDB itself (no separate state DB)
- Storage location: `~/.local/share/lake-of-vectors/chromadb/`

## Embedding Backend

Pluggable interface:

```python
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""
        ...
```

### Implementations

| Backend | Model | Dimensions | Notes |
|---------|-------|-----------|-------|
| `LocalEmbedder` | `all-MiniLM-L6-v2` via `sentence-transformers` | 384 | Default. ~80MB model, ~200-300MB RAM. Runs on CPU. |
| `APIEmbedder` | Configurable (e.g. OpenAI `text-embedding-3-small`) | varies | Needs API key in config. |

### Backend Mismatch Protection

The sync engine stores the embedding backend + model name in ChromaDB collection metadata. If the configured backend differs from what's stored, sync refuses with a clear error and prompts the user to run `lake sync --rebuild` (or `lake sync --rebuild --source X`).

## MCP Server

Runs over **stdio**. Claude Code starts/stops it automatically. Built with the `mcp` Python SDK.

### Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `semantic_search` | Find relevant chunks by meaning | `query: str`, `source?: str`, `limit?: int` (default 10) |
| `list_sources` | Show all configured/synced sources | none |

### `semantic_search` Behavior

1. Embed the query using the configured embedding backend
2. If `source` is specified, query that single collection. Otherwise, query all collections and merge results sorted by similarity score (top `limit` across all sources).
3. Return results with: chunk text, source file/path, chunk index, similarity score, metadata
4. Results formatted as readable text for Claude to use directly

### Tool Description (for Claude discoverability)

The `semantic_search` tool description will include a nudge:

> "Search the user's personal knowledge base. Use this BEFORE answering questions about security testing, vulnerabilities, or techniques, to supplement your knowledge with the user's notes."

### CLAUDE.md Instruction

Add to the user's CLAUDE.md or project CLAUDE.md:

> "When answering security questions, always search lake-of-vectors first."

## CLI

| Command | What it does |
|---------|-------------|
| `lake sync` | Full sync for all configured sources |
| `lake sync --source <name>` | Sync one source only |
| `lake sync --rebuild` | Delete all vectors, re-sync everything |
| `lake sync --rebuild --source <name>` | Rebuild vectors for one specific source |
| `lake serve` | Start MCP server (stdio, used by Claude Code) |
| `lake status` | Show per-source doc count, last sync time, embedding backend |

## Configuration

Location: `~/.config/lake-of-vectors/config.yaml`

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
  backend: local  # or "openai"
  model: all-MiniLM-L6-v2
  # api_key: sk-... (only for API backends)
```

## Project Structure

```
lake-of-vectors/
├── pyproject.toml
├── src/
│   └── lake_of_vectors/
│       ├── __init__.py
│       ├── cli.py              # CLI entry points (click)
│       ├── config.py           # Load/validate YAML config
│       ├── publishers/
│       │   ├── __init__.py
│       │   ├── base.py         # Document dataclass, Publisher protocol
│       │   ├── markdown.py
│       │   ├── sqlite.py
│       │   └── plaintext.py
│       ├── embeddings/
│       │   ├── __init__.py
│       │   ├── base.py         # Embedder protocol
│       │   ├── local.py        # sentence-transformers
│       │   └── api.py          # OpenAI etc.
│       ├── sync/
│       │   ├── __init__.py
│       │   ├── engine.py       # Diff, chunk, embed, upsert
│       │   └── chunker.py      # Text splitting logic
│       └── mcp/
│           ├── __init__.py
│           └── server.py       # MCP server with tools
├── config.example.yaml
└── tests/
```

## Installation

```bash
uv pip install -e .
```

Registers the `lake` CLI command.

## Claude Code MCP Config

Add to `~/.claude/settings.json` (or project-level):

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

## Testing & Debugging ChromaDB

### Semantic search (primary)

```bash
python scripts/search.py "SSRF blind techniques"
python scripts/search.py "SQL injection bypass" --source security-notes --limit 3
```

Reads `~/.config/lake-of-vectors/config.yaml`, embeds the query with the configured backend, and prints ranked results with similarity scores.

### Chunk counts per source

```bash
lake status
```

### Inspect raw data via Python REPL

```python
import chromadb
client = chromadb.PersistentClient(
    path="/Users/tungpun/.local/share/lake-of-vectors/chromadb"
)
for col in client.list_collections():
    print(col.name, "—", col.count(), "chunks")
    for doc in col.peek(3)["documents"]:
        print(" ", doc[:120])
```

### Inspect raw SQLite metadata

```bash
sqlite3 ~/.local/share/lake-of-vectors/chromadb/chroma.sqlite3 \
  "SELECT id, string_value FROM embedding_metadata \
   WHERE key='chunk_text' LIMIT 5;"
```

### Why `chroma.sqlite3` exists

ChromaDB uses SQLite as its backing store for collection metadata, document IDs, content hashes, and chunk text. The actual vector embeddings are stored in binary index files alongside it (in the same directory). The `chroma.sqlite3` file is ChromaDB's internal state — do not edit it directly.

## Dependencies

- `chromadb` — vector database
- `sentence-transformers` — local embedding (default backend)
- `mcp` — MCP server SDK
- `click` — CLI framework
- `pyyaml` — config parsing
- `openai` — optional, for API embedding backend
