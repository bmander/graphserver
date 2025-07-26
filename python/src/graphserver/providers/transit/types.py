"""Transit provider types and data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stop:
    """Represents a transit stop from GTFS data."""

    stop_id: str
    stop_name: str
    lat: float
    lon: float
    location_type: int = 0
    parent_station: str | None = None
    stop_timezone: str | None = None


@dataclass(frozen=True)
class Route:
    """Represents a transit route from GTFS data."""

    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int
    agency_id: str | None = None


@dataclass(frozen=True)
class Trip:
    """Represents a transit trip from GTFS data."""

    trip_id: str
    route_id: str
    service_id: str
    trip_headsign: str | None = None
    direction_id: int | None = None
    shape_id: str | None = None


@dataclass(frozen=True)
class StopTime:
    """Represents a stop time from GTFS data."""

    trip_id: str
    stop_id: str
    stop_sequence: int
    arrival_time: str  # HH:MM:SS format
    departure_time: str  # HH:MM:SS format
    pickup_type: int = 0
    drop_off_type: int = 0


@dataclass(frozen=True)
class Departure:
    """Represents a scheduled departure from a stop."""

    trip_id: str
    route_id: str
    stop_id: str
    stop_sequence: int
    departure_time: int  # Unix timestamp
    arrival_time: int    # Unix timestamp (at this stop)
    next_stop_id: str | None = None
    next_stop_sequence: int | None = None
    next_arrival_time: int | None = None


class TransitConfig:
    """Configuration for transit provider."""

    def __init__(
        self,
        *,
        search_radius_m: float = 500.0,
        max_nearby_stops: int = 10,
        max_departure_hours: int = 24,
        walking_speed_ms: float = 1.4,  # meters per second
        max_transfer_walk_time: int = 300,  # seconds
    ) -> None:
        """Initialize transit configuration.

        Args:
            search_radius_m: Search radius for finding nearby stops from coordinates
            max_nearby_stops: Maximum number of nearby stops to consider
            max_departure_hours: Maximum hours in future to look for departures
            walking_speed_ms: Walking speed in meters per second
            max_transfer_walk_time: Maximum walking time for transfers in seconds
        """
        self.search_radius_m = search_radius_m
        self.max_nearby_stops = max_nearby_stops
        self.max_departure_hours = max_departure_hours
        self.walking_speed_ms = walking_speed_ms
        self.max_transfer_walk_time = max_transfer_walk_time


def parse_gtfs_time(time_str: str) -> int:
    """Parse GTFS time string (HH:MM:SS) to seconds since midnight.

    Args:
        time_str: Time string in HH:MM:SS format

    Returns:
        Seconds since midnight
    """
    try:
        hours, minutes, seconds = map(int, time_str.split(":"))
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, AttributeError):
        return 0


def gtfs_time_to_timestamp(time_str: str, service_date: int) -> int:
    """Convert GTFS time to Unix timestamp.

    Args:
        time_str: Time string in HH:MM:SS format
        service_date: Service date as Unix timestamp (midnight)

    Returns:
        Unix timestamp
    """
    seconds_since_midnight = parse_gtfs_time(time_str)
    return service_date + seconds_since_midnight
