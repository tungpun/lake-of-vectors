import pytest
from pathlib import Path
from lake_of_vectors.publishers.markdown import MarkdownPublisher
from lake_of_vectors.publishers.base import Document, compute_hash


def test_crawl_finds_markdown_files(tmp_path):
    (tmp_path / "note1.md").write_text("# Hello\nThis is note 1.")
    (tmp_path / "note2.md").write_text("# World\nThis is note 2.")
    (tmp_path / "readme.txt").write_text("Not a markdown file.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)


def test_crawl_recursive(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    (tmp_path / "root.md").write_text("Root note.")
    (sub / "nested.md").write_text("Nested note.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2


def test_document_source_id_is_absolute_path(tmp_path):
    (tmp_path / "note.md").write_text("Content here.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].source_id == str(tmp_path / "note.md")


def test_document_content_hash(tmp_path):
    content = "# Test\nSome content."
    (tmp_path / "note.md").write_text(content)

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].content_hash == compute_hash(content)


def test_document_metadata_has_title_from_h1(tmp_path):
    (tmp_path / "note.md").write_text("# My Title\nBody text.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["title"] == "My Title"


def test_document_metadata_title_fallback_to_filename(tmp_path):
    (tmp_path / "note.md").write_text("No heading here, just text.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["title"] == "note"


def test_document_metadata_has_relative_path(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    (sub / "deep.md").write_text("# Deep\nContent.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["relative_path"] == "a/b/deep.md"


def test_crawl_empty_directory(tmp_path):
    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())
    assert docs == []


def test_crawl_skips_empty_files(tmp_path):
    (tmp_path / "empty.md").write_text("")
    (tmp_path / "real.md").write_text("Has content.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 1
    assert docs[0].metadata["title"] == "real"


def test_document_metadata_has_directory(tmp_path):
    sub = tmp_path / "security" / "web"
    sub.mkdir(parents=True)
    (sub / "xss.md").write_text("# XSS\nContent.")
    (tmp_path / "root.md").write_text("# Root\nContent.")

    publisher = MarkdownPublisher(path=tmp_path)
    docs = {d.metadata["relative_path"]: d for d in publisher.crawl()}

    assert docs["security/web/xss.md"].metadata["directory"] == "security/web"
    assert docs["root.md"].metadata["directory"] == ""
