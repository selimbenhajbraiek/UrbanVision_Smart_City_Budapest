"""Import static OpenStreetMap snapshots (EV charging, bike sharing, P+R) via Overpass API."""

import json
import logging
import time
from dataclasses import dataclass

import httpx
import psycopg

from app.urban_layers import BUDAPEST_OVERPASS_AREA_ID, URBAN_LAYERS, UrbanLayer
from ingestion.schema import apply_schema

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 502, 503, 504}
RETRY_BASE_SECONDS = 15


class OverpassError(Exception):
    pass


@dataclass
class Poi:
    osm_type: str
    osm_id: int
    lat: float
    lon: float
    tags: dict[str, str]

    @property
    def name(self) -> str | None:
        return self.tags.get("name")

    @property
    def operator(self) -> str | None:
        return self.tags.get("operator") or self.tags.get("network")


def build_query(layer: UrbanLayer) -> str:
    # `out center` gives ways/relations (e.g. car-park polygons) a single representative point.
    return (
        f"[out:json][timeout:120];"
        f"area(id:{BUDAPEST_OVERPASS_AREA_ID})->.city;"
        f"({layer.overpass_filter});"
        f"out center tags;"
    )


def parse_overpass(payload: dict) -> tuple[list[Poi], str | None]:
    """Convert an Overpass JSON response into POIs, skipping elements without a location."""
    if not isinstance(payload.get("elements"), list):
        raise OverpassError("Unexpected Overpass response: no 'elements' list")
    pois: list[Poi] = []
    for element in payload["elements"]:
        point = element if "lat" in element else element.get("center")
        if not point or "lat" not in point or "lon" not in point:
            continue
        pois.append(
            Poi(
                osm_type=element["type"],
                osm_id=int(element["id"]),
                lat=float(point["lat"]),
                lon=float(point["lon"]),
                tags={str(k): str(v) for k, v in element.get("tags", {}).items()},
            )
        )
    timestamp = payload.get("osm3s", {}).get("timestamp_osm_base")
    return pois, timestamp


def fetch_layer(
    layer: UrbanLayer, overpass_url: str, user_agent: str, attempts: int = 4
) -> tuple[list[Poi], str | None]:
    """Query Overpass, retrying when the public server is busy (429/5xx are common)."""
    for attempt in range(1, attempts + 1):
        logger.info("Querying Overpass for %s (attempt %d/%d)", layer.id, attempt, attempts)
        try:
            response = httpx.post(
                overpass_url,
                data={"data": build_query(layer)},
                headers={"User-Agent": user_agent},
                timeout=180,
            )
            if response.status_code in RETRYABLE_STATUS and attempt < attempts:
                wait = RETRY_BASE_SECONDS * attempt
                logger.warning(
                    "Overpass busy (HTTP %d); retrying in %ds", response.status_code, wait
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            return parse_overpass(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            if attempt < attempts and isinstance(exc, httpx.TransportError):
                time.sleep(RETRY_BASE_SECONDS * attempt)
                continue
            raise OverpassError(f"Overpass request for {layer.id} failed: {exc}") from exc
    raise OverpassError(f"Overpass request for {layer.id} failed after {attempts} attempts")


def store_layer(
    conn: psycopg.Connection, layer_id: str, pois: list[Poi], timestamp: str | None
) -> None:
    """Replace one layer's features atomically."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM urban_pois WHERE category = %s", (layer_id,))
        cur.executemany(
            """
            INSERT INTO urban_pois (category, osm_type, osm_id, name, operator, tags, geom)
            VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    layer_id,
                    p.osm_type,
                    p.osm_id,
                    p.name,
                    p.operator,
                    json.dumps(p.tags),
                    p.lon,
                    p.lat,
                )
                for p in pois
            ],
        )
        cur.execute(
            """
            INSERT INTO urban_layer_imports (category, feature_count, osm_data_timestamp)
            VALUES (%s, %s, %s)
            ON CONFLICT (category) DO UPDATE
            SET feature_count = EXCLUDED.feature_count,
                osm_data_timestamp = EXCLUDED.osm_data_timestamp,
                imported_at = now()
            """,
            (layer_id, len(pois), timestamp),
        )


def import_urban_layers(
    database_url: str, layer_ids: list[str], overpass_url: str, user_agent: str
) -> dict[str, int]:
    counts: dict[str, int] = {}
    with psycopg.connect(database_url, autocommit=True) as conn:
        apply_schema(conn)
        for layer_id in layer_ids:
            pois, timestamp = fetch_layer(URBAN_LAYERS[layer_id], overpass_url, user_agent)
            store_layer(conn, layer_id, pois, timestamp)
            counts[layer_id] = len(pois)
            logger.info("Stored %d %s features (OSM data as of %s)", len(pois), layer_id, timestamp)
    return counts
