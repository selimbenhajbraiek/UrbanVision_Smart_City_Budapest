"""Mapping from GTFS `route_type` codes to the transport modes shown in UrbanVision.

BKK uses basic GTFS codes (0 tram, 1 metro, 3 bus, 4 ferry) plus two extended codes:
11 (trolleybus) and 109 (suburban railway = HÉV). Extended "Hierarchical Vehicle Type"
codes (100-1700) are mapped by range so other feeds would work too.
"""

# Ordered by visual priority: when a stop is served by several modes, the first one wins.
MODES: dict[str, str] = {
    "metro": "Metro",
    "hev": "HÉV (suburban railway)",
    "rail": "Railway",
    "tram": "Tram",
    "trolleybus": "Trolleybus",
    "bus": "Bus",
    "boat": "Boat",
    "other": "Other",
}

_BASIC_ROUTE_TYPES = {
    0: "tram",
    1: "metro",
    2: "rail",
    3: "bus",
    4: "boat",
    5: "tram",  # cable tram
    6: "other",  # aerial lift
    7: "other",  # funicular
    11: "trolleybus",
    12: "rail",  # monorail
}


def mode_for_route_type(route_type: int) -> str:
    if route_type in _BASIC_ROUTE_TYPES:
        return _BASIC_ROUTE_TYPES[route_type]
    if route_type == 109:
        return "hev"
    if 100 <= route_type < 200:
        return "rail"
    if 200 <= route_type < 300 or 700 <= route_type < 800:
        return "bus"
    if 400 <= route_type < 500:
        return "metro"
    if route_type == 800:
        return "trolleybus"
    if 900 <= route_type < 1000:
        return "tram"
    if 1000 <= route_type < 1300:
        return "boat"
    return "other"


def parse_modes(raw: str | None) -> list[str] | None:
    """Parse a comma-separated `mode` query parameter. Raises ValueError on unknown modes."""
    if raw is None or not raw.strip():
        return None
    modes = [part.strip().lower() for part in raw.split(",") if part.strip()]
    unknown = sorted(set(modes) - MODES.keys())
    if unknown:
        raise ValueError(f"Unknown mode(s): {', '.join(unknown)}. Valid: {', '.join(MODES)}")
    return modes
