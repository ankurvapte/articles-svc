# articles-svc

The first microservice of the news app. It serves news articles over a
versioned REST API and is built to run in a container from day one.

## Layout (clean architecture)

```
app/
├── domain/models.py            # Entities + business rules. Depends on nothing.
├── application/
│   ├── ports.py                # ArticleRepository interface, StorageUnavailable
│   └── use_cases.py            # ArticleService: list, filter, paginate, get
├── infrastructure/
│   ├── postgres_repository.py  # PostgreSQL adapter (used when DATABASE_URL is set)
│   └── json_repository.py      # JSON file adapter (used when DATABASE_URL is not set)
├── api/
│   ├── schemas.py              # Public API contract (response models)
│   ├── routes.py               # /api/v1/* endpoints
│   └── health.py               # /health/live, /health/ready
├── config.py                   # Settings from environment variables
├── logging_setup.py            # JSON logs to stdout
└── main.py                     # Composition root: wires layers together
migrations/versions/            # Alembic migrations: the articles table schema, in order
alembic.ini                     # Alembic config (the URL comes from DATABASE_URL)
data/news.json                  # 10 mock articles; SEED_FILE for Postgres
tests/                          # Unit tests (no deps) + API tests (FastAPI) + Postgres/migration tests
```

Dependencies point inward: `api → application → domain`, and
`infrastructure` implements the `application` port.

## Data model

| Field | Type | Notes |
|---|---|---|
| id | string (UUID) | Primary identifier |
| slug | string | URL-friendly unique name |
| title, summary, content | string | `content` only in detail view |
| category | enum | city, technology, business, sports, weather, health, science, entertainment |
| tags | string[] | Lower-cased |
| author | {id, name} | Reference to the future `users-svc` |
| source | string | Publisher |
| image_url | string? | Hero image |
| language | string | ISO code, default `en` |
| status | enum | draft, published, archived (only published is served) |
| is_featured | bool | For homepage highlights |
| read_time_minutes | int | ≥ 1 |
| view_count | int | Used for "most viewed" sort |
| published_at, updated_at | ISO-8601 datetime | `updated_at ≥ published_at`. From Postgres they come back in UTC (same instant as the seed's `+05:30`) |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/articles` | List with `category`, `tag`, `author_id`, `featured`, `q`, `sort` (`newest`/`oldest`/`most_viewed`), `page`, `page_size` |
| GET | `/api/v1/articles/{id}` | Full article by id |
| GET | `/api/v1/articles/slug/{slug}` | Full article by slug |
| GET | `/api/v1/categories` | Categories with article counts |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe (503 if the database is unreachable or data failed to load) |
| GET | `/docs` | Interactive Swagger UI (auto-generated) |

Errors always look like:
```json
{ "error": "not_found", "message": "Article 'x' not found", "request_id": "..." }
```

| Status | `error` | When |
|---|---|---|
| 404 | `not_found` | Unknown or unpublished article |
| 422 | `validation_error` | Bad query parameter |
| 503 | `storage_unavailable` | The database is unreachable |

## Run it

**With Docker (recommended):**
```bash
docker compose up --build
# open http://localhost:8090/docs
curl "http://localhost:8090/api/v1/articles?category=technology"
```

Compose starts, in order:
1. `articles-db`: its own Postgres (database per service).
2. `articles-migrate`: a one-shot job from the same image that runs
   `alembic upgrade head` and exits. It shows as `Exited (0)` in
   `docker compose ps -a`; that's expected.
3. `articles-svc`: starts only if the migrations succeeded. On first connect,
   because `SEED_FILE` is set, it loads the 10 seed articles into the empty table.

Data lives on the named volume `articles-db-data`. To reset to the seed data,
run `docker compose down -v`.

The database publishes no host port. To look inside:
```bash
docker compose exec articles-db psql -U articles -c "SELECT slug, status FROM articles"
```

If the database goes down, articles-svc stays up: `/health/ready` returns 503
and requests return `503 storage_unavailable` until it is back.

**Without Docker:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8080
```
Without `DATABASE_URL` this uses the JSON file adapter on `data/news.json`.

## Test it

```bash
python -m unittest discover -s tests -p "test_use_cases.py"   # no dependencies
pytest                                                        # all tests, needs requirements-dev.txt
```

The Postgres adapter and migration tests need a throwaway database (they drop
the tables and run the migrations from scratch) and are skipped without one:
```bash
docker run --rm -d --name articles-test-db -e POSTGRES_PASSWORD=test -p 55433:5432 postgres:17-alpine
TEST_DATABASE_URL=postgresql://postgres:test@localhost:55433/postgres pytest tests/test_postgres_repository.py
docker stop articles-test-db
```

## CI and images

`.github/workflows/ci.yml` runs on every push:
1. `test`: `pytest` with a Postgres service container (`TEST_DATABASE_URL` set), so the
   Postgres and migration tests run too.
2. `image`: builds the image, smoke-tests it (`/health/ready` must return 200 with the
   bundled JSON data), then pushes it to GHCR. Runs only if `test` passed.

Images are `linux/arm64` only (built natively on ARM runners; the server is AWS Graviton). Images are public: `docker pull ghcr.io/ankurvapte/articles-svc:<full commit SHA>`.
Every pushed commit gets its own SHA tag, which never changes; pushes to `main` also
move `:main`. Deploy by pinning a SHA tag, never `:main`.
3. `deploy-bump` (main only, after `image`): pins the new SHA in
   [news-app-platform](https://github.com/ankurvapte/news-app-platform)'s
   `docker-compose.yml`; its updater then deploys it (pull-based CD). Needs the
   repo secret `PLATFORM_REPO_TOKEN`; without it the job only warns.

## Change the schema

The schema lives only in `migrations/versions/`, applied in order and recorded
in the `alembic_version` table. Never edit a migration that has been deployed;
add a new one:
```bash
alembic revision -m "add source_url to articles" --rev-id 0002   # no database needed
# write the SQL in upgrade() and downgrade() with op.execute(...)
docker compose up --build                                         # articles-migrate applies it
```
Expand, then contract: every migration must keep both the old and the new
app version working (add a nullable column first, make it required in a later
migration), so deploys and rollbacks stay safe. Adding a column also means
updating `postgres_repository.py` and this README's data model.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | *(unset)* | Postgres connection URL. Set → Postgres adapter; unset → JSON file adapter. Also used by `alembic upgrade head` |
| `SEED_FILE` | *(unset)* | JSON file loaded into an empty `articles` table on first connect (Postgres only) |
| `DATA_FILE` | `data/news.json` | JSON adapter's data file when `DATABASE_URL` is unset |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `DEFAULT_PAGE_SIZE` | `10` | Page size when none is given |
| `MAX_PAGE_SIZE` | `50` | Upper bound on `page_size` |
| `PORT` | `8080` | Container listen port |
| `SERVICE_NAME` | `articles-svc` | Name stamped on every log line |

## Which pillars this covers

1 one capability (articles) · 2 clean layers · 3 stateless container (state in
Postgres) · 4 env config · 5 own database · 6 versioned contract + consistent
errors · 7 multi-stage, non-root image · 8 health probes, JSON logs, request IDs ·
9 graceful startup/shutdown, timeouts on database calls. Still to come: 10 (CI/CD + gateway).
