# articles-svc

The first microservice of the news app. It serves news articles over a
versioned REST API and is built to run in a container from day one.

## Layout (clean architecture)

```
app/
├── domain/models.py            # Entities + business rules. Depends on nothing.
├── application/
│   ├── ports.py                # ArticleRepository interface
│   └── use_cases.py            # ArticleService: list, filter, paginate, get
├── infrastructure/
│   └── json_repository.py      # Reads data/news.json (swap for Postgres later)
├── api/
│   ├── schemas.py              # Public API contract (response models)
│   ├── routes.py               # /api/v1/* endpoints
│   └── health.py               # /health/live, /health/ready
├── config.py                   # Settings from environment variables
├── logging_setup.py            # JSON logs to stdout
└── main.py                     # Composition root: wires layers together
data/news.json                  # 10 mock articles
tests/                          # Unit tests (no deps) + API tests (FastAPI)
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
| published_at, updated_at | ISO-8601 datetime | `updated_at ≥ published_at` |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/articles` | List with `category`, `tag`, `author_id`, `featured`, `q`, `sort` (`newest`/`oldest`/`most_viewed`), `page`, `page_size` |
| GET | `/api/v1/articles/{id}` | Full article by id |
| GET | `/api/v1/articles/slug/{slug}` | Full article by slug |
| GET | `/api/v1/categories` | Categories with article counts |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe (503 if data failed to load) |
| GET | `/docs` | Interactive Swagger UI (auto-generated) |

Errors always look like:
```json
{ "error": "not_found", "message": "Article 'x' not found", "request_id": "..." }
```

## Run it

**With Docker (recommended):**
```bash
docker compose up --build
# open http://localhost:8080/docs
curl "http://localhost:8080/api/v1/articles?category=technology"
```

**Without Docker:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8080
```

## Test it

```bash
python -m unittest discover -s tests -p "test_use_cases.py"   # no dependencies
pytest                                                        # all tests, needs requirements-dev.txt
```

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DATA_FILE` | `data/news.json` | Path to the article data |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `DEFAULT_PAGE_SIZE` | `10` | Page size when none is given |
| `MAX_PAGE_SIZE` | `50` | Upper bound on `page_size` |
| `PORT` | `8080` | Container listen port |
| `SERVICE_NAME` | `articles-svc` | Name stamped on every log line |

## Which pillars this covers

1 one capability (articles) · 2 clean layers · 3 stateless · 4 env config ·
6 versioned contract + consistent errors · 7 multi-stage, non-root image ·
8 health probes, JSON logs, request IDs · 9 graceful startup/shutdown.
Still to come: 5 (own database), 10 (CI/CD + gateway).
