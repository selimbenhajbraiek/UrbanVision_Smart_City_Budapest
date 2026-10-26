"""Single source of truth for external data sources, licences and attribution.

Served at GET /api/meta and rendered in the frontend's "Data sources" dialog.
"""

from app.schemas.meta import DataSource

DATA_SOURCES: list[DataSource] = [
    DataSource(
        id="osm",
        name="OpenStreetMap",
        url="https://www.openstreetmap.org/copyright",
        provides="Base map tiles; EV charging, bike sharing and Park & Ride locations",
        license="Open Database License (ODbL) 1.0",
        attribution="© OpenStreetMap contributors",
        data_status="static",
        update_frequency="Tiles: continuously; POI layers: snapshot at import time",
    ),
    DataSource(
        id="bkk_gtfs",
        name="BKK GTFS timetable",
        url="https://bkk.hu/bkk-partnerek/egyeb/gtfs-menetrendi-adatok-programozoknak/",
        provides="Stops, routes, trips, scheduled departures, route shapes",
        license="Published openly by BKK for developers; no explicit licence stated",
        attribution="Timetable data: BKK Budapesti Közlekedési Központ",
        data_status="scheduled",
        update_frequency="Typically monthly, sometimes weekly; covers ~5 weeks ahead",
    ),
    DataSource(
        id="open_meteo",
        name="Open-Meteo",
        url="https://open-meteo.com/",
        provides="Current weather, hourly forecast, air quality (CAMS)",
        license="CC BY 4.0 (free for non-commercial use, no API key)",
        attribution="Weather data by Open-Meteo.com",
        data_status="model",
        update_frequency="Weather every 15 min; air quality hourly (cached 10 min)",
    ),
    DataSource(
        id="bkk_realtime",
        name="BKK FUTÁR GTFS-Realtime (optional)",
        url="https://opendata.bkk.hu/",
        provides="Live vehicle positions and service alerts",
        license="BKK OpenData terms of use (free API key required)",
        attribution="Real-time data: BKK FUTÁR",
        data_status="realtime",
        update_frequency="Seconds (only when BKK_API_KEY is configured)",
    ),
]
