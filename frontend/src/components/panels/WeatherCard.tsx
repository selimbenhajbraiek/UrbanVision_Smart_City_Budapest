import { useState } from "react";
import type { AirQualityResponse, WeatherResponse } from "../../api/types";
import type { ApiState } from "../../hooks/useApi";
import { aqiColor, formatClock, formatLocalHour, round } from "../../utils/format";
import { DataStatusBadge } from "../common/Badges";
import { Icon, weatherIconName } from "../common/Icon";

interface Props {
  weather: ApiState<WeatherResponse> | null;
  airQuality: ApiState<AirQualityResponse> | null;
}

export function WeatherCard({ weather, airQuality }: Props) {
  // Start collapsed on phones so the card does not cover the map.
  const [expanded, setExpanded] = useState(() => window.innerWidth > 900);
  const current = weather?.data?.current;

  return (
    <section className={`weather-card ${expanded ? "" : "collapsed"}`} aria-label="Weather in Budapest">
      <button
        type="button"
        className="weather-summary"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {current ? (
          <>
            <Icon name={weatherIconName(current.icon, current.is_day)} size={34} strokeWidth={1.6} />
            <div className="weather-main">
              <span className="temperature">{Math.round(current.temperature_c)}°C</span>
              <span className="condition">{current.condition}</span>
            </div>
          </>
        ) : (
          <div className="weather-main">
            <span className="condition">{weather?.error ?? "Budapest weather"}</span>
          </div>
        )}
        {airQuality?.data && !expanded && (
          <span className="aqi-pill" style={{ background: aqiColor(airQuality.data.current.european_aqi) }}>
            AQI {round(airQuality.data.current.european_aqi)}
          </span>
        )}
      </button>

      {expanded && (
        <div className="weather-details">
          {weather && current && weather.data && (
            <>
              <div className="weather-header">
                <strong>{weather.data.location.name}</strong>
                <DataStatusBadge status="model" />
              </div>
              <dl className="weather-grid">
                <div>
                  <dt>Feels like</dt>
                  <dd>{round(current.apparent_temperature_c)}°C</dd>
                </div>
                <div>
                  <dt>
                    <Icon name="wind" size={12} /> Wind
                  </dt>
                  <dd>
                    {round(current.wind_speed_kmh)} km/h {current.wind_direction ?? ""}
                  </dd>
                </div>
                <div>
                  <dt>
                    <Icon name="droplet" size={12} /> Precipitation
                  </dt>
                  <dd>{round(current.precipitation_mm, 1)} mm</dd>
                </div>
                <div>
                  <dt>Humidity</dt>
                  <dd>{round(current.humidity_percent)}%</dd>
                </div>
              </dl>
              <ol className="hourly">
                {weather.data.hourly.slice(1, 7).map((hour) => (
                  <li key={hour.time}>
                    <span>{formatLocalHour(hour.time)}</span>
                    <Icon name={weatherIconName(hour.icon ?? "unknown", hour.is_day)} size={18} strokeWidth={1.6} />
                    <strong>{round(hour.temperature_c)}°</strong>
                    <span className="muted">{round(hour.precipitation_probability_percent)}%</span>
                  </li>
                ))}
              </ol>
            </>
          )}

          {airQuality?.data && <AirQualitySection data={airQuality.data} />}
          {airQuality?.error && <p className="muted small">Air quality: {airQuality.error}</p>}

          {weather?.data && (
            <p className="footnote">
              {weather.data.attribution}. Model data for {formatLocalHour(current!.time)}, fetched{" "}
              {formatClock(weather.data.fetched_at)}.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function AirQualitySection({ data }: { data: AirQualityResponse }) {
  const aq = data.current;
  return (
    <div className="air-quality">
      <div className="weather-header">
        <strong>Air quality</strong>
        <span className="aqi-pill" style={{ background: aqiColor(aq.european_aqi) }}>
          {round(aq.european_aqi)} · {aq.european_aqi_label ?? "n/a"}
        </span>
      </div>
      <dl className="weather-grid">
        <div>
          <dt>PM2.5</dt>
          <dd>{round(aq.pm2_5_ugm3, 1)} µg/m³</dd>
        </div>
        <div>
          <dt>PM10</dt>
          <dd>{round(aq.pm10_ugm3, 1)} µg/m³</dd>
        </div>
        <div>
          <dt>NO₂</dt>
          <dd>{round(aq.nitrogen_dioxide_ugm3, 1)} µg/m³</dd>
        </div>
        <div>
          <dt>O₃</dt>
          <dd>{round(aq.ozone_ugm3, 1)} µg/m³</dd>
        </div>
      </dl>
      <p className="footnote">European AQI · CAMS model forecast via Open-Meteo (not a sensor reading).</p>
    </div>
  );
}
