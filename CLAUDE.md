## Project

Local semantic search over personal knowledge bases (Obsidian, SQLite, plaintext). Indexes into ChromaDB, exposed to Claude via MCP.

## Docs

- `docs/2026-04-03-lake-of-embeddings-design.md` — design spec and motivation
- `docs/2026-04-03-lake-of-embeddings-plan.md` — implementation plan

## Setup

Run `./init.sh` to install dependencies.

## Commands

- `lake sync` — index sources
- `lake serve` — start MCP server
- `lake status` — check sync state
- `pytest` — run tests

## Key paths

- Config: `~/.config/lake-of-vectors/config.yaml` (see `config.example.yaml`)
- Data: `~/.local/share/lake-of-vectors/chromadb`
- Source: `src/lake_of_vectors/`
