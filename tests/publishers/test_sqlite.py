import sqlite3
import pytest
from pathlib import Path
from lake_of_vectors.publishers.sqlite import SqlitePublisher
from lake_of_vectors.publishers.base import Document, compute_hash


@pytest.fixture
def sample_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            body TEXT,
            title TEXT,
            tags TEXT
        )
    """)
    conn.execute(
        "INSERT INTO notes (body, title, tags) VALUES (?, ?, ?)",
        ("SSRF attack techniques and mitigations.", "SSRF Guide", "security,web"),
    )
    conn.execute(
        "INSERT INTO notes (body, title, tags) VALUES (?, ?, ?)",
        ("SQL injection prevention strategies.", "SQLi Prevention", "security,db"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_crawl_returns_documents(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=["title", "tags"],
    )
    docs = list(publisher.crawl())

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)


def test_source_id_format(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=["title", "tags"],
    )
    docs = list(publisher.crawl())

    assert docs[0].source_id == f"{sample_db}:notes:1"
    assert docs[1].source_id == f"{sample_db}:notes:2"


def test_content_is_body_column(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=[],
    )
    docs = list(publisher.crawl())

    assert docs[0].content == "SSRF attack techniques and mitigations."


def test_metadata_includes_configured_columns(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=["title", "tags"],
    )
    docs = list(publisher.crawl())

    assert docs[0].metadata["title"] == "SSRF Guide"
    assert docs[0].metadata["tags"] == "security,web"
    assert docs[0].metadata["table"] == "notes"


def test_content_hash_matches(sample_db):
    publisher = SqlitePublisher(
        path=sample_db,
        table="notes",
        content_column="body",
        metadata_columns=[],
    )
    docs = list(publisher.crawl())

    expected = compute_hash("SSRF attack techniques and mitigations.")
    assert docs[0].content_hash == expected


def test_skips_rows_with_null_content(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO notes (body) VALUES (NULL)")
    conn.execute("INSERT INTO notes (body) VALUES ('Real content.')")
    conn.commit()
    conn.close()

    publisher = SqlitePublisher(
        path=db_path, table="notes", content_column="body", metadata_columns=[]
    )
    docs = list(publisher.crawl())

    assert len(docs) == 1


def test_skips_rows_with_empty_content(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
    conn.execute("INSERT INTO notes (body) VALUES ('')")
    conn.execute("INSERT INTO notes (body) VALUES ('Real content.')")
    conn.commit()
    conn.close()

    publisher = SqlitePublisher(
        path=db_path, table="notes", content_column="body", metadata_columns=[]
    )
    docs = list(publisher.crawl())

    assert len(docs) == 1
