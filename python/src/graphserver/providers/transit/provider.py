"""Transit Edge Provider

This module provides the main TransitProvider class that implements the EdgeProvider
protocol for GTFS-based transit pathfinding.
"""

from __future__ import annotations

import logging
from datetime import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from graphserver.core import Edge, Vertex, VertexEdgePair

from .gtfs_parser import GTFSParser, time_to_seconds

logger = logging.getLogger(__name__)


class TransitProvider:
    """Transit edge provider for GTFS-based public transit pathfinding.
    
    This provider supports multiple types of vertex inputs:
    1. Geographic coordinates with time: {"lat": float, "lon": float, "time": int}
    2. Stop references: {"stop_id": str}
    3. Boarding vertices: {"time": int, "trip_id": str, "stop_sequence": int, "vehicle_state": "boarding"}
    4. Alright vertices: {"time": int, "trip_id": str, "stop_sequence": int, "vehicle_state": "alright"}
    
    Edge expansion follows the specification:
    - [lat/lon/time] -> nearby stops with stop_id and arrival time
    - [stop_id] -> boarding vertices for departures in next X hours
    - [boarding vertex] -> alright vertex at next stop on trip
    - [alright vertex] -> boarding vertex at same stop + stop vertex at same stop
    """
    
    def __init__(
        self,
        gtfs_path: str | Path,
        *,
        search_radius_km: float = 0.5,
        departure_window_hours: int = 2,
        walking_speed_ms: float = 1.2,  # meters per second
        max_nearby_stops: int = 10,
    ) -> None:
        """Initialize transit provider from GTFS data.
        
        Args:
            gtfs_path: Path to GTFS directory containing transit data files
            search_radius_km: Search radius for finding nearby stops from coordinates
            departure_window_hours: Hours to look ahead for departures from a stop
            walking_speed_ms: Walking speed for coordinate-to-stop connections
            max_nearby_stops: Maximum number of nearby stops to consider
            
        Raises:
            FileNotFoundError: If GTFS directory or files don't exist
            ValueError: If GTFS data is invalid
        """
        self.gtfs_path = Path(gtfs_path)
        self.search_radius_km = search_radius_km
        self.departure_window_hours = departure_window_hours
        self.walking_speed_ms = walking_speed_ms
        self.max_nearby_stops = max_nearby_stops
        
        # Parse GTFS data
        logger.info("Initializing transit provider from %s", self.gtfs_path)
        self.parser = GTFSParser()
        self.parser.parse_gtfs_directory(self.gtfs_path)
        
        logger.info(
            "Transit provider ready: %d stops, %d routes, %d trips, %d stop times",
            len(self.parser.stops),
            len(self.parser.routes),
            len(self.parser.trips),
            len(self.parser.stop_times),
        )
    
    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a vertex (implements EdgeProvider protocol).
        
        Args:
            vertex: Input vertex containing location, stop, or vehicle state data
            
        Returns:
            List of (target_vertex, edge) tuples
        """
        # Check vertex type and route to appropriate handler
        if "lat" in vertex and "lon" in vertex and "time" in vertex:
            return self._edges_from_coordinates(vertex)
        elif "stop_id" in vertex:
            return self._edges_from_stop(vertex)
        elif ("vehicle_state" in vertex and 
              vertex.get("vehicle_state") == "boarding" and
              "trip_id" in vertex and "stop_sequence" in vertex and "time" in vertex):
            return self._edges_from_boarding_vertex(vertex)
        elif ("vehicle_state" in vertex and 
              vertex.get("vehicle_state") == "alright" and
              "trip_id" in vertex and "stop_sequence" in vertex and "time" in vertex):
            return self._edges_from_alright_vertex(vertex)
        
        # Unknown vertex type - return empty edges
        logger.warning("Unknown vertex type: %s", vertex)
        return []
    
    def _edges_from_coordinates(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from geographic coordinates with time.
        
        For every nearby stop, creates a vertex with stop_id and time at arrival.
        
        Args:
            vertex: Vertex containing "lat", "lon", and "time" keys
            
        Returns:
            List of edges to nearby stop vertices
        """
        lat = float(vertex["lat"])
        lon = float(vertex["lon"])
        current_time = int(vertex["time"])  # seconds since midnight
        
        # Find nearby stops
        nearby_stops = self.parser.get_nearby_stops(
            lat, lon, self.search_radius_km
        )
        nearby_stops = nearby_stops[:self.max_nearby_stops]
        
        edges = []
        for stop in nearby_stops:
            # Calculate walking distance and time
            distance_m = self.parser._calculate_distance(
                lat, lon, stop.stop_lat, stop.stop_lon
            ) * 1000  # Convert km to meters
            
            walking_time_s = distance_m / self.walking_speed_ms
            arrival_time = current_time + int(walking_time_s)
            
            # Create target vertex with stop information and arrival time
            target_vertex = Vertex({
                "stop_id": stop.stop_id,
                "stop_name": stop.stop_name,
                "lat": stop.stop_lat,
                "lon": stop.stop_lon,
                "time": arrival_time,
            })
            
            # Create edge with walking cost
            edge = Edge(
                cost=walking_time_s,
                metadata={
                    "edge_type": "coordinate_to_stop",
                    "distance_m": distance_m,
                    "walking_time_s": walking_time_s,
                    "stop_id": stop.stop_id,
                    "stop_name": stop.stop_name,
                },
            )
            
            edges.append((target_vertex, edge))
        
        return edges
    
    def _edges_from_stop(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from stop vertex to boarding vertices.
        
        For every vehicle departure in the next X hours, creates a boarding vertex.
        
        Args:
            vertex: Vertex containing "stop_id" key
            
        Returns:
            List of edges to boarding vertices
        """
        stop_id = str(vertex["stop_id"])
        
        # Use current time from vertex if available, otherwise use current system time
        if "time" in vertex:
            current_time_seconds = int(vertex["time"])
        else:
            # If no time specified, assume start of day for basic functionality
            current_time_seconds = 0
        
        # Get departures from this stop
        departures = self.parser.get_departures_from_stop(
            stop_id, current_time_seconds, self.departure_window_hours
        )
        
        edges = []
        for departure in departures:
            departure_time_seconds = time_to_seconds(departure.departure_time)
            
            # Calculate waiting time
            if departure_time_seconds >= current_time_seconds:
                waiting_time = departure_time_seconds - current_time_seconds
            else:
                # Handle next-day departures
                waiting_time = (departure_time_seconds + 86400) - current_time_seconds
            
            # Create boarding vertex
            target_vertex = Vertex({
                "time": departure_time_seconds,
                "trip_id": departure.trip_id,
                "stop_sequence": departure.stop_sequence,
                "vehicle_state": "boarding",
                "stop_id": departure.stop_id,
                "route_id": self.parser.trips.get(departure.trip_id, {}).route_id if departure.trip_id in self.parser.trips else None,
            })
            
            # Create edge with waiting cost
            edge = Edge(
                cost=waiting_time,
                metadata={
                    "edge_type": "stop_to_boarding",
                    "waiting_time_s": waiting_time,
                    "trip_id": departure.trip_id,
                    "route_id": self.parser.trips.get(departure.trip_id).route_id if departure.trip_id in self.parser.trips else None,
                    "departure_time": str(departure.departure_time),
                },
            )
            
            edges.append((target_vertex, edge))
        
        return edges
    
    def _edges_from_boarding_vertex(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from boarding vertex to alright vertex at next stop.
        
        Args:
            vertex: Boarding vertex with trip and stop sequence information
            
        Returns:
            List containing edge to alright vertex at next stop
        """
        trip_id = str(vertex["trip_id"])
        current_stop_sequence = int(vertex["stop_sequence"])
        current_time = int(vertex["time"])
        
        # Get next stop in trip
        next_stop_time = self.parser.get_next_stop_in_trip(trip_id, current_stop_sequence)
        
        if next_stop_time is None:
            # No next stop - end of trip
            return []
        
        arrival_time_seconds = time_to_seconds(next_stop_time.arrival_time)
        travel_time = arrival_time_seconds - current_time
        
        # Handle travel across midnight
        if travel_time < 0:
            travel_time += 86400
        
        # Create alright vertex at next stop
        target_vertex = Vertex({
            "time": arrival_time_seconds,
            "trip_id": trip_id,
            "stop_sequence": next_stop_time.stop_sequence,
            "vehicle_state": "alright",
            "stop_id": next_stop_time.stop_id,
            "route_id": self.parser.trips.get(trip_id).route_id if trip_id in self.parser.trips else None,
        })
        
        # Create edge with travel cost
        edge = Edge(
            cost=travel_time,
            metadata={
                "edge_type": "boarding_to_alright",
                "travel_time_s": travel_time,
                "trip_id": trip_id,
                "route_id": self.parser.trips.get(trip_id).route_id if trip_id in self.parser.trips else None,
                "from_stop_id": vertex.get("stop_id"),
                "to_stop_id": next_stop_time.stop_id,
                "arrival_time": str(next_stop_time.arrival_time),
            },
        )
        
        return [(target_vertex, edge)]
    
    def _edges_from_alright_vertex(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from alright vertex to boarding vertex and stop vertex.
        
        Args:
            vertex: Alright vertex with trip and stop information
            
        Returns:
            List containing edges to boarding vertex at same stop and stop vertex
        """
        stop_id = str(vertex["stop_id"])
        current_time = int(vertex["time"])
        
        edges = []
        
        # Edge 1: To boarding vertex at same stop (for transfers)
        boarding_vertex = Vertex({
            "stop_id": stop_id,
            "time": current_time,
        })
        
        # No cost for immediate transfer opportunity
        boarding_edge = Edge(
            cost=0.0,
            metadata={
                "edge_type": "alright_to_boarding",
                "stop_id": stop_id,
                "transfer_time_s": 0,
            },
        )
        
        edges.append((boarding_vertex, boarding_edge))
        
        # Edge 2: To stop vertex at same stop (for ending journey or walking transfers)
        if stop_id in self.parser.stops:
            stop = self.parser.stops[stop_id]
            stop_vertex = Vertex({
                "stop_id": stop_id,
                "stop_name": stop.stop_name,
                "lat": stop.stop_lat,
                "lon": stop.stop_lon,
                "time": current_time,
            })
            
            # No cost for alighting
            stop_edge = Edge(
                cost=0.0,
                metadata={
                    "edge_type": "alright_to_stop",
                    "stop_id": stop_id,
                    "stop_name": stop.stop_name,
                },
            )
            
            edges.append((stop_vertex, stop_edge))
        
        return edges
    
    @property
    def stop_count(self) -> int:
        """Get number of stops in the transit network."""
        return len(self.parser.stops)
    
    @property
    def route_count(self) -> int:
        """Get number of routes in the transit network."""
        return len(self.parser.routes)
    
    @property
    def trip_count(self) -> int:
        """Get number of trips in the transit network."""
        return len(self.parser.trips)
    
    def get_stop_by_id(self, stop_id: str) -> Vertex | None:
        """Get a vertex representation of a stop by ID.
        
        Args:
            stop_id: GTFS stop ID
            
        Returns:
            Vertex object or None if stop not found
        """
        if stop_id not in self.parser.stops:
            return None
        
        stop = self.parser.stops[stop_id]
        return Vertex({
            "stop_id": stop.stop_id,
            "stop_name": stop.stop_name,
            "lat": stop.stop_lat,
            "lon": stop.stop_lon,
        })
    
    def find_nearest_stop(self, lat: float, lon: float) -> Vertex | None:
        """Find the nearest stop to given coordinates.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            
        Returns:
            Vertex for nearest stop or None if no stop found
        """
        nearby_stops = self.parser.get_nearby_stops(lat, lon, self.search_radius_km)
        
        if not nearby_stops:
            return None
        
        nearest_stop = nearby_stops[0]
        return Vertex({
            "stop_id": nearest_stop.stop_id,
            "stop_name": nearest_stop.stop_name,
            "lat": nearest_stop.stop_lat,
            "lon": nearest_stop.stop_lon,
        })