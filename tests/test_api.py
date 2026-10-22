"""HTTP-level tests. Requires requirements-dev.txt (FastAPI, httpx, pytest).

    pip install -r requirements-dev.txt
    pytest
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATA_FILE", str(ROOT / "data" / "news.json"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # "with" runs the lifespan startup
        yield c


def test_health(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_list_articles(client):
    body = client.get("/api/v1/articles?page_size=3").json()
    assert body["pagination"] == {"page": 1, "page_size": 3, "total_items": 10, "total_pages": 4}
    assert "content" not in body["data"][0]  # list view stays lightweight


def test_filters(client):
    body = client.get("/api/v1/articles", params={"category": "business"}).json()
    assert body["pagination"]["total_items"] == 2


def test_get_article(client):
    r = client.get("/api/v1/articles/a1f3c2e0-0002-4c1a-9b10-000000000002")
    assert r.status_code == 200
    assert "content" in r.json()
    assert "X-Request-ID" in r.headers


def test_not_found_has_consistent_error(client):
    r = client.get("/api/v1/articles/nope", headers={"X-Request-ID": "abc-123"})
    assert r.status_code == 404
    assert r.json() == {"error": "not_found", "message": "Article 'nope' not found", "request_id": "abc-123"}


def test_invalid_category_is_422(client):
    r = client.get("/api/v1/articles?category=gossip")
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"
