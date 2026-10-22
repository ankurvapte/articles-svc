"""Ports: interfaces the application layer needs from the outside world.

Use cases depend on this abstraction, never on a concrete database.
Swapping the JSON file for Postgres later means writing a new class that
satisfies this Protocol. Nothing in the use cases or API changes.
"""
from __future__ import annotations

from typing import Protocol

from app.domain.models import Article


class ArticleRepository(Protocol):
    def list_all(self) -> list[Article]: ...

    def get_by_id(self, article_id: str) -> Article | None: ...

    def get_by_slug(self, slug: str) -> Article | None: ...

    def is_ready(self) -> bool: ...
