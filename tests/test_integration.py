import pytest
from pathlib import Path
from lake_of_embeddings.publishers.markdown import MarkdownPublisher
from lake_of_embeddings.sync.engine import SyncEngine


class FakeEmbedder:
    """Deterministic embedder for integration tests."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            h = hash(text) % 1000
            results.append([h / 1000.0, (h + 1) / 1000.0, (h + 2) / 1000.0])
        return results

    @property
    def model_name(self) -> str:
        return "fake:integration"


@pytest.fixture
def setup(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "ssrf.md").write_text(
        "# SSRF\nServer-Side Request Forgery allows an attacker to make "
        "requests from the server to internal resources."
    )
    (notes_dir / "sqli.md").write_text(
        "# SQL Injection\nSQL injection is a code injection technique that "
        "exploits security vulnerabilities in database queries."
    )
    (notes_dir / "xss.md").write_text(
        "# Cross-Site Scripting\nXSS attacks inject malicious scripts into "
        "web pages viewed by other users."
    )

    engine = SyncEngine(
        chromadb_path=str(tmp_path / "chromadb"),
        embedder=FakeEmbedder(),
    )
    return notes_dir, engine


def test_full_sync_and_search(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)

    report = engine.sync("security-notes", publisher.crawl())
    assert report.added == 3
    assert report.deleted == 0

    results = engine.search("server request forgery", limit=3)
    assert len(results) > 0
    assert all("chunk_text" in r for r in results)


def test_sync_detects_changes(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)

    engine.sync("security-notes", publisher.crawl())

    (notes_dir / "ssrf.md").write_text(
        "# SSRF Updated\nNew content about SSRF with blind techniques."
    )

    publisher2 = MarkdownPublisher(path=notes_dir)
    report = engine.sync("security-notes", publisher2.crawl())
    assert report.updated == 1
    assert report.unchanged == 2


def test_sync_detects_deletions(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)

    engine.sync("security-notes", publisher.crawl())

    (notes_dir / "xss.md").unlink()

    publisher2 = MarkdownPublisher(path=notes_dir)
    report = engine.sync("security-notes", publisher2.crawl())
    assert report.deleted == 1
    assert report.unchanged == 2


def test_list_sources_and_stats(setup):
    notes_dir, engine = setup
    publisher = MarkdownPublisher(path=notes_dir)
    engine.sync("security-notes", publisher.crawl())

    sources = engine.list_sources()
    assert "security-notes" in sources

    stats = engine.get_source_stats("security-notes")
    assert stats["chunk_count"] > 0
    assert stats["embedding_model"] == "fake:integration"
