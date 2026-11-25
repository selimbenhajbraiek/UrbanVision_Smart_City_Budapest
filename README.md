# UrbanVision — Real-Time Smart City Map for Budapest

UrbanVision is an interactive web application that shows open urban data for Budapest on a
single map: BKK public transport (stops, lines, scheduled departures), current weather and air
quality, and smart-city infrastructure such as EV chargers, bike sharing and Park & Ride.

> University project · Category: Map-based Smart City application
> **Team:** Selim Ben Haj Braiek (project leader, Neptun N5OQI9) · Nour Ounissi (Neptun RSPN69)

**Honest data labels.** Every dataset in the interface is tagged with its nature:
**Scheduled** (official timetable), **Model** (weather model output), **Static** (snapshot) or
**Live** (real-time). Live transport data is only shown if a BKK API key is configured
(see [Future improvements](#16-future-improvements)). UrbanVision never simulates live data.

> **Already running an older copy of the project?** The user accounts, admin dashboard and route
> planner need three extra setup steps. See
> [Updating an existing installation](#updating-an-existing-installation).

---

## Contents

1. [Project description](#1-project-description)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
4. [Technology stack](#4-technology-stack)
5. [Installation](#5-installation)
6. [Environment variables](#6-environment-variables)
7. [Database setup](#7-database-setup)
8. [GTFS import](#8-gtfs-import)
9. [Running the backend](#9-running-the-backend)
10. [Running the frontend](#10-running-the-frontend)
11. [API documentation](#11-api-documentation)
12. [Testing](#12-testing)
13. [Data sources](#13-data-sources)
14. [Licences and attribution](#14-licences-and-attribution)
15. [Known limitations](#15-known-limitations)
16. [Future improvements](#16-future-improvements)

---

## 1. Project description

Cities publish more and more open data, but it is scattered across portals and formats.
UrbanVision brings several of these sources together on one map of Budapest:

- **OpenStreetMap** provides the geographic base map and static infrastructure layers.
- **BKK GTFS** provides the complete public-transport timetable: about 6,000 stops, 389 lines
  and 5.7 million scheduled stop events.
- **Open-Meteo** provides weather and air quality from numerical models, with no API key.

The system is designed so that real-time sources (live vehicle positions, delays, disruptions)
can be plugged in later without changing the rest of the application.

## 2. Features

| Area | What you can do |
| --- | --- |
| Map | Pan and zoom Budapest, switch between muted and standard OSM base maps, reset the view |
| Public transport | See stops coloured by mode (metro, HÉV, tram, trolleybus, bus, boat). Low-importance stops only appear when you zoom in, which keeps the map uncluttered. |
| Lines | Show route geometry per mode in BKK's official colours; click a line to open it |
| Stop details | Name, ID, accessibility, lines serving the stop, **next scheduled departures** (refreshed every minute), and other platforms of the same interchange |
| Line details | Operator, trips today, both directions with their ordered stops. The line is highlighted and the map zooms to it. |
| Search | Accent-insensitive search for stops and lines (`deak`, `M2`, `47`) |
| Route planner | **Plan trip** from A to B: choose places by searching a stop, clicking the map, or "From here" / "To here" on a stop. Shows up to three public-transport journeys (plus a walking option for short trips) with times, changes and walking, explains the chosen one step by step, and draws it on the map. Based on the scheduled timetable. |
| User accounts | Register, log in and log out. Passwords are hashed (Argon2) and sessions use signed tokens (JWT). The map itself stays public. |
| Admin dashboard | `/admin`, for administrators only: user and data figures, user management (promote, deactivate, delete), and the status of the imported data (timetable validity, OpenStreetMap layers, real-time). |
| Weather | Temperature, condition, feels-like temperature, wind, precipitation, humidity and a 6-hour forecast |
| Air quality | European AQI, PM2.5, PM10, NO₂ and O₃ (CAMS model data) |
| Urban data | EV charging stations (517), bike sharing and rental (228), Park & Ride (53), from OpenStreetMap |
| Layers | One panel toggles every layer. The configuration and the selected stop or line are stored in the URL, so demo views can be bookmarked. |
| Dashboard | Mapped stops, routes, transport modes, trips today, weather, active layers, timetable validity, real-time status |
| Real-time (optional) | With a BKK API key: live vehicles, drawn as line-number badges with a heading arrow. Clicking one shows the line, destination, next stop, speed and vehicle. Service alerts are also available through the API. |
| Responsive | Works on desktop and mobile; on phones the side panel becomes a bottom sheet |

## 3. Architecture

```text
┌──────────────────────── DATA SOURCES ─────────────────────────┐
│ BKK GTFS zip     OpenStreetMap        Open-Meteo    BKK GTFS-RT │
│ (timetable)      (tiles, Overpass)    (weather/AQ)  (optional)  │
└──────┬─────────────────┬──────────────────┬────────────┬──────┘
       │ batch import    │ batch import     │ on demand  │ on demand
       ▼                 ▼                  │ (cached)   │ (cached)
┌──────────────────────────────┐           │            │
│ Ingestion CLI (python -m     │           │            │
│ ingestion): download →       │           │            │
│ extract → validate → load →  │           │            │
│ derive                       │           │            │
└──────────────┬───────────────┘           │            │
               ▼                           ▼            ▼
┌──────────────────────────┐   ┌──────────────────────────────────┐
│ PostgreSQL 17 + PostGIS  │◄──│ FastAPI backend                  │
│ (Docker)                 │   │ routers → services → repositories │
└──────────────────────────┘   └───────────────┬──────────────────┘
                                               │ REST: JSON + GeoJSON
                                               ▼
                               ┌──────────────────────────────────┐
                               │ React + TypeScript + Leaflet     │──► OSM tiles
                               └──────────────────────────────────┘
```

Key design decisions:

- **Import is a separate batch job.** The API only reads, and the GTFS import runs in a single
  transaction, so users never see a half-imported timetable.
- **Derived tables are computed at import time** (service dates, route↔stop links, stop modes,
  simplified route lines). This lets API requests answer in about 20–50 ms, even with 5.7 M stop times.
- **GeoJSON is built inside PostGIS** and streamed as text, then gzipped by the API.
- **External APIs are only called by the backend,** with a 10-minute cache, so the browser never
  talks to third parties except for map tiles.
- **Real-time sources sit behind an interface** (`RealtimeProvider`). Without a key, a
  "disabled" provider is used and the UI clearly says so.

More detail: [docs/architecture.md](docs/architecture.md).

### Folder structure

```text
UrbanVision_Smart_City_Budapest/
├── docker-compose.yml          # PostgreSQL + PostGIS
├── .env.example                # configuration template (copy to .env)
├── docs/                       # architecture, API, database, data sources
├── backend/
│   ├── pyproject.toml          # pinned dependencies, pytest and ruff config
│   ├── db/schema.sql           # tables and indexes
│   ├── app/                    # FastAPI application
│   │   ├── main.py             # app factory, middleware, error handlers
│   │   ├── config.py           # settings from environment / .env
│   │   ├── security.py         # password hashing (Argon2) and login tokens (JWT)
│   │   ├── api/                # HTTP routers (one file per resource, incl. auth, admin, planner)
│   │   ├── repositories/       # all SQL queries
│   │   ├── services/           # weather client, departure-time logic, cache, route planner
│   │   ├── schemas/            # Pydantic response models
│   │   └── realtime/           # real-time provider interface + BKK GTFS-RT client
│   ├── ingestion/              # CLI: GTFS and OpenStreetMap importers, create-admin
│   └── tests/                  # pytest suite + mini GTFS fixture feed
└── frontend/
    ├── package.json
    ├── vite.config.ts          # dev proxy /api → backend
    └── src/
        ├── main.tsx            # page routes: / (map), /login, /register, /admin
        ├── api/                # fetch client (sends the login token) + TypeScript API types
        ├── auth/               # login state (AuthContext) and the admin-only guard
        ├── pages/              # login, register and admin dashboard pages
        ├── config/             # transport modes, map, layer state
        ├── hooks/useApi.ts     # data fetching hook
        ├── components/         # map layers, panels, dashboard, header, admin, planner
        └── styles/global.css
```

## 4. Technology stack

| Layer | Technology | Why |
| --- | --- | --- |
| Frontend | React 19, TypeScript 7, Vite 8 | Typed API responses and fast development server |
| Map | Leaflet 1.9 + react-leaflet 5 | Free OSM raster tiles with no API key; simple to learn; canvas rendering for thousands of markers |
| Backend | Python 3.11+ (tested on 3.13), FastAPI | Automatic validation and interactive API docs at `/docs` |
| DB access | psycopg 3 (plain SQL, connection pool) | PostGIS functions and bulk `COPY` are clearest as SQL |
| Database | PostgreSQL 17 + PostGIS 3.5 (Docker) | Spatial indexes, geometry functions, GeoJSON output |
| Data processing | pandas | Reading, cleaning and validating GTFS CSV files |
| HTTP client | httpx | Open-Meteo, Overpass, BKK real-time |
| Accounts | pwdlib (Argon2), PyJWT, react-router | Safe password storage, stateless login tokens, separate login/admin pages |
| Route planner | Connection Scan Algorithm (own implementation) | Runs on the imported GTFS timetable, no external routing service or API key |
| Tests | pytest, respx (HTTP mocking), Vitest, Testing Library | |
| Lint and format | ruff, `tsc --noEmit` | |

## 5. Installation

**Prerequisites:** Git, Docker Desktop, Python ≥ 3.11 and Node.js ≥ 20.19 (22 LTS recommended).

```bash
git clone <your-repo-url> UrbanVision_Smart_City_Budapest
cd UrbanVision_Smart_City_Budapest

# 1. Configuration: copy the template, then edit .env
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
#    - change POSTGRES_PASSWORD
#    - set JWT_SECRET_KEY to a long random value (needed for log in), e.g. the output of:
#      python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Database
docker compose up -d db

# 3. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"

# 4. Data and first admin account (see sections 7 and 8)
python -m ingestion init-db
python -m ingestion gtfs
python -m ingestion osm
python -m ingestion create-admin --email admin@example.com   # asks for a password

# 5. Frontend
cd ../frontend
npm install
```

### Updating an existing installation

If you already had UrbanVision running before the **user accounts, admin dashboard and route
planner** were added, do this once after pulling the new code (`git pull`):

```bash
# 1. Add a login secret to the project-root .env (keep it private, never commit it)
python -c "import secrets; print(secrets.token_urlsafe(48))"
#    copy the output into .env:   JWT_SECRET_KEY=<the value>
#    optional:                    JWT_EXPIRE_MINUTES=60

# 2. Install the new dependencies
cd backend
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"         # adds pyjwt and pwdlib[argon2]
cd ../frontend
npm install                     # adds react-router-dom

# 3. Create the new `users` table (existing data is kept) and your admin account
cd ../backend
python -m ingestion init-db
python -m ingestion create-admin --email admin@example.com
```

Then restart the backend (`uvicorn ...`) so it reads the new `.env` value.

- **Without `JWT_SECRET_KEY`** the map and the route planner still work, but log in and register
  answer *503 "Login is not configured"*.
- **Without `init-db`** the login and admin endpoints answer *503 "Database is not initialised"*.
- The route planner needs no extra step: it uses the timetable that is already imported.

## 6. Environment variables

Everything is configured in the project-root `.env` file. Docker Compose and the backend both
read it, and `.env` is git-ignored. **Never commit secrets.**

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_USER` | `urbanvision` | Database user |
| `POSTGRES_PASSWORD` | *(required)* | Database password |
| `POSTGRES_DB` | `urbanvision` | Main database |
| `POSTGRES_TEST_DB` | `urbanvision_test` | Database used by the automated tests (created automatically) |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5433` | Host port. 5433 avoids clashing with a locally installed PostgreSQL. |
| `LOG_LEVEL` | `INFO` | Backend log level |
| `CORS_ORIGINS` | `http://localhost:5173,…` | Browser origins allowed to call the API |
| `GTFS_URL` | `https://bkk.hu/gtfs/budapest_gtfs.zip` | Official BKK feed |
| `OPEN_METEO_FORECAST_URL` | `https://api.open-meteo.com/v1/forecast` | Weather API |
| `OPEN_METEO_AIR_QUALITY_URL` | `https://air-quality-api.open-meteo.com/v1/air-quality` | Air-quality API |
| `WEATHER_CACHE_TTL_SECONDS` | `600` | How long weather responses are cached |
| `OVERPASS_URL` | `https://overpass-api.de/api/interpreter` | OpenStreetMap query API |
| `BKK_API_KEY` | *(empty)* | Optional: enables live vehicles and alerts (free key from opendata.bkk.hu) |
| `JWT_SECRET_KEY` | *(required for log in)* | Secret that signs login tokens. Use a long random value; changing it logs everyone out. |
| `JWT_EXPIRE_MINUTES` | `60` | How long a login stays valid |

Frontend (optional, `frontend/.env.local`): `VITE_API_BASE_URL` for production builds served
from another host, and `VITE_PROXY_TARGET` if the backend is not on `127.0.0.1:8000`.

## 7. Database setup

```bash
docker compose up -d db                     # starts PostgreSQL 17 + PostGIS on port 5433
docker compose ps                           # should show "healthy"
cd backend && python -m ingestion init-db   # creates tables and indexes (the importers also do this)
```

The schema lives in [backend/db/schema.sql](backend/db/schema.sql) and is idempotent (safe to
re-run). Tables, relationships and indexes are explained in
[docs/database.md](docs/database.md). The main GTFS tables are `agencies`, `routes`, `stops`,
`trips`, `stop_times`, `calendar`, `calendar_dates` and `shapes`. The derived tables are
`service_dates` and `route_stops`, and `urban_pois` holds the OpenStreetMap layers. `users`
holds the accounts (e-mail, Argon2 password hash, role `user` or `admin`, active flag); the
GTFS and OpenStreetMap importers never touch it.

To inspect the database:
`docker exec -it urbanvision-db psql -U urbanvision -d urbanvision`

## 8. GTFS import

```bash
cd backend
python -m ingestion gtfs                          # download the official BKK feed and import it
python -m ingestion gtfs --file path/to/feed.zip  # import a local ZIP (or an extracted folder)
python -m ingestion gtfs --force                  # re-import even if the file is unchanged
python -m ingestion osm                           # import the OpenStreetMap urban layers
```

The pipeline, in `backend/ingestion/gtfs/`:

1. **Download.** The ZIP (about 60 MB) is streamed to `backend/data/gtfs/`. If its SHA-256 matches
   the last import, the import is skipped.
2. **Extract.** Files are extracted to a temporary folder, protected against path tricks in
   the archive.
3. **Validate.** The importer checks required files and columns. `calendar.txt` is optional,
   because BKK ships only `calendar_dates.txt`. Rows with invalid coordinates, times, route
   types or dangling references are dropped, and each drop is reported.
4. **Load.** Rows are cleaned with pandas and bulk-loaded with PostgreSQL `COPY`.
   `stop_times.txt` (441 MB) is streamed in 500k-row chunks.
5. **Derive.** The importer builds service dates, route↔stop links, the modes serving each
   stop, and simplified route lines.

Everything runs in **one transaction**: if anything fails, the previous timetable stays intact.
A full Budapest import takes **about 3–4 minutes** and uses about 0.9 GB of disk.

Example output:

```text
Imported GTFS in 196.4s
  agencies                       2
  routes                       389
  stops                      6,018
  shapes                     1,593
  trips                    282,994
  stop_times             5,729,142
  calendar_dates             9,874
  service_dates              9,874
  route_stops               17,549
  warnings: 0
```

> The BKK feed covers only about 5 weeks ahead. **Re-import before a demo.** The UI warns you
> when today is outside the imported timetable.

### Admin account

There is no public way to become an admin. Create the first one from the command line:

```bash
cd backend
python -m ingestion create-admin --email admin@example.com   # asks for the password twice (min. 8 characters)
```

Running it again with an existing e-mail promotes that user to admin and resets the password.
After that, admins can promote other users from the dashboard at <http://localhost:5173/admin>.

## 9. Running the backend

```bash
cd backend
.venv\Scripts\activate                      # macOS/Linux: source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/api/health>
- Interactive API docs (Swagger): <http://localhost:8000/docs>

## 10. Running the frontend

```bash
cd frontend
npm run dev          # http://localhost:5173 (proxies /api to the backend)
npm run build        # production build in frontend/dist (type-checks first)
```

## 11. API documentation

All endpoints live under `/api`. Data endpoints are `GET`; only the account and admin
endpoints use `POST`, `PATCH` and `DELETE`. Map layers return **GeoJSON**
(`application/geo+json`) and everything else returns JSON. Errors always have the form
`{"detail": "…"}`: **401** when a login is required, **403** when admin rights are required,
**404** for an unknown stop, route, layer or user, **409** for a conflict (e-mail already
registered, removing the last admin), **422** for invalid parameters, and **503** when the
database or an upstream service is unavailable.

| Endpoint | Description |
| --- | --- |
| `GET /api/health` | API and database status |
| `GET /api/meta` | Timetable validity, real-time status, data sources and licences |
| `GET /api/stats` | Dashboard figures |
| `GET /api/stops?bbox=&mode=&limit=` | Stops as GeoJSON (filter by bounding box and mode) |
| `GET /api/stops/{stop_id}` | Stop details, lines, other platforms of the interchange |
| `GET /api/stops/{stop_id}/departures?date=&time=&minutes=&limit=` | **Scheduled** departures |
| `GET /api/routes?mode=&q=` | All lines |
| `GET /api/routes/geometry?mode=&route_id=` | Line geometry as GeoJSON |
| `GET /api/routes/{route_id}` | Line details: directions, stops, trips today, geometry |
| `GET /api/search?q=` | Search stops and lines |
| `GET /api/weather?lat=&lon=` | Current weather and 12-hour forecast (default: central Budapest) |
| `GET /api/air-quality?lat=&lon=` | European AQI and pollutants |
| `GET /api/layers` | Additional urban layers and their import status |
| `GET /api/layers/{layer_id}?bbox=` | Layer features as GeoJSON |
| `GET /api/realtime/status` | Whether live data is configured |
| `GET /api/realtime/vehicles?mode=` | Live vehicle positions (503 unless `BKK_API_KEY` is set) |
| `GET /api/realtime/alerts` | Live service alerts (503 unless `BKK_API_KEY` is set) |
| `GET /api/plan?from=lat,lon&to=lat,lon&date=&time=` | **Route planner:** up to three journeys from A to B, plus a walking option (scheduled timetable) |
| `POST /api/auth/register` | Create an account (`{"email", "password"}`, password ≥ 8 characters) and log in |
| `POST /api/auth/login` | Log in; returns a bearer token |
| `GET /api/auth/me` | The logged-in user (needs `Authorization: Bearer <token>`) |
| `GET /api/admin/stats` | *Admin:* user and data figures |
| `GET /api/admin/users` | *Admin:* list of users |
| `PATCH /api/admin/users/{id}` | *Admin:* change role (`user`/`admin`) or activate/deactivate |
| `DELETE /api/admin/users/{id}` | *Admin:* delete a user |
| `GET /api/admin/data-status` | *Admin:* timetable validity, OpenStreetMap layer imports, real-time status |

In Swagger (`/docs`), log in with `POST /api/auth/login`, copy the `access_token`, and paste it
into the **Authorize** button to try the admin endpoints.

**Route planner algorithm.** `GET /api/plan` runs the Connection Scan Algorithm on the next
2.5 hours of the imported timetable: walk up to 800 m to and from stops, change between stops up
to 250 m apart, 60 s minimum change time. It returns the earliest arrival first and the next
departures as alternatives (about 0.4 s for Budapest). Details:
[backend/app/services/planner.py](backend/app/services/planner.py).

Full parameter descriptions and example responses: [docs/api.md](docs/api.md). The live
Swagger UI at `/docs` lets you try every endpoint.

## 12. Testing

### Automated tests

```bash
docker compose up -d db              # database tests need PostgreSQL running
cd backend && pytest                 # 136 tests
cd frontend && npm test              # 41 tests
cd frontend && npm run typecheck
cd backend && ruff check . && ruff format --check .
```

**Backend (pytest).** The database tests import a hand-made **mini GTFS feed**
(`backend/tests/fixtures/mini_gtfs/`) into the separate `urbanvision_test` database. The feed
deliberately includes the tricky cases: no `calendar.txt`, times after midnight (`24:30:00`),
IDs with leading zeros, a station with platforms, an entrance, an unused stop, a stop without
coordinates, an invalid route type, orphan rows and an invalid time. The tests cover:

| Area | Test file |
| --- | --- |
| GTFS parsing and validation | `test_gtfs_validation.py` |
| GTFS import and database content | `test_gtfs_import.py` |
| Stops, departures, search and invalid requests | `test_api_stops.py` |
| Routes, meta, stats and health | `test_api_routes.py` |
| Weather and air quality (mocked Open-Meteo, cache, errors) | `test_weather.py` |
| Service-day time maths, including daylight-saving days | `test_schedule_time.py` |
| OpenStreetMap layers (parsing, retries, storage, API) | `test_urban_layers.py` |
| Real-time provider (synthetic GTFS-RT protobuf) | `test_realtime.py` |
| Register, log in, tokens (expired, forged), deactivated users | `test_auth.py` |
| Admin access rules (401/403), user management, data status, `create-admin` | `test_admin.py` |
| Route planner: direct and walking-transfer trips, after-midnight trips, no service, invalid requests, the scan algorithm itself | `test_planner.py` |

No test calls the internet: every external API is mocked with `respx`.

**Frontend (Vitest).** The tests cover layer and URL state, transport-mode rules, formatting
(including Budapest time zone handling), component rendering (dashboard, weather card, badges),
log in and the admin-only page guard, the admin users table and data status, and the route
planner (journey list, step-by-step view, panel).

### Manual test checklist

Start the database, backend and frontend, then open <http://localhost:5173>:

1. The map shows Budapest, and the bottom-right attribution reads "© OpenStreetMap
   contributors, Timetable: BKK GTFS".
2. The dashboard shows about 5,600 stops, 389 routes, 6 transport modes, trips today, weather,
   and the timetable dates.
3. At the default zoom, only metro, HÉV and boat stops are visible, and a hint says to zoom in
   for tram and bus stops. After zooming in, those stops appear.
4. Click a metro stop (for example Deák Ferenc tér). The side panel shows its lines, next
   departures marked **Scheduled**, and other platforms of the interchange.
5. Click a line badge. The line is highlighted, the map zooms to it, and both directions
   list their stops.
6. Search for `deak` (without the accent) and for `M2`. Choosing a result opens it.
7. In **Data layers**, switch on Bus lines (a dense network appears), EV charging stations
   (click one for a popup), and the "None" base map.
8. Reload the page. The layer choice and the selected stop are restored from the URL.
9. Collapse and expand the weather card. The air-quality AQI badge is colour-coded.
10. Open **Data sources**. The table lists every source with its licence and data type.
11. Stop the backend. The UI shows "Cannot reach the UrbanVision API" instead of crashing.
12. Try invalid API calls in the browser:
    `/api/stops/NOPE` returns 404 and `/api/stops?bbox=1,2` returns 422.
13. Narrow the browser window (under 900 px). The panel becomes a bottom sheet and the
    header buttons collapse to icons.
14. Click **Plan trip**. Choose A by typing `deak` and B with the pin button and a click on the
    map. Up to three journeys appear (marked **Scheduled**); the chosen one is explained step by
    step and drawn on the map between the A and B pins.
15. Open a stop and click **From here**: the planner opens with that stop as A.
16. Click **Log in** → **Create one**, register a user, then open `/admin`: you see
    "Access denied".
17. Log in with the admin account from `create-admin`. **Admin** appears in the header; the
    dashboard shows the figures, the users (promote, deactivate, delete) and the data status.

## 13. Data sources

| Dataset | Source | Licence | Update frequency | Access | Format | Data type |
| --- | --- | --- | --- | --- | --- | --- |
| Base map tiles | OpenStreetMap tile server | ODbL 1.0 (data), CC BY-SA 2.0 (tiles) | Continuous | HTTPS tiles | PNG | Static |
| Public transport | [BKK GTFS](https://bkk.hu/bkk-partnerek/egyeb/gtfs-menetrendi-adatok-programozoknak/) | Publicly released by BKK; no explicit licence stated | Monthly, sometimes weekly; about 5 weeks ahead | ZIP download | GTFS (CSV) | Scheduled |
| Weather | [Open-Meteo Forecast API](https://open-meteo.com/) | CC BY 4.0, free for non-commercial use | 15 min (model) | REST, no key | JSON | Model |
| Air quality | [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) (Copernicus CAMS) | CC BY 4.0 | Hourly (model) | REST, no key | JSON | Model |
| EV charging, bike sharing, P+R | OpenStreetMap via [Overpass API](https://overpass-api.de/) | ODbL 1.0 | Snapshot on import | Overpass QL | JSON | Static |
| Live vehicles and alerts (optional) | [BKK OpenData / FUTÁR](https://opendata.bkk.hu/) | BKK terms of use | Seconds | GTFS-Realtime, API key | Protobuf | Live |

Per-dataset limitations, and datasets that were investigated but not added (traffic, parking
occupancy, sensor-based air quality), are documented in
[docs/data-sources.md](docs/data-sources.md).

## 14. Licences and attribution

- **OpenStreetMap:** "© OpenStreetMap contributors", linked to
  <https://www.openstreetmap.org/copyright>. It is always visible in the map's attribution
  control. We follow the [tile usage policy](https://operations.osmfoundation.org/policies/tiles/):
  standard tile URL, low traffic, attribution, no bulk downloading.
- **BKK:** "Timetable: BKK GTFS" is shown in the map attribution and in the Data sources dialog.
  Departures are labelled as scheduled.
- **Open-Meteo:** "Weather data by Open-Meteo.com (CC BY 4.0)" is shown on the weather card.
- **Overpass:** requests identify the application with a User-Agent, and the importer backs off
  when the server is busy (HTTP 429 or 504).
- **Source code:** university project. Add a licence file (for example MIT) if the repository
  is published.

## 15. Known limitations

- **Transit data is scheduled, not live.** Departures do not include delays or cancellations
  unless the optional real-time provider is enabled. Even then, delays are not yet merged into
  departures (see below).
- **The timetable expires.** The BKK feed covers about 5 weeks, so it must be re-imported
  regularly (there is no scheduler).
- **Route geometry is simplified.** It shows the most frequent pattern per direction. Short
  workings and depot runs are not drawn (5 of 389 routes have no shape).
- **"Other platforms" is a heuristic.** Platforms are grouped by the same parent station, or by
  the same base name within 300 m.
- **Weather and air quality are model outputs** for one point (central Budapest), not sensor
  readings.
- **OSM layers are snapshots.** They show where chargers and bike docks are, not whether they
  are free right now.
- **Public tile and Overpass servers** are shared community resources, suitable for a demo but
  not for heavy production traffic.
- **Daylight-saving days:** schedule times follow the GTFS "noon minus 12 h" rule. Trips
  scheduled in the skipped or repeated hour may appear shifted by one hour.
- The real-time client is tested against the GTFS-Realtime specification with synthetic data.
  It has **not** been tested against the live BKK endpoint without an API key.
- **Route planner:** it uses the scheduled timetable (no delays), estimates walking as a straight
  line × 1.25 rather than along real streets, optimises the earliest arrival (not the fewest
  changes), only searches the next 2.5 hours, and draws vehicle legs stop to stop rather than
  along the exact line shape.
- **Accounts:** there is no password reset by e-mail (an admin can rerun `create-admin`), and
  logging out only forgets the token in the browser; the token stays valid until it expires
  (60 min by default). Deactivated or deleted users lose access immediately.

## 16. Future improvements

- **Route planner:** live delays (with `BKK_API_KEY`), a multi-criteria search (time *and*
  changes, e.g. RAPTOR), walking along real streets, an accessible-only option and
  "arrive by" times.

- **Real-time (Phase 10 design is ready).** Register at <https://opendata.bkk.hu/> and set
  `BKK_API_KEY` to enable live vehicle positions and alerts. Next steps:
  - Use `TripUpdates.pb` to show delays next to the scheduled departures (`data_status: "realtime"`).
  - Show alerts in the stop and line panels.
  - Add live bike-sharing availability (GBFS) and live parking occupancy, if an open source becomes available.
  - See [docs/architecture.md](docs/architecture.md#real-time-extension-phase-10).
- Scheduled GTFS re-import (for example a nightly cron job or GitHub Actions).
- Docker images for the backend and frontend, so the whole stack runs with one `docker compose up`.
- Accessibility filters (wheelchair-accessible stops and vehicles are already in the data).
- Trip planner or isochrones ("where can I get in 20 minutes?").
- CI pipeline running the test suites on every pull request.
