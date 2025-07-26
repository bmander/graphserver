"""Transit Edge Provider

This module provides the main TransitProvider class that implements the EdgeProvider
protocol for GTFS-based transit pathfinding.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from graphserver.core import Edge, Vertex, VertexEdgePair

from .gtfs_parser import GTFSParser
from .spatial import SpatialIndex
from .types import TransitConfig

logger = logging.getLogger(__name__)


class TransitProvider:
    """Transit edge provider for GTFS-based pathfinding.

    This provider supports several types of vertex inputs:
    1. Geographic coordinates with time: {"lat": float, "lon": float, "time": int}
    2. Stop with time: {"stop_id": str, "time": int}
    3. Boarding vertex: {
        "time": int, "trip_id": str, "stop_sequence": int,
        "vehicle_state": "boarding"
    }
    4. Alright vertex: {
        "time": int, "trip_id": str, "stop_sequence": int,
        "vehicle_state": "alright"
    }

    Edge expansion specification:
    - [lat/lon/time] -> nearby stops with arrival time
    - [stop_id/time] -> boarding vertices for departures
    - [boarding vertex] -> alright vertex at next stop
    - [alright vertex] -> boarding vertex at same stop + stop vertex at same stop
    """

    def __init__(
        self,
        gtfs_file: str | Path,
        *,
        config: TransitConfig | None = None,
        build_index: bool = True,
    ) -> None:
        """Initialize transit provider from a GTFS file.

        Args:
            gtfs_file: Path to GTFS zip file or directory
            config: Transit configuration options
            build_index: Whether to build spatial index (recommended for performance)

        Raises:
            FileNotFoundError: If GTFS file doesn't exist
            RuntimeError: If parsing fails
        """
        self.gtfs_file = Path(gtfs_file)
        self.config = config or TransitConfig()

        # Parse GTFS data
        logger.info("Initializing transit provider from %s", self.gtfs_file)
        self.parser = GTFSParser(self.gtfs_file)

        # Build spatial index for efficient coordinate-based queries
        self.spatial_index: SpatialIndex | None = None
        if build_index:
            self._build_spatial_index()

        logger.info(
            "Transit provider ready: %d stops, %d routes, %d trips",
            self.parser.stop_count,
            self.parser.route_count,
            self.parser.trip_count,
        )

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for transit stops")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_stops(self.parser.stops)

    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a vertex (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing location/time or transit state

        Returns:
            List of (target_vertex, edge) tuples
        """
        # Check vehicle state vertices first (these also have stop_id/time)
        # Check if vertex is a boarding vertex
        if (
            "time" in vertex
            and "trip_id" in vertex
            and "stop_sequence" in vertex
            and vertex.get("vehicle_state") == "boarding"
        ):
            return self._edges_from_boarding(vertex)

        # Check if vertex is an alright vertex
        if (
            "time" in vertex
            and "trip_id" in vertex
            and "stop_sequence" in vertex
            and vertex.get("vehicle_state") == "alright"
        ):
            return self._edges_from_alright(vertex)

        # Check if vertex contains geographic coordinates with time
        if "lat" in vertex and "lon" in vertex and "time" in vertex:
            return self._edges_from_coordinates(vertex)

        # Check if vertex contains stop ID with time (but no vehicle state)
        if "stop_id" in vertex and "time" in vertex and "vehicle_state" not in vertex:
            return self._edges_from_stop(vertex)

        # Unknown vertex type - return empty edges
        logger.warning("Unknown vertex type: %s", vertex)
        return []

    def _edges_from_coordinates(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from geographic coordinates with time.

        Args:
            vertex: Vertex containing "lat", "lon", and "time" keys

        Returns:
            List of edges to nearby transit stops
        """
        lat = float(vertex["lat"])
        lon = float(vertex["lon"])
        time = int(vertex["time"])

        # Find nearby stops
        if self.spatial_index is not None:
            # Use spatial index for efficient lookup
            nearby_results = self.spatial_index.find_nearest_stops(
                lat, lon, self.config.search_radius_m, self.config.max_nearby_stops
            )
            nearby_stops = [stop for stop, _ in nearby_results]
        else:
            # Fallback to checking all stops (slower)
            from .spatial import calculate_distance

            nearby_stops = []
            for stop in self.parser.stops.values():
                distance = calculate_distance(lat, lon, stop.lat, stop.lon)
                if distance <= self.config.search_radius_m:
                    nearby_stops.append(stop)
            nearby_stops = nearby_stops[: self.config.max_nearby_stops]

        # Generate edges to nearby stops
        edges = []
        for stop in nearby_stops:
            # Calculate walking time to stop
            from .spatial import calculate_distance

            distance_m = calculate_distance(lat, lon, stop.lat, stop.lon)
            walking_time_s = distance_m / self.config.walking_speed_ms
            arrival_time = time + int(walking_time_s)

            # Create target vertex - stop with arrival time
            target_vertex = Vertex(
                {
                    "stop_id": stop.stop_id,
                    "time": arrival_time,
                    "lat": stop.lat,
                    "lon": stop.lon,
                    "stop_name": stop.stop_name,
                }
            )

            # Create edge with walking time as cost
            edge = Edge(
                cost=walking_time_s,
                metadata={
                    "edge_type": "walk_to_stop",
                    "distance_m": distance_m,
                    "walking_time_s": walking_time_s,
                    "stop_id": stop.stop_id,
                },
            )

            edges.append((target_vertex, edge))

        return edges

    def _edges_from_stop(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from stop with time.

        Args:
            vertex: Vertex containing "stop_id" and "time" keys

        Returns:
            List of edges to boarding vertices for departures
        """
        stop_id = str(vertex["stop_id"])
        time = int(vertex["time"])

        # Get departures from this stop
        departures = self.parser.get_departures_from_stop(
            stop_id, time, self.config.max_departure_hours
        )

        edges = []
        for departure in departures:
            # Only consider departures after current time
            if departure.departure_time < time:
                continue

            # Create boarding vertex
            target_vertex = Vertex(
                {
                    "time": departure.departure_time,
                    "trip_id": departure.trip_id,
                    "stop_sequence": departure.stop_sequence,
                    "vehicle_state": "boarding",
                    "stop_id": departure.stop_id,
                    "route_id": departure.route_id,
                }
            )

            # Cost is waiting time until departure
            waiting_time = departure.departure_time - time
            edge = Edge(
                cost=waiting_time,
                metadata={
                    "edge_type": "wait_for_departure",
                    "waiting_time_s": waiting_time,
                    "trip_id": departure.trip_id,
                    "route_id": departure.route_id,
                    "departure_time": departure.departure_time,
                },
            )

            edges.append((target_vertex, edge))

        return edges

    def _edges_from_boarding(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from boarding vertex.

        Args:
            vertex: Boarding vertex

        Returns:
            List of edges to alright vertex at next stop
        """
        trip_id = str(vertex["trip_id"])
        stop_sequence = int(vertex["stop_sequence"])
        boarding_time = int(vertex["time"])

        # Get next stop in trip
        next_stop_time = self.parser.get_next_stop_in_trip(trip_id, stop_sequence)
        if next_stop_time is None:
            return []  # End of trip

        # Get service date for time conversion
        from datetime import datetime

        boarding_datetime = datetime.fromtimestamp(boarding_time)
        service_date = int(
            boarding_datetime.replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp()
        )

        # Convert GTFS time to timestamp
        from .types import gtfs_time_to_timestamp

        arrival_time = gtfs_time_to_timestamp(next_stop_time.arrival_time, service_date)

        # Create alright vertex at next stop
        target_vertex = Vertex(
            {
                "time": arrival_time,
                "trip_id": trip_id,
                "stop_sequence": next_stop_time.stop_sequence,
                "vehicle_state": "alright",
                "stop_id": next_stop_time.stop_id,
                "route_id": vertex.get("route_id", ""),
            }
        )

        # Cost is travel time
        travel_time = arrival_time - boarding_time
        edge = Edge(
            cost=travel_time,
            metadata={
                "edge_type": "in_vehicle_travel",
                "travel_time_s": travel_time,
                "trip_id": trip_id,
                "from_stop_sequence": stop_sequence,
                "to_stop_sequence": next_stop_time.stop_sequence,
                "to_stop_id": next_stop_time.stop_id,
            },
        )

        return [(target_vertex, edge)]

    def _edges_from_alright(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from alright vertex.

        Args:
            vertex: Alright vertex

        Returns:
            List of edges to boarding vertex at same stop and stop vertex
        """
        trip_id = str(vertex["trip_id"])
        stop_sequence = int(vertex["stop_sequence"])
        arrival_time = int(vertex["time"])
        stop_id = str(vertex["stop_id"])

        edges = []

        # Edge 1: To boarding vertex at same stop (for continuing on vehicle)
        boarding_vertex = Vertex(
            {
                "time": arrival_time,
                "trip_id": trip_id,
                "stop_sequence": stop_sequence,
                "vehicle_state": "boarding",
                "stop_id": stop_id,
                "route_id": vertex.get("route_id", ""),
            }
        )

        boarding_edge = Edge(
            cost=0,  # No cost to change state
            metadata={
                "edge_type": "alright_to_boarding",
                "trip_id": trip_id,
                "stop_id": stop_id,
            },
        )

        edges.append((boarding_vertex, boarding_edge))

        # Edge 2: To stop vertex (for alighting)
        if stop_id in self.parser.stops:
            stop = self.parser.stops[stop_id]
            stop_vertex = Vertex(
                {
                    "stop_id": stop_id,
                    "time": arrival_time,
                    "lat": stop.lat,
                    "lon": stop.lon,
                    "stop_name": stop.stop_name,
                }
            )

            alighting_edge = Edge(
                cost=0,  # No cost to alight
                metadata={
                    "edge_type": "alight_at_stop",
                    "trip_id": trip_id,
                    "stop_id": stop_id,
                },
            )

            edges.append((stop_vertex, alighting_edge))

        return edges

    @property
    def stop_count(self) -> int:
        """Get number of transit stops."""
        return self.parser.stop_count

    @property
    def route_count(self) -> int:
        """Get number of transit routes."""
        return self.parser.route_count

    @property
    def trip_count(self) -> int:
        """Get number of transit trips."""
        return self.parser.trip_count
