"""HTTP routes for /api/v1. Thin: parse input, call a use case, shape output."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api.schemas import (
    ArticleDetailOut, ArticleListOut, ArticleSummaryOut, CategoryOut, ErrorOut, PaginationOut,
)
from app.application.use_cases import ArticleFilter, ArticleService, SortOrder
from app.domain.models import Category

router = APIRouter(prefix="/api/v1", tags=["articles"])


def get_service(request: Request) -> ArticleService:
    return request.app.state.article_service


@router.get("/articles", response_model=ArticleListOut, summary="List news articles")
def list_articles(
    request: Request,
    category: Category | None = Query(None, description="Filter by category"),
    tag: str | None = Query(None, description="Filter by tag"),
    author_id: str | None = Query(None, description="Filter by author id"),
    featured: bool | None = Query(None, description="Only featured (true) or non-featured (false)"),
    q: str | None = Query(None, min_length=2, description="Search in title, summary and tags"),
    sort: SortOrder = Query(SortOrder.NEWEST),
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1),
    service: ArticleService = Depends(get_service),
) -> ArticleListOut:
    settings = request.app.state.settings
    size = min(page_size or settings.default_page_size, settings.max_page_size)
    result = service.list_articles(
        ArticleFilter(category=category, tag=tag, author_id=author_id, featured=featured, query=q),
        sort=sort, page=page, page_size=size,
    )
    return ArticleListOut(
        data=[ArticleSummaryOut.from_domain(a) for a in result.items],
        pagination=PaginationOut(
            page=result.page, page_size=result.page_size,
            total_items=result.total, total_pages=result.total_pages,
        ),
    )


@router.get(
    "/articles/{article_id}", response_model=ArticleDetailOut,
    responses={404: {"model": ErrorOut}}, summary="Get one article by id",
)
def get_article(article_id: str, service: ArticleService = Depends(get_service)) -> ArticleDetailOut:
    return ArticleDetailOut.from_domain(service.get_article(article_id))


@router.get(
    "/articles/slug/{slug}", response_model=ArticleDetailOut,
    responses={404: {"model": ErrorOut}}, summary="Get one article by URL slug",
)
def get_article_by_slug(slug: str, service: ArticleService = Depends(get_service)) -> ArticleDetailOut:
    return ArticleDetailOut.from_domain(service.get_article_by_slug(slug))


@router.get("/categories", response_model=list[CategoryOut], summary="List categories with counts")
def list_categories(service: ArticleService = Depends(get_service)) -> list[CategoryOut]:
    return [CategoryOut(name=k, article_count=v) for k, v in service.category_counts().items()]
