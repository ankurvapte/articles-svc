"""Application layer: what the service can do (its use cases).

Orchestrates domain objects through the repository port. Knows nothing
about HTTP status codes, request objects or where data is stored.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum

from app.application.ports import ArticleRepository
from app.domain.models import Article, Category


class ArticleNotFound(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Article '{key}' not found")
        self.key = key


class SortOrder(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_VIEWED = "most_viewed"


@dataclass(frozen=True)
class ArticleFilter:
    category: Category | None = None
    tag: str | None = None
    author_id: str | None = None
    featured: bool | None = None
    query: str | None = None


@dataclass(frozen=True)
class Page:
    items: list[Article]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.total else 0


class ArticleService:
    def __init__(self, repository: ArticleRepository) -> None:
        self._repo = repository

    def list_articles(
        self,
        filters: ArticleFilter = ArticleFilter(),
        sort: SortOrder = SortOrder.NEWEST,
        page: int = 1,
        page_size: int = 10,
    ) -> Page:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")

        articles = [a for a in self._repo.list_all() if a.is_public]

        if filters.category:
            articles = [a for a in articles if a.category == filters.category]
        if filters.tag:
            tag = filters.tag.lower()
            articles = [a for a in articles if tag in a.tags]
        if filters.author_id:
            articles = [a for a in articles if a.author.id == filters.author_id]
        if filters.featured is not None:
            articles = [a for a in articles if a.is_featured == filters.featured]
        if filters.query:
            articles = [a for a in articles if a.matches_text(filters.query)]

        if sort == SortOrder.MOST_VIEWED:
            articles.sort(key=lambda a: a.view_count, reverse=True)
        else:
            articles.sort(key=lambda a: a.published_at, reverse=(sort == SortOrder.NEWEST))

        start = (page - 1) * page_size
        return Page(items=articles[start : start + page_size], total=len(articles), page=page, page_size=page_size)

    def get_article(self, article_id: str) -> Article:
        article = self._repo.get_by_id(article_id)
        if article is None or not article.is_public:
            raise ArticleNotFound(article_id)
        return article

    def get_article_by_slug(self, slug: str) -> Article:
        article = self._repo.get_by_slug(slug)
        if article is None or not article.is_public:
            raise ArticleNotFound(slug)
        return article

    def category_counts(self) -> dict[str, int]:
        counts = Counter(a.category.value for a in self._repo.list_all() if a.is_public)
        return dict(sorted(counts.items()))
