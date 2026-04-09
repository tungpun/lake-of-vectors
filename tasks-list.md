# Task List

Agent instructions:
- Read this file at the start of each session
- Update task state as you work (`[ ]` → `[~]` in progress, `[x]` done)
- Add new tasks discovered during work
- Update "Last updated" and append a session note when done

Last updated: 2026-04-09

- [x] Project scaffolding (pyproject.toml, package structure)
- [x] Config loading
- [x] Publishers: Markdown, Plaintext, SQLite
- [x] Embedding backends: Local (sentence-transformers), OpenAI API
- [x] Sync engine with content hash diffing
- [x] MCP server with `semantic_search` + `list_sources`
- [x] CLI: `lake sync`, `lake serve`, `lake status`, `lake prune`
- [x] Unit + integration tests
- [ ] Add NotionPublisher — see `docs/design.md`
- [ ] Add ConfluencePublisher — same doc
- [ ] Add `lake sync --watch` mode for incremental re-sync on file change
- [ ] Improve chunker to respect Markdown heading boundaries
- [ ] Add `lake search` CLI command for quick terminal queries (wraps semantic_search without MCP)

---

## Session Notes

- 2026-04-09: Created CLAUDE.md, init.sh, features-list.md, tasks-list.md
