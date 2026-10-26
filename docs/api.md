# UrbanVision REST API

Base URL in development: `http://localhost:8000/api` (the frontend reaches it through the Vite proxy at `/api`).
Interactive documentation, generated from the code: `http://localhost:8000/docs`.

## Conventions

- All endpoints are read-only `GET` requests.
- **Map layers** return GeoJSON `FeatureCollection`s with the media type `application/geo+json`. Coordinates are `[longitude, latitude]` (WGS84).
- **Everything else** returns JSON described by Pydantic models (see `backend/app/schemas/`).
- Responses larger than 1 KB are gzip-compressed when the client sends `Accept-Encoding: gzip`.
- Times are ISO 8601 with a UTC offset in Budapest local time, e.g. `2026-10-05T08:00:00+02:00`.
- Every response that contains data about the city states its nature in `data_status`:
  - `scheduled`: timetable
  - `model`: weather model
  - `static`: snapshot
  - `realtime`: live

### Errors

| Status | When | Body |
| --- | --- | --- |
| 404 | Unknown stop, route or layer | `{"detail": "Stop 'NOPE' not found"}` |
| 422 | Invalid parameter (bad bbox, unknown mode, time `25:00`, location outside Budapest, …) | `{"detail": "..."}` (a string or FastAPI's list of validation errors) |
| 503 | Database unavailable or not initialised, Open-Meteo/BKK unreachable, real-time not configured | `{"detail": "..."}` |

### Common parameters

| Name | Format | Example |
| --- | --- | --- |
| `bbox` | `minLon,minLat,maxLon,maxLat` | `19.03,47.49,19.07,47.51` |
| `mode` | comma-separated list of `metro`, `hev`, `rail`, `tram`, `trolleybus`, `bus`, `boat`, `other` | `metro,tram` |

---

## System

### `GET /api/health`
Returns `200` when the API can reach the database, and `503` otherwise.
```json
{"status": "ok", "database": "ok", "gtfs_loaded": true}
```

### `GET /api/meta`
Timetable validity, real-time status and the data-source catalogue, which the frontend uses for attribution.
```json
{
  "app": "UrbanVision", "version": "1.0.0", "timezone": "Europe/Budapest",
  "feed": {"publisher_name": "BKK Zrt.", "feed_version": "2770.20260927",
           "valid_from": "2026-09-27", "valid_to": "2026-11-01",
           "imported_at": "2026-09-27T17:47:42Z", "covers_today": true},
  "realtime": {"enabled": false, "provider": null, "message": "Real-time data is not configured. ..."},
  "data_sources": [{"id": "osm", "name": "OpenStreetMap", "license": "Open Database License (ODbL) 1.0",
                    "attribution": "© OpenStreetMap contributors", "data_status": "static", "...": "..."}]
}
```

### `GET /api/stats`
Figures for the dashboard.
```json
{"stops": 5644, "stations": 196, "routes": 389, "trips": 282994, "trips_today": 27809,
 "transport_modes": 6,
 "routes_by_mode": {"bus": 319, "tram": 44, "trolleybus": 16, "hev": 5, "metro": 4, "boat": 1},
 "stops_by_mode": {"bus": 4625, "tram": 657, "trolleybus": 339, "hev": 140, "metro": 103, "boat": 2},
 "urban_features": 798, "feed": {"...": "..."}}
```

---

## Stops

### `GET /api/stops`
Boarding points (GTFS `location_type = 0`) served by at least one line, as GeoJSON points.

| Parameter | Default | Description |
| --- | --- | --- |
| `bbox` | – | Only stops inside this box (uses the spatial index) |
| `mode` | – | Only stops served by at least one of these modes |
| `limit` | 5000 | 1–10000 |

```json
{"type": "FeatureCollection", "features": [
  {"type": "Feature", "id": "007884",
   "geometry": {"type": "Point", "coordinates": [19.055158, 47.497413]},
   "properties": {"stop_id": "007884", "name": "Deák Ferenc tér M", "stop_code": "007884", "modes": ["tram"]}}
]}
```

### `GET /api/stops/{stop_id}`
The stop, the lines serving it (or any of its platforms, for a station), and other platforms of the same interchange: the same parent station, or the same base name within 300 m.
```json
{"stop_id": "F00954", "stop_code": "F00954", "name": "Deák Ferenc tér",
 "latitude": 47.49866, "longitude": 19.054545, "location_type": 0,
 "parent_station": "CSF00954", "wheelchair_boarding": 1, "modes": ["metro"],
 "routes": [{"route_id": "5300", "short_name": "M3", "mode": "metro", "color": "005CA5",
             "text_color": "FFFFFF", "description": "Újpest-központ / Kőbánya-Kispest", "...": "..."}],
 "nearby_platforms": [{"stop_id": "074959", "name": "Deák Ferenc tér M", "modes": ["bus"],
                       "latitude": 47.498429, "longitude": 19.054972, "distance_m": 41.0}]}
```

### `GET /api/stops/{stop_id}/departures`
**Scheduled** departures from the static BKK timetable. For a station, the departures of all its platforms are included. Arrivals at a trip's last stop and stops with `pickup_type = 1` are excluded.

| Parameter | Default | Description |
| --- | --- | --- |
| `date` | today | `YYYY-MM-DD` |
| `time` | now (if `date` is today), otherwise `00:00` | `HH:MM`, Budapest time |
| `minutes` | 120 | Look-ahead window, 1–1440 |
| `limit` | 20 | 1–100 |

Late-night trips are handled correctly. At 00:15, a trip scheduled at GTFS time `24:30:00` on the previous service day is returned with `service_date` set to yesterday and `departure_time` set to today 00:30.

```json
{"stop_id": "F00954", "stop_name": "Deák Ferenc tér",
 "requested_at": "2026-09-27T19:57:00+02:00", "window_minutes": 120,
 "data_status": "scheduled", "schedule_available": true, "notice": null,
 "departures": [
   {"trip_id": "C97763252", "route_id": "5300", "route_short_name": "M3", "mode": "metro",
    "color": "005CA5", "text_color": "FFFFFF", "headsign": "Újpest-központ",
    "service_date": "2026-09-27", "scheduled_time": "20:00:20",
    "departure_time": "2026-09-27T20:00:20+02:00", "minutes_until": 3,
    "wheelchair_accessible": true}]}
```
If the requested date is outside the imported timetable, the response has `schedule_available: false` and a `notice` explains that a newer feed must be imported.

---

## Routes

### `GET /api/routes`
All lines, ordered like BKK's official list (`route_sort_order`).

| Parameter | Description |
| --- | --- |
| `mode` | Filter by mode |
| `q` | Matches the start of the line number, or text in the line name/description (accent-insensitive) |

### `GET /api/routes/geometry`
Line geometry as GeoJSON `MultiLineString`s. Each line contains the most frequent shape per direction, simplified to about 2 m. Lines without shapes are omitted.

| Parameter | Description |
| --- | --- |
| `mode` | Filter by mode (the frontend requests `metro,hev,tram,boat` by default) |
| `route_id` | Comma-separated route IDs |

Feature properties: `route_id`, `short_name`, `mode`, `color`, `text_color`, `description`.

### `GET /api/routes/{route_id}`
```json
{"route_id": "3060", "short_name": "6", "mode": "tram", "route_type": 0,
 "color": "FFD800", "text_color": "000000", "agency_id": "BKK", "agency_name": "BKK",
 "description": "Széll Kálmán tér M / Móricz Zsigmond körtér M", "trips_today": 287,
 "directions": [{"direction_id": 0, "headsign": "Móricz Zs. körtér M",
                 "stops": [{"sequence": 1, "stop_id": "...", "name": "Széll Kálmán tér M",
                            "latitude": 47.507, "longitude": 19.024}]}],
 "geometry": {"type": "MultiLineString", "coordinates": [[[19.02, 47.50], "..."]]}}
```

---

## Search

### `GET /api/search?q=deak&limit=8`
Accent-insensitive search (`q` needs 2–100 characters).
- **Stops** are grouped by name and area (about 1 km), so "Deák Ferenc tér" appears once, with its number of platforms.
- **Routes** match by line number or name.

```json
{"query": "deak",
 "stops": [{"stop_id": "F00954", "name": "Deák Ferenc tér", "latitude": 47.498, "longitude": 19.054,
            "modes": ["metro"], "platform_count": 6}],
 "routes": []}
```

---

## Weather and air quality

Both endpoints default to central Budapest. Custom `lat`/`lon` must lie in the Budapest area (47.30–47.70 N, 18.85–19.35 E); otherwise the response is `422`. Open-Meteo responses are cached for 10 minutes per location.

### `GET /api/weather`
```json
{"location": {"name": "Budapest", "latitude": 47.4979, "longitude": 19.0402},
 "current": {"time": "2026-09-27T19:45", "temperature_c": 21.0, "apparent_temperature_c": 19.7,
             "humidity_percent": 38.0, "precipitation_mm": 0.0, "weather_code": 3,
             "condition": "Overcast", "icon": "cloudy", "is_day": false,
             "wind_speed_kmh": 2.5, "wind_direction_deg": 308.0, "wind_direction": "NW",
             "wind_gusts_kmh": 4.0},
 "hourly": [{"time": "2026-09-27T20:00", "temperature_c": 20.8, "precipitation_probability_percent": 0,
             "precipitation_mm": 0.0, "weather_code": 3, "condition": "Overcast", "icon": "cloudy",
             "is_day": false}],
 "source": "Open-Meteo", "data_status": "model", "fetched_at": "2026-09-27T17:45:10Z",
 "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)"}
```

### `GET /api/air-quality`
```json
{"current": {"time": "2026-09-27T19:00", "european_aqi": 37, "european_aqi_label": "Fair",
             "pm10_ugm3": 13.9, "pm2_5_ugm3": 9.5, "nitrogen_dioxide_ugm3": 22.7, "ozone_ugm3": 75.0},
 "source": "Open-Meteo Air Quality (CAMS Europe)", "data_status": "model", "...": "..."}
```
EAQI bands: ≤20 Good, ≤40 Fair, ≤60 Moderate, ≤80 Poor, ≤100 Very poor, >100 Extremely poor.

---

## Urban layers (OpenStreetMap snapshots)

### `GET /api/layers`
```json
[{"id": "ev_charging", "title": "EV charging stations", "feature_count": 517,
  "imported_at": "2026-09-27T17:58:22Z", "osm_data_timestamp": "2026-09-27T17:57:21Z",
  "data_status": "static", "source": "OpenStreetMap contributors (Overpass API)", "license": "ODbL 1.0"}]
```
The layer IDs are `ev_charging`, `bike_rental` and `park_and_ride`. A layer that has not been imported yet has `feature_count: 0`.

### `GET /api/layers/{layer_id}?bbox=`
GeoJSON points. Feature properties: `name`, `operator`, `osm_url`, and `details`, which holds a curated subset of OSM tags such as capacity, socket types and opening hours.

---

## Real-time (optional)

These endpoints only return data when the backend has `BKK_API_KEY` configured. Without it, `/status` reports `enabled: false`, and the other two return `503` with an explanation.

| Endpoint | Returns |
| --- | --- |
| `GET /api/realtime/status` | `{"enabled": bool, "provider": str \| null, "message": str}` |
| `GET /api/realtime/vehicles?mode=&include_idle=` | Vehicles in passenger service (from BKK `VehiclePositions.pb`, cached for 15 s). Each vehicle is explained with the timetable: line number, mode and colours, `headsign` (where it is going), `final_stop`, `next_stop_name`, `current_status` (`in_transit_to` / `stopped_at` / `incoming_at`), licence plate, accessibility, speed and bearing. Trips missing from the BKK timetable (e.g. MÁV national trains) have `trip_in_timetable: false`, and `headsign` then falls back to BKK's own label. `include_idle=true` adds vehicles without a trip. |
| `GET /api/realtime/alerts` | Service alerts (from BKK `Alerts.pb`); English text is preferred, with Hungarian as the fallback |
