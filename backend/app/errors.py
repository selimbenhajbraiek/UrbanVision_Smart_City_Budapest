"""Domain errors, translated to HTTP responses in `app.main`."""


class UpstreamServiceError(Exception):
    """An external data source (Open-Meteo, BKK) failed or returned invalid data."""


class FeatureNotConfiguredError(Exception):
    """An optional feature (e.g. real-time data) is not configured on this server."""
