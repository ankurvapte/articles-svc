# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

First microservice of a news app, built to learn containerization and
microservice architecture. Python 3.12, FastAPI, runs in Docker.
`README.md` is the public contract (data model, endpoints, env vars) — keep it in sync when those change.

## Commands
- Unit tests (no deps): `python3 -m unittest discover -s tests -p "test_use_cases.py"`
- All tests: `pip install -r requirements-dev.txt && pytest`
- Single test: `pytest tests/test_api.py::test_health` or `python3 -m unittest tests.test_use_cases.ArticleServiceTests.test_most_viewed_sort`
- Run locally: `uvicorn app.main:app --reload --port 8080` → http://localhost:8080/docs
- Run in Docker: `docker compose up --build`
- No linter/formatter or pytest config is set up.

## Architecture rules (always follow)
Clean architecture; dependencies point inward only:
`api → application → domain`, and `infrastructure` implements `application/ports.py`.
- `app/domain/` — entities and business rules. Pure Python. Never import FastAPI, pydantic, json, os or any infrastructure here.
- `app/application/` — use cases (`ArticleService`) and ports (interfaces). No HTTP concepts (status codes, Request).
- `app/infrastructure/` — adapters (currently JSON file; next: Postgres). Only place that knows where data lives.
- `app/api/` — thin HTTP layer: parse input, call a use case, map to `schemas.py`. No business logic.
- `app/main.py` — composition root; the only place layers are wired together.

## How it fits together
- **Wiring:** `main.py` calls `load_settings()` at import time, then `lifespan` builds `JsonArticleRepository` → `ArticleService` and stores them (plus `settings`) on `app.state`. Routes get the service via `Depends(get_service)`; `/health/ready` reads `app.state.repository.is_ready()`. A new adapter (e.g. Postgres) only needs to satisfy the `ArticleRepository` Protocol and be swapped in `lifespan`.
- **Errors:** use cases raise plain exceptions (`ArticleNotFound`); `main.py` exception handlers map them to HTTP status + the `{error, message, request_id}` body. A new domain/application error needs a handler there — never raise `HTTPException` from lower layers.
- **Visibility:** only `status == published` articles are served — `ArticleService` filters on `Article.is_public` for lists, lookups and category counts. Keep that rule in the service when adding queries.
- **Pagination:** `page_size` is defaulted and clamped to `MAX_PAGE_SIZE` in `api/routes.py` (from settings); `ArticleService.list_articles` just validates it's positive.
- **Load failures:** the JSON repository logs and reports not-ready instead of raising, so the container stays up with `/health/ready` → 503 rather than crash-looping. New adapters should follow the same pattern.
- **Request middleware** (`main.py`) reuses or generates `X-Request-ID`, echoes it on the response and logs one JSON line per non-health request. Log extra fields with `logger.info("msg", extra={...})` — `logging_setup.py` turns `extra` keys into top-level JSON keys.
- **Tests:** `test_use_cases.py` uses the real `data/news.json` (10 articles — counts in assertions depend on it). `test_api.py` sets `DATA_FILE` before importing `app.main` (settings load on import) and uses `with TestClient(app)` so `lifespan` runs.
- **Docker:** compose maps host `8080`; if that port is taken the container gets created without its port binding — free the port, then `docker compose up -d --force-recreate`. Compose `environment:` overrides Dockerfile `ENV`, which overrides `config.py` defaults.

## Container-first checklist for every change
1. One business capability per service — articles only. Users, comments, search become separate services.
2. Stateless — no in-memory or local-disk state that must survive a restart.
3. Config from environment variables only (`app/config.py`); never hardcode, never bake secrets into the image.
4. Own your data — never read another service's database.
5. API is versioned (`/api/v1`) and errors use the `{error, message, request_id}` format.
6. Image stays small and non-root (multi-stage `Dockerfile`, keep `.dockerignore` current).
7. Observability — JSON logs to stdout, propagate `X-Request-ID`, keep `/health/live` and `/health/ready` accurate.
8. Design for failure — timeouts/retries on outbound calls, graceful shutdown in `lifespan`.
9. Add/adjust unit tests for domain and use cases with every change.

## Roadmap (from the Containerization project)
- [x] Best-practice pillars defined
- [x] Mock data (10 articles) + read API
- [ ] Skills for the best practices
- [ ] Postgres repository + docker-compose DB (database per service)
- [ ] API gateway (NGINX/Traefik), CI/CD pipeline
- [ ] Deploy to a web server
