import pytest
from lake_of_embeddings.sync.engine import SyncEngine
from lake_of_embeddings.publishers.base import Document, compute_hash


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
