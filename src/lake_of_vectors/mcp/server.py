from mcp.server.fastmcp import FastMCP

from lake_of_vectors.sync.engine import SyncEngine


def create_mcp_server(engine: SyncEngine) -> FastMCP:
    mcp = FastMCP("lake-of-vectors")

    @mcp.tool()
    def semantic_search(query: str, source: str = "", limit: int = 10) -> str:
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
            similarity = max(0.0, 1.0 - r["distance"])

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
