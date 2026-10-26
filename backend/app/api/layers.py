from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from psycopg import Connection

from app.api.deps import parse_bbox
from app.db import get_connection
from app.repositories import urban_layers as repo
from app.schemas.meta import UrbanLayerInfo
from app.urban_layers import URBAN_LAYERS

router = APIRouter(prefix="/layers", tags=["urban layers"])

ConnDep = Annotated[Connection, Depends(get_connection)]


@router.get("", response_model=list[UrbanLayerInfo])
def list_layers(conn: ConnDep) -> list[UrbanLayerInfo]:
    """Additional smart-city layers and whether they have been imported."""
    imports = repo.layer_imports(conn)
    result = []
    for layer in URBAN_LAYERS.values():
        imported = imports.get(layer.id)
        result.append(
            UrbanLayerInfo(
                id=layer.id,
                title=layer.title,
                description=layer.description,
                feature_count=imported["feature_count"] if imported else 0,
                imported_at=imported["imported_at"] if imported else None,
                osm_data_timestamp=imported["osm_data_timestamp"] if imported else None,
            )
        )
    return result


@router.get(
    "/{layer_id}",
    response_class=Response,
    responses={200: {"content": {"application/geo+json": {}}}},
)
def layer_features(
    layer_id: str,
    conn: ConnDep,
    bbox: Annotated[str | None, Query(description="minLon,minLat,maxLon,maxLat")] = None,
) -> Response:
    """Features of one layer as GeoJSON (static OpenStreetMap snapshot)."""
    layer = URBAN_LAYERS.get(layer_id)
    if layer is None:
        raise HTTPException(
            404, f"Unknown layer '{layer_id}'. Available: {', '.join(URBAN_LAYERS)}"
        )
    geojson = repo.layer_geojson(conn, layer_id, layer.popup_tags, parse_bbox(bbox))
    return Response(geojson, media_type="application/geo+json")
