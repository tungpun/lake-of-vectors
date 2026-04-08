import pytest
from pathlib import Path
from lake_of_vectors.publishers.plaintext import PlaintextPublisher
from lake_of_vectors.publishers.base import Document, compute_hash


def test_crawl_finds_txt_files(tmp_path):
    (tmp_path / "a.txt").write_text("File A content.")
    (tmp_path / "b.txt").write_text("File B content.")
    (tmp_path / "c.md").write_text("Not a txt file.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)


def test_crawl_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.txt").write_text("Root.")
    (sub / "nested.txt").write_text("Nested.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 2


def test_source_id_is_absolute_path(tmp_path):
    (tmp_path / "note.txt").write_text("Content.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].source_id == str(tmp_path / "note.txt")


def test_metadata_has_filename_and_relative_path(tmp_path):
    sub = tmp_path / "dir"
    sub.mkdir()
    (sub / "file.txt").write_text("Content.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].metadata["filename"] == "file.txt"
    assert docs[0].metadata["relative_path"] == "dir/file.txt"


def test_content_hash_matches(tmp_path):
    content = "Some plaintext content."
    (tmp_path / "note.txt").write_text(content)

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert docs[0].content_hash == compute_hash(content)


def test_skips_empty_files(tmp_path):
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "real.txt").write_text("Has content.")

    publisher = PlaintextPublisher(path=tmp_path)
    docs = list(publisher.crawl())

    assert len(docs) == 1
