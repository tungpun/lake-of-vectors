from dataclasses import dataclass
from typing import Iterator

import chromadb

from lake_of_embeddings.embeddings.base import Embedder
from lake_of_embeddings.publishers.base import Document
from lake_of_embeddings.sync.chunker import chunk_text


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
        documents_list = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.source_id}::chunk_{i}"
            ids.append(chunk_id)
            documents_list.append(chunk)
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
            documents=documents_list,
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
            "embedding_model": collection.metadata.get("embedding_model", "unknown"),
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
            for i in range(len(results["ids"][0])):
                all_results.append({
                    "chunk_text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "source_name": collection.name,
                })

        # Sort by distance (lower = more similar) and take top limit
        all_results.sort(key=lambda r: r["distance"])
        return all_results[:limit]
