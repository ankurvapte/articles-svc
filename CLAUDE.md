# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
Shared architecture rules and the container checklist live in `../CLAUDE.md` (from the [news-app-platform](https://github.com/ankurvapte/news-app-platform) repo).

articles-svc: the news articles read API, the first microservice of the news app.
`README.md` is the public contract (data model, endpoints, env vars). Keep it in sync when those change.

## Commands
- Unit tests (no deps): `python3 -m unittest discover -s tests -p "test_use_cases.py"`
- All tests: `pip install -r requirements-dev.txt && pytest`
- Single test: `pytest tests/test_api.py::test_health` or `python3 -m unittest tests.test_use_cases.ArticleServiceTests.test_most_viewed_sort`
- Run locally: `uvicorn app.main:app --reload --port 8080` → http://localhost:8080/docs
- Run in Docker: `docker compose up --build` → host port **8090** (compose maps `8090:8080`)
- No linter/formatter or pytest config is set up.

## Service-specific notes
- **Wiring:** `lifespan` builds `JsonArticleRepository` → `ArticleService` and stores the service as `app.state.article_service`.
- **Errors:** `ArticleNotFound` → 404 `not_found`.
- **Visibility:** only `status == published` articles are served. `ArticleService` filters on `Article.is_public` for lists, lookups and category counts. Keep that rule in the service when adding queries.
- **Read-only:** data is loaded once from `DATA_FILE` at startup and baked into the image. No writes, no volume.
- **Authors:** `Article.author` is `{id, name}`; `author.id` will reference a `users-svc` user (via HTTP, never its data).
- **Tests:** `test_use_cases.py` uses the real `data/news.json` (10 articles; counts in assertions depend on it).
