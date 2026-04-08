from pathlib import Path
from typing import Iterator

from .base import Document, compute_hash


class PlaintextPublisher:
    def __init__(self, path: Path):
        self.path = Path(path)

    def crawl(self) -> Iterator[Document]:
        for txt_file in sorted(self.path.rglob("*.txt")):
            if not txt_file.is_file():
                continue
            content = txt_file.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                continue

            yield Document(
                source_id=str(txt_file),
                content=content,
                metadata={
                    "filename": txt_file.name,
                    "relative_path": str(txt_file.relative_to(self.path)),
                },
                content_hash=compute_hash(content),
            )
