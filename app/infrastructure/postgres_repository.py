"""Infrastructure layer: a concrete ArticleRepository backed by PostgreSQL.

Used when DATABASE_URL is set. Nothing is kept in memory, so any number of
replicas can share one database. Like the JSON adapter, it never crashes
startup: if the database is unreachable it reports not-ready, and calls
fail with StorageUnavailable (503) until the database is back.

Tables come from Alembic migrations (`migrations/`), applied before the
service starts. This adapter never creates or changes them.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.application.ports import StorageUnavailable
from app.domain.models import Article, ArticleStatus, Author, Category
from app.infrastructure.json_repository import JsonArticleRepository

logger = logging.getLogger(__name__)

_COLUMNS = (
    "id, slug, title, summary, content, category, author_id, author_name, source, "
    "published_at, updated_at, status, tags, image_url, language, is_featured, "
    "read_time_minutes, view_count"
)


class PostgresArticleRepository:
    def __init__(self, database_url: str, seed_file: str | None = None) -> None:
        self._seed_file = seed_file
        self._seed_checked = False
        # Design for failure: short connect/pool timeouts and a statement
        # timeout, so a slow or dead database turns into a fast 503.
        self._pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=5,
            timeout=2,
            open=False,
            kwargs={"row_factory": dict_row, "connect_timeout": 2, "options": "-c statement_timeout=5000"},
        )
        # wait=False: don't block startup on the database; connections are
        # retried in the background and /health/ready reflects the result.
        self._pool.open(wait=False)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection]:
        # The pool commits on success and rolls back if the block raises.
        try:
            with self._pool.connection() as conn:
                if not self._seed_checked:
                    self._seed_if_empty(conn)
                yield conn
        except (psycopg.Error, PoolTimeout) as exc:
            logger.error("Database error", extra={"error": str(exc)})
            raise StorageUnavailable("Article storage is unavailable") from exc

    def _seed_if_empty(self, conn: psycopg.Connection) -> None:
        # If migrations haven't run yet, the table is missing: this raises,
        # the service reports not-ready, and the next call tries again.
        empty = conn.execute("SELECT NOT EXISTS (SELECT 1 FROM articles) AS empty").fetchone()["empty"]
        if empty and self._seed_file:
            # Reuse the JSON adapter to parse and validate the seed file.
            seed = JsonArticleRepository(self._seed_file).list_all()
            with conn.cursor() as cur:
                cur.executemany(
                    f"INSERT INTO articles ({_COLUMNS}) VALUES "
                    "(%(id)s, %(slug)s, %(title)s, %(summary)s, %(content)s, %(category)s, "
                    "%(author_id)s, %(author_name)s, %(source)s, %(published_at)s, %(updated_at)s, "
                    "%(status)s, %(tags)s, %(image_url)s, %(language)s, %(is_featured)s, "
                    "%(read_time_minutes)s, %(view_count)s) "
                    "ON CONFLICT DO NOTHING",
                    [self._to_record(a) for a in seed],
                )
            logger.info("Seeded articles", extra={"count": len(seed), "path": self._seed_file})
        conn.commit()
        self._seed_checked = True

    @staticmethod
    def _to_domain(row: dict) -> Article:
        return Article(
            id=row["id"],
            slug=row["slug"],
            title=row["title"],
            summary=row["summary"],
            content=row["content"],
            category=Category(row["category"]),
            author=Author(id=row["author_id"], name=row["author_name"]),
            source=row["source"],
            published_at=row["published_at"],
            updated_at=row["updated_at"],
            status=ArticleStatus(row["status"]),
            tags=tuple(row["tags"]),
            image_url=row["image_url"],
            language=row["language"],
            is_featured=row["is_featured"],
            read_time_minutes=row["read_time_minutes"],
            view_count=row["view_count"],
        )

    @staticmethod
    def _to_record(article: Article) -> dict:
        return {
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "category": article.category.value,
            "author_id": article.author.id,
            "author_name": article.author.name,
            "source": article.source,
            "published_at": article.published_at,
            "updated_at": article.updated_at,
            "status": article.status.value,
            "tags": list(article.tags),
            "image_url": article.image_url,
            "language": article.language,
            "is_featured": article.is_featured,
            "read_time_minutes": article.read_time_minutes,
            "view_count": article.view_count,
        }

    def list_all(self) -> list[Article]:
        with self._connection() as conn:
            rows = conn.execute(f"SELECT {_COLUMNS} FROM articles").fetchall()
        return [self._to_domain(r) for r in rows]

    def get_by_id(self, article_id: str) -> Article | None:
        with self._connection() as conn:
            row = conn.execute(f"SELECT {_COLUMNS} FROM articles WHERE id = %s", (article_id,)).fetchone()
        return self._to_domain(row) if row else None

    def get_by_slug(self, slug: str) -> Article | None:
        with self._connection() as conn:
            row = conn.execute(f"SELECT {_COLUMNS} FROM articles WHERE slug = %s", (slug,)).fetchone()
        return self._to_domain(row) if row else None

    def is_ready(self) -> bool:
        try:
            with self._connection() as conn:
                conn.execute("SELECT 1")
        except StorageUnavailable:
            return False
        return True

    def close(self) -> None:
        self._pool.close()
