from typing import Annotated

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from app.db import get_connection
from app.repositories import routes as routes_repo
from app.repositories import stops as stops_repo
from app.schemas.transit import RouteSummary, SearchResponse, StopSearchResult

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search(
    conn: Annotated[Connection, Depends(get_connection)],
    q: Annotated[str, Query(min_length=2, max_length=100, description="Stop name or line number")],
    limit: Annotated[int, Query(ge=1, le=25)] = 8,
) -> SearchResponse:
    """Accent-insensitive search over stop names and route numbers ("deak", "M2", "47")."""
    query = q.strip()
    return SearchResponse(
        query=query,
        stops=[StopSearchResult(**row) for row in stops_repo.search_stops(conn, query, limit)],
        routes=[RouteSummary(**row) for row in routes_repo.list_routes(conn, None, query)[:limit]],
    )
