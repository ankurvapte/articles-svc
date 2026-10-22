# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
Shared architecture rules and the container checklist live in `../CLAUDE.md` (from the [news-app-platform](https://github.com/ankurvapte/news-app-platform) repo).

articles-svc: the news articles read API, the first microservice of the news app.
`README.md` is the public contract (data model, endpoints, env vars). Keep it in sync when those change.

## Commands
- Unit tests (no deps): `python3 -m unittest discover -s tests -p "test_use_cases.py"`
- All tests: `pip install -r requirements-dev.txt && pytest` (Postgres tests skip unless `TEST_DATABASE_URL` is set; see README)
- Single test: `pytest tests/test_api.py::test_health` or `python3 -m unittest tests.test_use_cases.ArticleServiceTests.test_most_viewed_sort`
- Run locally: `uvicorn app.main:app --reload --port 8080` → http://localhost:8080/docs (no `DATABASE_URL`, so it reads `DATA_FILE`)
- Run in Docker: `docker compose up --build` → host port **8090** (compose maps `8090:8080`) + `articles-db` Postgres; reset data with `docker compose down -v`
- No linter/formatter or pytest config is set up.

## Service-specific notes
- **Wiring:** `build_repository` in `main.py` uses `PostgresArticleRepository` when `DATABASE_URL` is set, else `JsonArticleRepository`. `lifespan` passes it to `ArticleService` (stored as `app.state.article_service`) and calls `close()` on shutdown.
- **Errors:** `ArticleNotFound` → 404 `not_found`; `StorageUnavailable` (declared in `application/ports.py`) → 503 `storage_unavailable`.
- **Visibility:** only `status == published` articles are served. `ArticleService` filters on `Article.is_public` for lists, lookups and category counts. Keep that rule in the service when adding queries.
- **Read-only API:** no write endpoints yet. Postgres is filled from `SEED_FILE` only when the table is empty; the JSON adapter loads `DATA_FILE` once at startup.
- **Postgres adapter:** same shape as users-svc: psycopg 3 sync `ConnectionPool` opened with `wait=False`, `schema.sql` applied on first successful connect, seed parsed via `JsonArticleRepository`. `author` is stored as `author_id` + `author_name` columns, `tags` as `TEXT[]`. Timestamps are `TIMESTAMPTZ`, so they come back in UTC. Any `psycopg.Error`/`PoolTimeout` → `StorageUnavailable`. Filtering, sorting and paging still happen in `ArticleService` over `list_all()`.
- **Persistence:** compose runs `articles-db` (postgres:17-alpine) on the `articles-db-data` volume, with no host port. articles-svc waits for its `pg_isready` healthcheck.
- **Authors:** `Article.author` is `{id, name}`; `author.id` will reference a `users-svc` user (via HTTP, never its data).
- **Tests:** `test_postgres_repository.py` drops and recreates the `articles` table on `TEST_DATABASE_URL`; never point it at real data. `test_use_cases.py` uses the real `data/news.json` (10 articles; counts in assertions depend on it).
