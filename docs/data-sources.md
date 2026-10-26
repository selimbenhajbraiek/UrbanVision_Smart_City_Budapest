# Data sources

For every dataset, this document records its source, licence, update frequency, access method, format and limitations. The same information, shortened, is served by `GET /api/meta` and shown in the app's **Data sources** dialog.

Data types used throughout the app:
- **Scheduled**: official timetable
- **Model**: numerical model output
- **Static**: snapshot taken at import time
- **Live**: real-time feed

---

## Integrated datasets

### 1. OpenStreetMap: base map

| | |
| --- | --- |
| Source | <https://www.openstreetmap.org>, tiles from `tile.openstreetmap.org` |
| Licence | Data: ODbL 1.0. Attribution "© OpenStreetMap contributors" required. |
| Update frequency | Continuous (tiles re-rendered as the map changes) |
| Access | HTTPS raster tiles `/{z}/{x}/{y}.png`, no key |
| Format | 256 px PNG |
| Type | Static |
| Limitations | The [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) allows light use with attribution. It is fine for a demo, but a production deployment would need its own tile server or a commercial provider. The "muted" style is the same tiles desaturated with CSS in the browser. |

We also evaluated CARTO basemaps. They now return "API key required" tiles, so they are not used.

### 2. BKK GTFS: public-transport timetable

| | |
| --- | --- |
| Source | BKK (Budapesti Közlekedési Központ), <https://bkk.hu/bkk-partnerek/egyeb/gtfs-menetrendi-adatok-programozoknak/> |
| Download | <https://bkk.hu/gtfs/budapest_gtfs.zip>, which redirects to `go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip` (about 60 MB) |
| Licence | BKK publishes the data openly for developers. The page does **not** state an explicit licence. We credit "BKK" and use it for non-commercial education. |
| Update frequency | According to BKK, typically monthly and sometimes weekly. The feed inspected on 2026-09-27 covered 2026-09-27 to 2026-11-01. |
| Format | GTFS static (CSV files in a ZIP) |
| Type | **Scheduled.** It contains no vehicle positions and no delays. |
| Files used | `agency`, `routes`, `stops`, `trips`, `stop_times`, `calendar_dates`, `shapes`, `feed_info` (`calendar.txt` is supported but not provided by BKK) |
| Files ignored | `pathways.txt` (in-station walkways) and `translations.txt` (a few English names); not needed for the map |
| Limitations | Short validity window, so it needs regular re-import. Short-notice diversions are not included; BKK itself notes that only planned changes are published. There are 178 stops with no service in the current feed; they are hidden. |

### 3. Open-Meteo: weather

| | |
| --- | --- |
| Source | <https://open-meteo.com/>, Forecast API `api.open-meteo.com/v1/forecast` |
| Licence | CC BY 4.0. Free for non-commercial use without an API key (fair-use limit of about 10,000 calls/day). |
| Update frequency | "Current" values are 15-minute model steps; the forecast is hourly |
| Format | JSON |
| Type | **Model**: output of weather models (e.g. ICON, ECMWF), not a station measurement |
| Our usage | One request per 10 minutes per location (server-side cache), central Budapest by default |
| Limitations | One point for the whole city. Precipitation is a model estimate. |

### 4. Open-Meteo Air Quality: CAMS

| | |
| --- | --- |
| Source | <https://open-meteo.com/en/docs/air-quality-api>, based on the Copernicus Atmosphere Monitoring Service (CAMS) European forecast |
| Licence | CC BY 4.0 (Open-Meteo), with Copernicus data attribution |
| Update frequency | Hourly values |
| Format | JSON |
| Type | **Model** |
| Values used | European AQI, PM2.5, PM10, NO₂, O₃ |
| Limitations | Modelled at about 10 km resolution, so it is not a street-level sensor reading. The UI states "not a sensor reading". |

### 5. OpenStreetMap via Overpass: urban layers

| Layer | OSM filter | Features (27 Sept 2026) |
| --- | --- | ---: |
| EV charging stations | `amenity=charging_station` | 517 |
| Bike sharing & rental | `amenity=bicycle_rental` (includes MOL Bubi docks) | 228 |
| Park & Ride | `amenity=parking` + `park_ride≠no` | 53 |

| | |
| --- | --- |
| Source | Overpass API `overpass-api.de`, area = Budapest administrative boundary (OSM relation 37244) |
| Licence | ODbL 1.0 ("© OpenStreetMap contributors") |
| Update frequency | Snapshot whenever `python -m ingestion osm` is run |
| Format | Overpass JSON. Ways and relations are reduced to their centre point. |
| Type | **Static** |
| Limitations | Completeness depends on OSM volunteers. There is no availability information, e.g. whether a charger is free. The public Overpass server rate-limits; the importer retries with back-off. |

### 6. BKK FUTÁR GTFS-Realtime (optional, Phase 10)

| | |
| --- | --- |
| Source | BKK OpenData, <https://opendata.bkk.hu/> |
| Endpoints | `https://go.bkk.hu/api/query/v1/ws/gtfs-rt/full/VehiclePositions.pb`, `Alerts.pb` (also `TripUpdates.pb`) |
| Licence | BKK OpenData terms of use. Requires a free API key (the endpoint returns HTTP 401 without one, verified 2026-09-27). |
| Update frequency | Seconds |
| Format | GTFS-Realtime (Protocol Buffers) |
| Type | **Live** |
| Status | Client implemented and tested with synthetic feeds. It is disabled until `BKK_API_KEY` is set. |

---

## Investigated but not integrated

We did not add these datasets merely to add features. Each one was dropped for a stated reason.

| Topic | Finding | Decision |
| --- | --- | --- |
| **Live traffic** | We found no free, open, documented traffic-flow API for Budapest. Commercial providers (TomTom, HERE, Google) require API keys and commercial terms. | Not added. This avoids paid or keyed APIs and fake data. |
| **Live parking occupancy** | We found no open real-time occupancy feed. | We show P+R *locations* (static) instead of occupancy. |
| **Sensor-based air quality** | The Hungarian national network (OLM) publishes measurements on its website. We did not find a documented open API. | We use CAMS model data and label it clearly as model data. Official measurements are a candidate for future work. |
| **Live bike-sharing availability** | MOL Bubi availability may be published through BKK's API (requires a key). This is unverified. | Future work, alongside the real-time provider. Dock locations come from OSM. |
| **Cycling infrastructure (bike lanes)** | Available in OSM (`highway=cycleway`, `cycleway=*`), but it is line data and would add a lot of geometry. | Future work. It would need simplification and a separate zoom-dependent layer. |
