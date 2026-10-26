import logging

import psycopg
from fastapi import APIRouter, Request, Response
from psycopg_pool import PoolTimeout

from app.schemas.meta import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request, response: Response) -> HealthResponse:
    """Liveness check. Returns 503 when the database cannot be reached."""
    try:
        with request.app.state.pool.connection(timeout=2) as conn:
            schema_ready = conn.execute(
                "SELECT to_regclass('public.feed_info') IS NOT NULL AS ok"
            ).fetchone()["ok"]
            loaded = (
                schema_ready
                and conn.execute("SELECT EXISTS (SELECT 1 FROM feed_info) AS ok").fetchone()["ok"]
            )
        return HealthResponse(status="ok", database="ok", gtfs_loaded=bool(loaded))
    except (PoolTimeout, psycopg.Error) as exc:
        logger.warning("Health check failed: %s", exc)
        response.status_code = 503
        return HealthResponse(status="degraded", database="unavailable", gtfs_loaded=False)
