"""Domain layer: the core business entities.

Pure Python only. No FastAPI, no database, no JSON parsing here.
Everything else in the service depends on this module; it depends on nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Category(str, Enum):
    CITY = "city"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SPORTS = "sports"
    WEATHER = "weather"
    HEALTH = "health"
    SCIENCE = "science"
    ENTERTAINMENT = "entertainment"


class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class Author:
    id: str
    name: str


@dataclass(frozen=True)
class Article:
    id: str
    slug: str
    title: str
    summary: str
    content: str
    category: Category
    author: Author
    source: str
    published_at: datetime
    updated_at: datetime
    status: ArticleStatus = ArticleStatus.PUBLISHED
    tags: tuple[str, ...] = field(default_factory=tuple)
    image_url: str | None = None
    language: str = "en"
    is_featured: bool = False
    read_time_minutes: int = 1
    view_count: int = 0

    def __post_init__(self) -> None:
        # Business rules live with the entity, not in the HTTP layer.
        if not self.title.strip():
            raise ValueError("Article title cannot be empty")
        if self.updated_at < self.published_at:
            raise ValueError("updated_at cannot be earlier than published_at")
        if self.read_time_minutes < 1:
            raise ValueError("read_time_minutes must be at least 1")

    @property
    def is_public(self) -> bool:
        return self.status == ArticleStatus.PUBLISHED

    def matches_text(self, query: str) -> bool:
        q = query.lower()
        return q in self.title.lower() or q in self.summary.lower() or any(q in t for t in self.tags)
