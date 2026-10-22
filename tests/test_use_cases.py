"""Unit tests for domain + application layers.

No FastAPI, no web server, no container needed. Runs with either:
    python -m unittest discover -s tests -p "test_use_cases.py"
    pytest tests/test_use_cases.py
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.application.use_cases import (  # noqa: E402
    ArticleFilter, ArticleNotFound, ArticleService, SortOrder,
)
from app.domain.models import Article, Author, Category  # noqa: E402
from app.infrastructure.json_repository import JsonArticleRepository  # noqa: E402

DATA = ROOT / "data" / "news.json"


class ArticleServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = JsonArticleRepository(DATA)
        self.service = ArticleService(self.repo)

    def test_loads_all_ten_articles(self):
        self.assertTrue(self.repo.is_ready())
        self.assertEqual(self.service.list_articles(page_size=50).total, 10)

    def test_default_sort_is_newest_first(self):
        items = self.service.list_articles(page_size=50).items
        dates = [a.published_at for a in items]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_most_viewed_sort(self):
        items = self.service.list_articles(sort=SortOrder.MOST_VIEWED, page_size=50).items
        self.assertEqual(items[0].view_count, max(a.view_count for a in items))

    def test_filter_by_category(self):
        page = self.service.list_articles(ArticleFilter(category=Category.TECHNOLOGY))
        self.assertEqual(page.total, 2)
        self.assertTrue(all(a.category == Category.TECHNOLOGY for a in page.items))

    def test_filter_by_tag_and_featured(self):
        self.assertEqual(self.service.list_articles(ArticleFilter(tag="Containers")).total, 1)
        self.assertEqual(self.service.list_articles(ArticleFilter(featured=True)).total, 4)

    def test_text_search(self):
        page = self.service.list_articles(ArticleFilter(query="kubernetes"))
        self.assertEqual([a.slug for a in page.items], ["kubernetes-skills-demand-india-jobs"])

    def test_pagination(self):
        p2 = self.service.list_articles(page=2, page_size=4)
        self.assertEqual((len(p2.items), p2.total, p2.total_pages), (4, 10, 3))
        p3 = self.service.list_articles(page=3, page_size=4)
        self.assertEqual(len(p3.items), 2)

    def test_get_by_id_and_slug(self):
        a = self.service.get_article("a1f3c2e0-0004-4c1a-9b10-000000000004")
        self.assertEqual(self.service.get_article_by_slug(a.slug).id, a.id)

    def test_missing_article_raises(self):
        with self.assertRaises(ArticleNotFound):
            self.service.get_article("does-not-exist")

    def test_category_counts(self):
        counts = self.service.category_counts()
        self.assertEqual(sum(counts.values()), 10)
        self.assertEqual(counts["business"], 2)

    def test_missing_data_file_reports_not_ready(self):
        self.assertFalse(JsonArticleRepository(ROOT / "nope.json").is_ready())


class DomainRuleTests(unittest.TestCase):
    def _make(self, **overrides):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        fields = dict(
            id="x", slug="x", title="Title", summary="s", content="c",
            category=Category.CITY, author=Author("a", "A"), source="src",
            published_at=now, updated_at=now,
        )
        fields.update(overrides)
        return Article(**fields)

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            self._make(title="  ")

    def test_updated_before_published_rejected(self):
        with self.assertRaises(ValueError):
            self._make(updated_at=datetime(2020, 1, 1, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
