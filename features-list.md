# Feature List

Last updated: 2026-04-09

- [x] Config loading (`~/.config/lake-of-vectors/config.yaml`)
- [x] MarkdownPublisher — recursive `.md` crawl with title extraction
- [x] PlaintextPublisher — recursive `.txt` crawl
- [x] SqlitePublisher — configurable table/column crawl
- [x] LocalEmbedder — sentence-transformers (`all-MiniLM-L6-v2`)
- [x] APIEmbedder — OpenAI embeddings
- [x] Sync engine — content hash diffing, chunk/embed/upsert, delete stale
- [x] Chunker — recursive text splitter (~500 tokens, ~50 overlap)
- [x] MCP server — `semantic_search` and `list_sources` tools (stdio)
- [x] CLI — `lake sync`, `lake serve`, `lake status`, `lake prune`
- [x] Tests — unit tests for all modules + integration tests
- [ ] NotionPublisher
- [ ] ConfluencePublisher
- [ ] Web UI for browsing indexed content
- [ ] `lake sync --watch` — incremental re-sync on file change
