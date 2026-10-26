// TypeScript mirrors of the backend's Pydantic response models (see backend/app/schemas).
import type { MultiLineString } from "geojson";

export type Mode = "metro" | "hev" | "rail" | "tram" | "trolleybus" | "bus" | "boat" | "other";
export type DataStatus = "scheduled" | "realtime" | "model" | "static";

export interface RouteSummary {
  route_id: string;
  short_name: string | null;
  long_name: string | null;
  description: string | null;
  mode: Mode;
  route_type: number;
  color: string | null;
  text_color: string | null;
  agency_id: string | null;
}

export interface StopSummary {
  stop_id: string;
  name: string;
  latitude: number;
  longitude: number;
  modes: Mode[];
  distance_m: number | null;
}

export interface StopDetail {
  stop_id: string;
  stop_code: string | null;
  name: string;
  latitude: number;
  longitude: number;
  location_type: number;
  parent_station: string | null;
  wheelchair_boarding: number | null;
  modes: Mode[];
  routes: RouteSummary[];
  nearby_platforms: StopSummary[];
}

export interface RouteStop {
  sequence: number;
  stop_id: string;
  name: string;
  latitude: number;
  longitude: number;
}

export interface RouteDirection {
  direction_id: number;
  headsign: string | null;
  stops: RouteStop[];
}

export interface RouteDetail extends RouteSummary {
  agency_name: string | null;
  trips_today: number;
  directions: RouteDirection[];
  geometry: MultiLineString | null;
}

export interface Departure {
  trip_id: string;
  route_id: string;
  route_short_name: string | null;
  mode: Mode;
  color: string | null;
  text_color: string | null;
  headsign: string | null;
  service_date: string;
  scheduled_time: string;
  departure_time: string;
  minutes_until: number;
  wheelchair_accessible: boolean | null;
}

export interface DeparturesResponse {
  stop_id: string;
  stop_name: string;
  requested_at: string;
  window_minutes: number;
  data_status: DataStatus;
  schedule_available: boolean;
  notice: string | null;
  departures: Departure[];
}

export interface StopSearchResult {
  stop_id: string;
  name: string;
  latitude: number;
  longitude: number;
  modes: Mode[];
  platform_count: number;
}

export interface SearchResponse {
  query: string;
  stops: StopSearchResult[];
  routes: RouteSummary[];
}

export interface FeedInfo {
  publisher_name: string | null;
  feed_version: string | null;
  valid_from: string | null;
  valid_to: string | null;
  imported_at: string;
  covers_today: boolean;
}

export interface DataSource {
  id: string;
  name: string;
  url: string;
  provides: string;
  license: string;
  attribution: string;
  data_status: DataStatus;
  update_frequency: string;
}

export interface RealtimeStatus {
  enabled: boolean;
  provider: string | null;
  message: string;
}

export interface MetaResponse {
  app: string;
  version: string;
  timezone: string;
  feed: FeedInfo | null;
  realtime: RealtimeStatus;
  data_sources: DataSource[];
}

export interface StatsResponse {
  stops: number;
  stations: number;
  routes: number;
  trips: number;
  trips_today: number;
  transport_modes: number;
  routes_by_mode: Partial<Record<Mode, number>>;
  stops_by_mode: Partial<Record<Mode, number>>;
  urban_features: number;
  feed: FeedInfo | null;
}

export interface CurrentWeather {
  time: string;
  temperature_c: number;
  apparent_temperature_c: number | null;
  humidity_percent: number | null;
  precipitation_mm: number | null;
  weather_code: number;
  condition: string;
  icon: string;
  is_day: boolean | null;
  wind_speed_kmh: number;
  wind_direction_deg: number | null;
  wind_direction: string | null;
  wind_gusts_kmh: number | null;
}

export interface HourlyForecast {
  time: string;
  temperature_c: number | null;
  precipitation_probability_percent: number | null;
  precipitation_mm: number | null;
  weather_code: number | null;
  condition: string | null;
  icon: string | null;
  is_day: boolean | null;
}

export interface WeatherResponse {
  location: { name: string; latitude: number; longitude: number };
  current: CurrentWeather;
  hourly: HourlyForecast[];
  source: string;
  data_status: DataStatus;
  fetched_at: string;
  attribution: string;
}

export interface AirQualityResponse {
  location: { name: string; latitude: number; longitude: number };
  current: {
    time: string;
    european_aqi: number | null;
    european_aqi_label: string | null;
    pm10_ugm3: number | null;
    pm2_5_ugm3: number | null;
    nitrogen_dioxide_ugm3: number | null;
    ozone_ugm3: number | null;
  };
  source: string;
  data_status: DataStatus;
  fetched_at: string;
  attribution: string;
}

export interface UrbanLayerInfo {
  id: string;
  title: string;
  description: string;
  feature_count: number;
  imported_at: string | null;
  osm_data_timestamp: string | null;
  data_status: DataStatus;
  source: string;
  license: string;
}

export interface Vehicle {
  vehicle_id: string;
  label: string | null;
  license_plate: string | null;
  wheelchair_accessible: boolean | null;
  in_service: boolean;
  trip_id: string | null;
  trip_in_timetable: boolean;
  route_id: string | null;
  route_short_name: string | null;
  route_description: string | null;
  mode: Mode | null;
  color: string | null;
  text_color: string | null;
  headsign: string | null;
  final_stop: string | null;
  next_stop_id: string | null;
  next_stop_name: string | null;
  current_status: "in_transit_to" | "stopped_at" | "incoming_at" | null;
  latitude: number;
  longitude: number;
  bearing: number | null;
  speed_kmh: number | null;
  timestamp: string | null;
}

export interface VehiclesResponse {
  data_status: DataStatus;
  provider: string;
  feed_timestamp: string | null;
  fetched_at: string;
  vehicles: Vehicle[];
}

// GeoJSON feature properties produced by the backend
export interface StopFeatureProps {
  stop_id: string;
  name: string;
  stop_code: string | null;
  modes: Mode[];
}

export interface RouteFeatureProps {
  route_id: string;
  short_name: string | null;
  mode: Mode;
  color: string | null;
  text_color: string | null;
  description: string | null;
}

export interface UrbanFeatureProps {
  name: string | null;
  operator: string | null;
  osm_url: string;
  details: Record<string, string>;
}
