// Minimal stroke icons (24×24, drawn in the style of Feather icons) to avoid an icon dependency.

const PATHS: Record<string, string[]> = {
  layers: ["M12 2 2 7l10 5 10-5-10-5z", "M2 17l10 5 10-5", "M2 12l10 5 10-5"],
  info: ["M12 16v-4", "M12 8h.01", "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z"],
  close: ["M18 6 6 18", "M6 6l12 12"],
  search: ["M21 21l-4.35-4.35", "M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0z"],
  refresh: ["M23 4v6h-6", "M20.49 15a9 9 0 1 1-2.12-9.36L23 10"],
  home: ["M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z", "M9 22V12h6v10"],
  wheelchair: ["M12 4h.01", "M10 8h3l1 5h4", "M9 11a5 5 0 1 0 6 6"],
  wind: ["M9.59 4.59A2 2 0 1 1 11 8H2", "M12.59 19.41A2 2 0 1 0 14 16H2", "M17.73 7.73A2.5 2.5 0 1 1 19.5 12H2"],
  droplet: ["M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"],
  alert: ["M12 9v4", "M12 17h.01", "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"],
  // weather
  clear: ["M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z", "M12 1v2", "M12 21v2", "M4.22 4.22l1.42 1.42",
    "M18.36 18.36l1.42 1.42", "M1 12h2", "M21 12h2", "M4.22 19.78l1.42-1.42", "M18.36 5.64l1.42-1.42"],
  moon: ["M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"],
  cloudy: ["M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"],
  "partly-cloudy": ["M8 2v1.5", "M3.5 6.5 4.6 7.6", "M2 11h1.5", "M12.5 6.5l-1.1 1.1",
    "M5.2 13.4A4 4 0 1 1 11.4 8", "M19 14h-1a6 6 0 1 0-6 7h7a3.5 3.5 0 0 0 0-7z"],
  fog: ["M3 10h18", "M5 14h14", "M3 18h18", "M6 6h12"],
  drizzle: ["M8 19v2", "M8 13v2", "M16 19v2", "M16 13v2", "M12 21v2", "M12 15v2",
    "M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"],
  rain: ["M16 13v8", "M8 13v8", "M12 15v8", "M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"],
  snow: ["M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25", "M8 16h.01", "M8 20h.01",
    "M12 18h.01", "M12 22h.01", "M16 16h.01", "M16 20h.01"],
  thunderstorm: ["M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9", "M13 11l-4 6h6l-4 6"],
  unknown: ["M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"],
};

interface IconProps {
  name: string;
  size?: number;
  strokeWidth?: number;
  className?: string;
  title?: string;
}

export function Icon({ name, size = 18, strokeWidth = 2, className, title }: IconProps) {
  const paths = PATHS[name] ?? PATHS.unknown;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {paths.map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

/** Weather icon, using a moon for clear nights. */
export function weatherIconName(icon: string, isDay: boolean | null): string {
  if (icon === "clear" && isDay === false) return "moon";
  return icon in PATHS ? icon : "unknown";
}
