#!/usr/bin/env python3
"""
Manual search script for testing ChromaDB content without the MCP server.

Usage:
    python scripts/search.py "your query here"
    python scripts/search.py "your query here" --source security-notes
    python scripts/search.py "your query here" --limit 5
"""

import argparse
from pathlib import Path

from lake_of_embeddings.config import load_config, default_config_path
from lake_of_embeddings.embeddings.local import LocalEmbedder
from lake_of_embeddings.sync.engine import SyncEngine

CHROMADB_PATH = Path("~/.local/share/lake-of-embeddings/chromadb").expanduser()


def main():
    parser = argparse.ArgumentParser(description="Search lake-of-embeddings")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--source", default=None, help="Limit to a specific source name")
    parser.add_argument("--limit", type=int, default=5, help="Number of results (default: 5)")
    args = parser.parse_args()

    config = load_config(default_config_path())

    if config.embedding.backend == "local":
        embedder = LocalEmbedder(model=config.embedding.model)
    elif config.embedding.backend == "openai":
        from lake_of_embeddings.embeddings.api import APIEmbedder
        embedder = APIEmbedder(model=config.embedding.model, api_key=config.embedding.api_key)
    else:
        raise SystemExit(f"Unknown embedding backend: {config.embedding.backend}")

    engine = SyncEngine(chromadb_path=str(CHROMADB_PATH), embedder=embedder)

    sources = engine.list_sources()
    if not sources:
        raise SystemExit("No sources synced yet. Run 'lake sync' first.")

    results = engine.search(args.query, source=args.source, limit=args.limit)

    if not results:
        print("No results found.")
        return

    print(f"\nQuery: {args.query!r}")
    print(f"Results: {len(results)}\n")
    print("─" * 60)

    for i, r in enumerate(results, 1):
        distance = r.get("distance", 0)
        score = 1 - distance  # cosine similarity approximation
        source = r.get("source", "unknown")
        meta = {k: v for k, v in r.items() if k not in ("chunk_text", "source", "distance")}

        print(f"[{i}] score={score:.3f}  source={source}")
        if meta:
            for k, v in meta.items():
                print(f"    {k}: {v}")
        print()
        print(r["chunk_text"])
        print("─" * 60)


if __name__ == "__main__":
    main()
