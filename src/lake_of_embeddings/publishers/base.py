from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable
import hashlib


@dataclass
class Document:
    source_id: str
    content: str
    metadata: dict
    content_hash: str


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@runtime_checkable
class Publisher(Protocol):
    def crawl(self) -> Iterator[Document]:
        ...
