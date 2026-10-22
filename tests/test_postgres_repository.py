"""Contract tests for PostgresArticleRepository.

Needs a throwaway Postgres; the tests drop and recreate the articles table:

    docker run --rm -d --name articles-test-db -e POSTGRES_PASSWORD=test -p 55433:5432 postgres:17-alpine
    TEST_DATABASE_URL=postgresql://postgres:test@localhost:55433/postgres pytest tests/test_postgres_repository.py
    docker stop articles-test-db

Without TEST_DATABASE_URL only the "database down" test runs.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402

from app.application.ports import StorageUnavailable  # noqa: E402
from app.application.use_cases import ArticleFilter, ArticleService  # noqa: E402
from app.domain.models import Category  # noqa: E402
from app.infrastructure.json_repository import JsonArticleRepository  # noqa: E402
from app.infrastructure.postgres_repository import PostgresArticleRepository  # noqa: E402

DB_URL = os.getenv("TEST_DATABASE_URL")
SEED = ROOT / "data" / "news.json"
METRO = "a1f3c2e0-0001-4c1a-9b10-000000000001"
METRO_SLUG = "bengaluru-metro-yellow-line-ridership-milestone"


class DatabaseDownTests(unittest.TestCase):
    def test_unreachable_database_is_not_ready_and_raises_storage_unavailable(self):
        repo = PostgresArticleRepository("postgresql://nobody:nothing@127.0.0.1:1/none")
        try:
            self.assertFalse(repo.is_ready())
            with self.assertRaises(StorageUnavailable):
                repo.get_by_id(METRO)
        finally:
            repo.close()


@unittest.skipUnless(DB_URL, "set TEST_DATABASE_URL to run Postgres tests")
class PostgresArticleRepositoryTests(unittest.TestCase):
    def setUp(self):
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            conn.execute("DROP TABLE IF EXISTS articles")
        self.repo = PostgresArticleRepository(DB_URL, seed_file=str(SEED))

    def tearDown(self):
        self.repo.close()

    def test_creates_schema_and_seeds_empty_table(self):
        self.assertTrue(self.repo.is_ready())
        self.assertEqual(len(self.repo.list_all()), 10)

    def test_seed_runs_only_once(self):
        self.repo.list_all()
        second = PostgresArticleRepository(DB_URL, seed_file=str(SEED))
        try:
            self.assertEqual(len(second.list_all()), 10)
        finally:
            second.close()

    def test_round_trips_every_seed_article(self):
        # Same entities as the JSON adapter: tags, author, enums and
        # timestamps (same instant; Postgres returns them in UTC) all survive.
        expected = {a.id: a for a in JsonArticleRepository(SEED).list_all()}
        self.assertEqual({a.id: a for a in self.repo.list_all()}, expected)

    def test_lookups(self):
        article = self.repo.get_by_id(METRO)
        self.assertEqual(article.slug, METRO_SLUG)
        self.assertEqual(self.repo.get_by_slug(METRO_SLUG), article)
        self.assertIsNone(self.repo.get_by_id("nope"))
        self.assertIsNone(self.repo.get_by_slug("nope"))

    def test_works_behind_the_use_cases(self):
        service = ArticleService(self.repo)
        page = service.list_articles(ArticleFilter(category=Category.BUSINESS))
        self.assertEqual(page.total, 2)
        self.assertEqual(service.get_article_by_slug(METRO_SLUG).id, METRO)


if __name__ == "__main__":
    unittest.main()
