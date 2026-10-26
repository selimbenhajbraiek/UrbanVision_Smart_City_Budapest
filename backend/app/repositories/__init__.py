"""Data access: every SQL query of the API lives in this package.

GeoJSON FeatureCollections are assembled inside PostgreSQL and returned as ready-made
JSON text, which avoids converting thousands of features to Python objects and back.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def as_params(self) -> dict[str, float]:
        return {
            "min_lon": self.min_lon,
            "min_lat": self.min_lat,
            "max_lon": self.max_lon,
            "max_lat": self.max_lat,
        }


BBOX_CONDITION = "geom && ST_MakeEnvelope(%(min_lon)s, %(min_lat)s, %(max_lon)s, %(max_lat)s, 4326)"


def like_pattern(text: str) -> str:
    """Escape LIKE wildcards in user input and wrap it for a 'contains' search."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
