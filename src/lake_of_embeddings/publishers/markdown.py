import re
from pathlib import Path
from typing import Iterator

from .base import Document, Publisher, compute_hash


class MarkdownPublisher:
    def __init__(self, path: Path):
        self.path = Path(path)

    def crawl(self) -> Iterator[Document]:
        for md_file in sorted(self.path.rglob("*.md")):
            if not md_file.is_file():
                continue
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                continue

            title = self._extract_title(content, md_file)
            relative_path = str(md_file.relative_to(self.path))

            yield Document(
                source_id=str(md_file),
                content=content,
                metadata={
                    "title": title,
                    "relative_path": relative_path,
                    "directory": str(md_file.parent.relative_to(self.path))
                    if md_file.parent != self.path
                    else "",
                },
                content_hash=compute_hash(content),
            )

    def _extract_title(self, content: str, file_path: Path) -> str:
        match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return file_path.stem
