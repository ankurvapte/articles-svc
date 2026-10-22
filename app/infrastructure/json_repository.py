"""Infrastructure layer: a concrete ArticleRepository backed by a JSON file.

This is the only place that knows the data lives in a file. Later, a
PostgresArticleRepository can replace it without touching other layers.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from app.domain.models import Article, ArticleStatus, Author, Category

logger = logging.getLogger(__name__)


class JsonArticleRepository:
    def __init__(self, data_file: str | Path) -> None:
        self._path = Path(data_file)
        self._articles: dict[str, Article] = {}
        self._by_slug: dict[str, Article] = {}
        self._loaded = False
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            articles = [self._to_domain(item) for item in raw]
        except (OSError, ValueError, KeyError) as exc:
            # Don't crash on startup: report not-ready so the orchestrator
            # keeps traffic away instead of restart-looping the container.
            logger.error("Failed to load articles", extra={"path": str(self._path), "error": str(exc)})
            return
        self._articles = {a.id: a for a in articles}
        self._by_slug = {a.slug: a for a in articles}
        self._loaded = True
        logger.info("Loaded articles", extra={"count": len(articles), "path": str(self._path)})

    @staticmethod
    def _to_domain(item: dict) -> Article:
        return Article(
            id=item["id"],
            slug=item["slug"],
            title=item["title"],
            summary=item["summary"],
            content=item["content"],
            category=Category(item["category"]),
            author=Author(**item["author"]),
            source=item["source"],
            published_at=datetime.fromisoformat(item["published_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            status=ArticleStatus(item.get("status", "published")),
            tags=tuple(t.lower() for t in item.get("tags", [])),
            image_url=item.get("image_url"),
            language=item.get("language", "en"),
            is_featured=item.get("is_featured", False),
            read_time_minutes=item.get("read_time_minutes", 1),
            view_count=item.get("view_count", 0),
        )

    def list_all(self) -> list[Article]:
        return list(self._articles.values())

    def get_by_id(self, article_id: str) -> Article | None:
        return self._articles.get(article_id)

    def get_by_slug(self, slug: str) -> Article | None:
        return self._by_slug.get(slug)

    def is_ready(self) -> bool:
        return self._loaded
