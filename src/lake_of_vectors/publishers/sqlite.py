import sqlite3
from pathlib import Path
from typing import Iterator

from .base import Document, compute_hash


class SqlitePublisher:
    def __init__(
        self,
        path: Path,
        table: str,
        content_column: str,
        metadata_columns: list[str],
    ):
        self.path = Path(path)
        self.table = table
        self.content_column = content_column
        self.metadata_columns = metadata_columns

    def crawl(self) -> Iterator[Document]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            columns = ["rowid AS rowid", self.content_column] + self.metadata_columns
            query = f"SELECT {', '.join(columns)} FROM {self.table}"
            for row in conn.execute(query):
                content = row[self.content_column]
                if not content or not str(content).strip():
                    continue

                content = str(content)
                metadata = {"table": self.table}
                for col in self.metadata_columns:
                    metadata[col] = row[col]

                yield Document(
                    source_id=f"{self.path}:{self.table}:{row['rowid']}",
                    content=content,
                    metadata=metadata,
                    content_hash=compute_hash(content),
                )
        finally:
            conn.close()
