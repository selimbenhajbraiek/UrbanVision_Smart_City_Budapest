"""Additional smart-city layers (Phase 8), all sourced from OpenStreetMap via Overpass.

Each layer is a static snapshot: it is imported with `python -m ingestion osm` and is
NOT live data (e.g. we know where EV chargers are, not whether they are free right now).
"""

from dataclasses import dataclass

# Budapest's administrative boundary is OSM relation 37244; Overpass area ids add 3600000000.
BUDAPEST_OVERPASS_AREA_ID = 3600037244


@dataclass(frozen=True)
class UrbanLayer:
    id: str
    title: str
    description: str
    overpass_filter: str  # Overpass QL statement; `.city` is the Budapest area
    popup_tags: tuple[str, ...]  # OSM tags worth showing to users


URBAN_LAYERS: dict[str, UrbanLayer] = {
    layer.id: layer
    for layer in (
        UrbanLayer(
            id="ev_charging",
            title="EV charging stations",
            description="Public electric-vehicle charging points mapped in OpenStreetMap.",
            overpass_filter='nwr["amenity"="charging_station"](area.city);',
            popup_tags=(
                "operator",
                "network",
                "capacity",
                "socket:type2",
                "socket:type2_combo",
                "socket:chademo",
                "fee",
                "opening_hours",
                "access",
            ),
        ),
        UrbanLayer(
            id="bike_rental",
            title="Bike sharing & rental",
            description="Bike-sharing docks (e.g. MOL Bubi) and bike rental points.",
            overpass_filter='nwr["amenity"="bicycle_rental"](area.city);',
            popup_tags=("network", "operator", "capacity", "bicycle_rental", "opening_hours"),
        ),
        UrbanLayer(
            id="park_and_ride",
            title="Park & Ride",
            description="Car parks tagged as Park & Ride next to public transport.",
            overpass_filter='nwr["amenity"="parking"]["park_ride"]["park_ride"!="no"](area.city);',
            popup_tags=("operator", "capacity", "fee", "parking", "access", "opening_hours"),
        ),
    )
}
