-- articles-svc owns this schema; no other service reads or writes it.
-- Applied on first connect and safe to re-run. Move to a migration tool
-- (e.g. Alembic) once the schema starts changing.
CREATE TABLE IF NOT EXISTS articles (
    id                TEXT PRIMARY KEY,
    slug              TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,
    summary           TEXT NOT NULL,
    content           TEXT NOT NULL,
    category          TEXT NOT NULL,
    -- Author is a reference to a users-svc user, copied here (never joined).
    author_id         TEXT NOT NULL,
    author_name       TEXT NOT NULL,
    source            TEXT NOT NULL,
    published_at      TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL,
    status            TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('draft', 'published', 'archived')),
    tags              TEXT[] NOT NULL DEFAULT '{}',
    image_url         TEXT,
    language          TEXT NOT NULL DEFAULT 'en',
    is_featured       BOOLEAN NOT NULL DEFAULT FALSE,
    read_time_minutes INTEGER NOT NULL DEFAULT 1 CHECK (read_time_minutes >= 1),
    view_count        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS articles_published_at_idx ON articles (published_at DESC);
