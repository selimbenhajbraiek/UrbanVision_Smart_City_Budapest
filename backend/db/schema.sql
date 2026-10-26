-- UrbanVision database schema (PostgreSQL + PostGIS).
-- Idempotent: safe to run repeatedly (`python -m ingestion init-db`).
-- All geometries use WGS84 (SRID 4326), the coordinate system used by GTFS and OpenStreetMap.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;   -- accent-insensitive search ("Deak" finds "Deák")

-- ---------------------------------------------------------------------------
-- Import metadata: one row per successful GTFS import (latest row = current feed)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feed_info (
    id               SERIAL PRIMARY KEY,
    publisher_name   TEXT,
    feed_version     TEXT,
    feed_start_date  DATE,
    feed_end_date    DATE,
    source           TEXT NOT NULL,          -- URL or local file path
    file_sha256      TEXT,
    imported_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Static GTFS tables (replaced completely on every import)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agencies (
    agency_id  TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    url        TEXT,
    timezone   TEXT,
    phone      TEXT
);

CREATE TABLE IF NOT EXISTS routes (
    route_id    TEXT PRIMARY KEY,
    agency_id   TEXT REFERENCES agencies (agency_id),
    short_name  TEXT,
    long_name   TEXT,
    description TEXT,
    route_type  SMALLINT NOT NULL,
    mode        TEXT NOT NULL,               -- derived: metro|hev|rail|tram|trolleybus|bus|boat|other
    color       CHAR(6),
    text_color  CHAR(6),
    sort_order  INTEGER,
    geom        geometry(MultiLineString, 4326)   -- derived: main shape per direction, simplified
);

CREATE TABLE IF NOT EXISTS stops (
    stop_id              TEXT PRIMARY KEY,
    stop_code            TEXT,
    name                 TEXT NOT NULL,
    geom                 geometry(Point, 4326) NOT NULL,
    location_type        SMALLINT NOT NULL DEFAULT 0,   -- 0 stop/platform, 1 station, 2 entrance, 3 node
    parent_station       TEXT REFERENCES stops (stop_id),
    wheelchair_boarding  SMALLINT,
    modes                TEXT[] NOT NULL DEFAULT '{}'   -- derived: transport modes serving the stop
);

CREATE TABLE IF NOT EXISTS shapes (
    shape_id  TEXT PRIMARY KEY,
    geom      geometry(LineString, 4326) NOT NULL        -- built from shapes.txt points
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id                TEXT PRIMARY KEY,
    route_id               TEXT NOT NULL REFERENCES routes (route_id),
    service_id             TEXT NOT NULL,
    headsign               TEXT,
    direction_id           SMALLINT,
    shape_id               TEXT REFERENCES shapes (shape_id),
    wheelchair_accessible  SMALLINT,
    bikes_allowed          SMALLINT
);

-- Largest table (~5.7M rows for Budapest). Times are stored as seconds since the start
-- of the service day and may exceed 86400 (e.g. 25:10:00 for trips after midnight).
-- Referential integrity to trips/stops is enforced by the importer (orphans are dropped)
-- instead of FK constraints, which would slow the bulk load down considerably.
CREATE TABLE IF NOT EXISTS stop_times (
    trip_id         TEXT NOT NULL,
    stop_sequence   INTEGER NOT NULL,
    stop_id         TEXT NOT NULL,
    arrival_secs    INTEGER,
    departure_secs  INTEGER,
    stop_headsign   TEXT,
    pickup_type     SMALLINT,
    drop_off_type   SMALLINT,
    PRIMARY KEY (trip_id, stop_sequence)
);

-- Optional in GTFS (BKK currently ships only calendar_dates.txt).
CREATE TABLE IF NOT EXISTS calendar (
    service_id  TEXT PRIMARY KEY,
    monday      BOOLEAN NOT NULL,
    tuesday     BOOLEAN NOT NULL,
    wednesday   BOOLEAN NOT NULL,
    thursday    BOOLEAN NOT NULL,
    friday      BOOLEAN NOT NULL,
    saturday    BOOLEAN NOT NULL,
    sunday      BOOLEAN NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_dates (
    service_id      TEXT NOT NULL,
    date            DATE NOT NULL,
    exception_type  SMALLINT NOT NULL,   -- 1 = service added, 2 = service removed
    PRIMARY KEY (service_id, date)
);

-- ---------------------------------------------------------------------------
-- Derived tables (computed at import time so API queries stay fast)
-- ---------------------------------------------------------------------------
-- Concrete dates on which each service_id runs (calendar rules + exceptions).
CREATE TABLE IF NOT EXISTS service_dates (
    service_date  DATE NOT NULL,
    service_id    TEXT NOT NULL,
    PRIMARY KEY (service_date, service_id)
);

-- Which routes serve which stops (avoids scanning stop_times on every click).
CREATE TABLE IF NOT EXISTS route_stops (
    stop_id   TEXT NOT NULL REFERENCES stops (stop_id),
    route_id  TEXT NOT NULL REFERENCES routes (route_id),
    PRIMARY KEY (stop_id, route_id)
);

-- ---------------------------------------------------------------------------
-- Additional urban data (Phase 8): static snapshots of OpenStreetMap features
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS urban_pois (
    category  TEXT NOT NULL,             -- ev_charging | bike_sharing | park_and_ride
    osm_type  TEXT NOT NULL,             -- node | way | relation
    osm_id    BIGINT NOT NULL,
    name      TEXT,
    operator  TEXT,
    tags      JSONB NOT NULL DEFAULT '{}',
    geom      geometry(Point, 4326) NOT NULL,
    PRIMARY KEY (category, osm_type, osm_id)
);

CREATE TABLE IF NOT EXISTS urban_layer_imports (
    category          TEXT PRIMARY KEY,
    feature_count     INTEGER NOT NULL,
    osm_data_timestamp TEXT,             -- "timestamp_osm_base" reported by Overpass
    imported_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS stops_geom_idx            ON stops USING GIST (geom);
CREATE INDEX IF NOT EXISTS stops_parent_station_idx  ON stops (parent_station);
CREATE INDEX IF NOT EXISTS stops_modes_idx           ON stops USING GIN (modes);
CREATE INDEX IF NOT EXISTS routes_geom_idx           ON routes USING GIST (geom);
CREATE INDEX IF NOT EXISTS routes_mode_idx           ON routes (mode);
CREATE INDEX IF NOT EXISTS trips_route_idx           ON trips (route_id);
CREATE INDEX IF NOT EXISTS trips_service_idx         ON trips (service_id);
CREATE INDEX IF NOT EXISTS stop_times_departures_idx ON stop_times (stop_id, departure_secs);
CREATE INDEX IF NOT EXISTS route_stops_route_idx     ON route_stops (route_id);
CREATE INDEX IF NOT EXISTS urban_pois_geom_idx       ON urban_pois USING GIST (geom);
