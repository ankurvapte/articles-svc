"""API contract: response shapes exposed over HTTP (pillar 6).

Kept separate from domain models so the public contract can evolve
(v1, v2) without changing business entities, and vice versa.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.models import Article


class AuthorOut(BaseModel):
    id: str
    name: str


class ArticleSummaryOut(BaseModel):
    """Lightweight shape for lists: no full content."""
    id: str
    slug: str
    title: str
    summary: str
    category: str
    tags: list[str]
    author: AuthorOut
    image_url: str | None
    is_featured: bool
    read_time_minutes: int
    published_at: datetime

    @classmethod
    def from_domain(cls, a: Article) -> "ArticleSummaryOut":
        return cls(
            id=a.id, slug=a.slug, title=a.title, summary=a.summary,
            category=a.category.value, tags=list(a.tags),
            author=AuthorOut(id=a.author.id, name=a.author.name),
            image_url=a.image_url, is_featured=a.is_featured,
            read_time_minutes=a.read_time_minutes, published_at=a.published_at,
        )


class ArticleDetailOut(ArticleSummaryOut):
    content: str
    source: str
    language: str
    view_count: int
    updated_at: datetime

    @classmethod
    def from_domain(cls, a: Article) -> "ArticleDetailOut":
        base = ArticleSummaryOut.from_domain(a).model_dump()
        return cls(
            **base, content=a.content, source=a.source, language=a.language,
            view_count=a.view_count, updated_at=a.updated_at,
        )


class PaginationOut(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class ArticleListOut(BaseModel):
    data: list[ArticleSummaryOut]
    pagination: PaginationOut


class CategoryOut(BaseModel):
    name: str
    article_count: int


class ErrorOut(BaseModel):
    """One consistent error format for every endpoint."""
    error: str
    message: str
    request_id: str | None = None
