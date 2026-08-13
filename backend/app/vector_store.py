from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, Protocol

@dataclass
class Statute:
    id: str
    chapter: str
    section: str
    title: str
    text: str
    embedding: Optional[list[float]] = None

class VectorStore(Protocol):
    def seed(self, statutes: list[Statute]) -> None: ...
    def search(self, embedding: list[float], k: int) -> list[Statute]: ...

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

class LocalVectorStore:
    def __init__(self) -> None:
        self._items: list[Statute] = []

    def seed(self, statutes: list[Statute]) -> None:
        self._items = list(statutes)

    def search(self, embedding: list[float], k: int) -> list[Statute]:
        scored = sorted(self._items,
                        key=lambda s: _cosine(embedding, s.embedding or []),
                        reverse=True)
        return scored[:k]
