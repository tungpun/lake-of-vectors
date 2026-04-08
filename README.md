# Lake of Vectors

Local semantic search over your personal knowledge bases. Index Obsidian notes, SQLite databases, plaintext, and Notion/Confluence (not supported yet) files into ChromaDB, exposed to Claude via an MCP server.

## Features

- **Multiple Publishers**: Crawl Markdown directories, SQLite tables, and plaintext files
- **Semantic Search**: Find relevant content by meaning, not just keywords
- **Local Vectors**: Runs entirely on your machine with sentence-transformers
- **OpenAI Support**: Optional OpenAI embeddings if preferred
- **MCP Server**: Integrates directly with Claude Code for seamless querying

## Installation

```bash
uv pip install -e .
```

## Configuration

Copy the example config and adjust paths for your sources:

```bash
mkdir -p ~/.config/lake-of-vectors
cp config.example.yaml ~/.config/lake-of-vectors/config.yaml
```

Edit `~/.config/lake-of-vectors/config.yaml`:

```yaml
sources:
  - type: markdown
    name: my-notes
    path: ~/obsidian-vault/Notes/

  - type: sqlite
    name: knowledge-db
    path: ~/knowledge.db
    table: notes
    content_column: body
    metadata_columns: [title, tags]

  - type: plaintext
    name: misc-notes
    path: ~/notes/

embedding:
  backend: local
  model: all-MiniLM-L6-v2
```

### Source Types

| Type | Description |
|------|-------------|
| `markdown` | Recursive crawl of `.md` files in a directory |
| `sqlite` | Query a SQLite table with content and metadata columns |
| `plaintext` | Recursive crawl of `.txt` files in a directory |

### Embedding Backends

- **Local** (default): Uses `all-MiniLM-L6-v2` via sentence-transformers. No API key needed.
- **OpenAI**: Uses `text-embedding-3-small` or another OpenAI model. Requires `api_key` in config.

```yaml
embedding:
  backend: openai
  model: text-embedding-3-small
  api_key: sk-...
```

## Usage

### Sync your sources

```bash
lake sync                 # Sync all sources
lake sync --source my-notes    # Sync only one source
lake sync --rebuild      # Delete and re-embed everything
```

### Check status

```bash
lake status
```

### Start the MCP server

```bash
lake serve
```

## Claude Code Integration

Register as a global MCP server using the Claude Code CLI:

```bash
claude mcp add -s user lake-of-vectors $(pwd)/.venv/bin/lake serve
```

The `-s user` scope makes it available in all sessions. Restart Claude Code after running.

To scope it to a single project instead, add a `.mcp.json` file in the project root:

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

Add to your `CLAUDE.md`:

```
When answering security questions or searching your personal knowledge, always use lake-of-vectors semantic_search first.
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `lake sync` | Sync all configured sources into ChromaDB |
| `lake sync --source <name>` | Sync a specific source |
| `lake sync --rebuild` | Delete all vectors and re-sync everything |
| `lake prune` | Remove stale collections not in current config |
| `lake prune --dry-run` | Preview what would be pruned without deleting |
| `lake serve` | Start the MCP server (stdio mode) |
| `lake status` | Show sync status for all sources |

## Data

ChromaDB vectors are stored at:

```
~/.local/share/lake-of-vectors/chromadb
```

## Architecture

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                      lake-of-vectors                             │                                                                   
  │                                                                  │
  │  ┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐   │                                                                    
  │  │  Publishers │──▶│   Sync Engine    │──▶│    ChromaDB      │   │                                                                    
  │  │             │   │                  │   │    (on-disk)     │   │                                                                    
  │  │ • Markdown  │   │ • Chunking       │   │                  │   │                                                                    
  │  │ • SQLite    │   │ • Content hash   │   │ one collection   │   │                                                                    
  │  │ • Plaintext │   │   diffing        │   │ per source       │   │                                                                    
  │  └─────────────┘   │ • Embedding      │   └────────┬─────────┘   │                                                                    
  │                    │ • ChromaDB upsert│            │             │                                                                    
  │                    └──────────────────┘            │             │                                                                    
  │                                                    │             │                                                                  
  │  ┌─────────────────────┐   ┌──────────────────┐    │             │                                                                     
  │  │  Embedding Backends │   │   MCP Server     │◀───┘             │                                                                     
  │  │                     │   │   (stdio)        │                  │                                                                     
  │  │ • Local             │   │                  │                  │                                                                     
  │  │   (sentence-        │   │ • semantic_search│                  │                                                                     
  │  │    transformers)    │   │ • list_sources   │                  │                                                                   
  │  │ • OpenAI API        │   └──────────────────┘                  │                                                                     
  │  └─────────────────────┘                                         │                                                                  
  │                                                                  │                                                                   
  │  CLI: lake sync | lake serve | lake prune | lake status          │                                                                 
  └──────────────────────────────────────────────────────────────────┘  
```

## License

MIT
