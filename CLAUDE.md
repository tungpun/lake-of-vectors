## Project

Local semantic search over personal knowledge bases (Obsidian, SQLite, plaintext). Indexes into ChromaDB, exposed to Claude via MCP.

## Agent Workflow

At session start: read `STATUS.md` (feature state) and `TASKS.md` (current tasks).
At session end: update `TASKS.md` — mark completed tasks, add new ones, append a session note.

## Docs

- `features-list.md` — implemented vs. planned features
- `tasks-list.md` — structured task list for agents
- `docs/design.md` — design spec and motivation
- `docs/plan.md` — implementation plan

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
