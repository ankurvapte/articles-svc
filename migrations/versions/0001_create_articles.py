"""Create the articles table (baseline, same as the old schema.sql).

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS only here, so databases created by the old schema.sql are
    # adopted as-is. Later migrations state exact changes and never use it.
    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS articles_published_at_idx ON articles (published_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE articles")
