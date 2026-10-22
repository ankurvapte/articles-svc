"""HTTP routes for /api/v1. Thin: parse input, call a use case, shape output."""
from __future__ import annotations  # Treat type hints as strings (lets us write `X | None` freely)

from fastapi import APIRouter, Depends, Query, Request  # FastAPI building blocks for routes

# Response models: the public JSON shape, kept separate from domain entities
from app.api.schemas import (
    ArticleDetailOut, ArticleListOut, ArticleSummaryOut, CategoryOut, ErrorOut, PaginationOut,
)
from app.application.use_cases import ArticleFilter, ArticleService, SortOrder  # Use cases + their inputs
from app.domain.models import Category  # Enum, so FastAPI rejects unknown categories with a 422

# Every route below is served under /api/v1 and grouped as "articles" in /docs
router = APIRouter(prefix="/api/v1", tags=["articles"])


def get_service(request: Request) -> ArticleService:
    # Dependency: hand routes the service that main.py's lifespan built at startup
    return request.app.state.article_service


@router.get("/articles", response_model=ArticleListOut, summary="List news articles")  # GET /api/v1/articles
def list_articles(
    request: Request,  # Raw request, used to reach app settings
    category: Category | None = Query(None, description="Filter by category"),  # ?category=technology
    tag: str | None = Query(None, description="Filter by tag"),  # ?tag=metro
    author_id: str | None = Query(None, description="Filter by author id"),  # ?author_id=auth-01
    featured: bool | None = Query(None, description="Only featured (true) or non-featured (false)"),  # ?featured=true
    q: str | None = Query(None, min_length=2, description="Search in title, summary and tags"),  # ?q=..., 2+ chars
    sort: SortOrder = Query(SortOrder.NEWEST),  # ?sort=newest|oldest|most_viewed, newest by default
    page: int = Query(1, ge=1),  # ?page=N, 1-based, must be >= 1
    page_size: int | None = Query(None, ge=1),  # ?page_size=N, optional, must be >= 1
    service: ArticleService = Depends(get_service),  # Injected use-case service
) -> ArticleListOut:
    settings = request.app.state.settings  # Env-driven config loaded at startup
    size = min(page_size or settings.default_page_size, settings.max_page_size)  # Fall back to default, cap at max
    result = service.list_articles(  # Run the use case; returns a Page of domain Articles
        ArticleFilter(category=category, tag=tag, author_id=author_id, featured=featured, query=q),  # Bundle filters
        sort=sort, page=page, page_size=size,
    )
    return ArticleListOut(  # Shape the domain result into the public response
        data=[ArticleSummaryOut.from_domain(a) for a in result.items],  # Summaries only, no full content
        pagination=PaginationOut(  # Paging metadata so clients can build "next page" links
            page=result.page, page_size=result.page_size,
            total_items=result.total, total_pages=result.total_pages,
        ),
    )


@router.get(  # GET /api/v1/articles/{article_id}
    "/articles/{article_id}", response_model=ArticleDetailOut,
    responses={404: {"model": ErrorOut}}, summary="Get one article by id",  # Document the 404 shape in /docs
)
def get_article(article_id: str, service: ArticleService = Depends(get_service)) -> ArticleDetailOut:
    # Raises ArticleNotFound if missing; main.py turns that into a 404 error body
    return ArticleDetailOut.from_domain(service.get_article(article_id))


@router.get(  # GET /api/v1/articles/slug/{slug}
    "/articles/slug/{slug}", response_model=ArticleDetailOut,
    responses={404: {"model": ErrorOut}}, summary="Get one article by URL slug",
)
def get_article_by_slug(slug: str, service: ArticleService = Depends(get_service)) -> ArticleDetailOut:
    # Same as above, looked up by the URL-friendly slug instead of the id
    return ArticleDetailOut.from_domain(service.get_article_by_slug(slug))


@router.get("/categories", response_model=list[CategoryOut], summary="List categories with counts")  # GET /api/v1/categories
def list_categories(service: ArticleService = Depends(get_service)) -> list[CategoryOut]:
    # Turn the {category: count} dict into a list of response objects
    return [CategoryOut(name=k, article_count=v) for k, v in service.category_counts().items()]
