"""Spatial indexing for transit stops."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .types import Stop

import rtree.index

logger = logging.getLogger(__name__)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points in meters.

    Uses the haversine formula.

    Args:
        lat1, lon1: First point coordinates in degrees
        lat2, lon2: Second point coordinates in degrees

    Returns:
        Distance in meters
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in meters
    earth_radius_m = 6371000

    return earth_radius_m * c


def degrees_to_meters(degrees: float, latitude: float) -> float:
    """Convert degrees to meters at a given latitude.

    Args:
        degrees: Degrees to convert
        latitude: Latitude in degrees

    Returns:
        Distance in meters
    """
    # One degree of latitude is approximately 111,111 meters
    lat_meters = degrees * 111111.0

    # One degree of longitude varies by latitude
    lon_meters = degrees * 111111.0 * math.cos(math.radians(latitude))

    return max(lat_meters, lon_meters)


def meters_to_degrees(meters: float, latitude: float) -> float:
    """Convert meters to degrees at a given latitude.

    Args:
        meters: Meters to convert
        latitude: Latitude in degrees

    Returns:
        Distance in degrees
    """
    # One degree of latitude is approximately 111,111 meters
    lat_degrees = meters / 111111.0

    # One degree of longitude varies by latitude
    lon_degrees = meters / (111111.0 * math.cos(math.radians(latitude)))

    return max(lat_degrees, lon_degrees)


class SpatialIndex:
    """Spatial index for efficient stop lookups using R-tree."""

    def __init__(self) -> None:
        """Initialize spatial index."""
        self.index = rtree.index.Index()
        self.stops: dict[int, Stop] = {}
        self._next_id = 0

    def add_stops(self, stops: dict[str, Stop]) -> None:
        """Add stops to the spatial index.

        Args:
            stops: Dictionary of stop_id -> Stop objects
        """
        logger.info("Building spatial index for %d stops", len(stops))

        for stop in stops.values():
            # Use internal ID for rtree
            internal_id = self._next_id
            self._next_id += 1

            # Store stop with internal ID
            self.stops[internal_id] = stop

            # Add to spatial index (left, bottom, right, top)
            self.index.insert(internal_id, (stop.lon, stop.lat, stop.lon, stop.lat))

    def find_nearest_stops(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        max_results: int = 10,
    ) -> Sequence[tuple[Stop, float]]:
        """Find nearby stops within radius.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters
            max_results: Maximum number of results

        Returns:
            List of (stop, distance_m) tuples sorted by distance
        """
        # Convert radius to degrees (approximate)
        radius_deg = meters_to_degrees(radius_m, lat)

        # Search bounding box
        left = lon - radius_deg
        bottom = lat - radius_deg
        right = lon + radius_deg
        top = lat + radius_deg

        # Find candidates
        candidate_ids = list(self.index.intersection((left, bottom, right, top)))

        # Calculate exact distances and filter
        results = []
        for internal_id in candidate_ids:
            if internal_id not in self.stops:
                continue

            stop = self.stops[internal_id]
            distance = calculate_distance(lat, lon, stop.lat, stop.lon)

            if distance <= radius_m:
                results.append((stop, distance))

        # Sort by distance and limit results
        results.sort(key=lambda x: x[1])
        return results[:max_results]

    def find_nearest_stop(
        self,
        lat: float,
        lon: float,
        radius_m: float,
    ) -> Stop | None:
        """Find the nearest stop within radius.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters

        Returns:
            Nearest stop or None if no stop found
        """
        results = self.find_nearest_stops(lat, lon, radius_m, max_results=1)
        return results[0][0] if results else None
