"""Pydantic models describing the JSON returned by the API (they also document /docs)."""

from typing import Literal

# How "fresh" a piece of data is. Shown in the UI so we never pass off schedules as live data.
DataStatus = Literal["scheduled", "realtime", "model", "static"]
