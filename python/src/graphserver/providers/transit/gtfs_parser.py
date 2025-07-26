"""GTFS Parser

This module provides functionality to parse GTFS (General Transit Feed Specification) files
and convert them into structures suitable for transit routing.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union


@dataclass
class GTFSStop:
    """Represents a GTFS stop."""
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    location_type: int = 0
    parent_station: Optional[str] = None


@dataclass
class GTFSRoute:
    """Represents a GTFS route."""
    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int
    agency_id: Optional[str] = None


@dataclass
class GTFSTrip:
    """Represents a GTFS trip."""
    trip_id: str
    route_id: str
    service_id: str
    direction_id: Optional[int] = None
    trip_headsign: Optional[str] = None


@dataclass
class GTFSStopTime:
    """Represents a GTFS stop time."""
    trip_id: str
    stop_id: str
    arrival_time: time
    departure_time: time
    stop_sequence: int
    pickup_type: int = 0
    drop_off_type: int = 0


def parse_time(time_str: str) -> time:
    """Parse GTFS time string (HH:MM:SS) handling times >= 24:00:00."""
    if not time_str or time_str.strip() == "":
        return time(0, 0, 0)
    
    parts = time_str.strip().split(":")
    if len(parts) != 3:
        return time(0, 0, 0)
    
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        
        # Handle times >= 24:00:00 by wrapping around
        hours = hours % 24
        
        return time(hours, minutes, seconds)
    except (ValueError, IndexError):
        return time(0, 0, 0)


def time_to_seconds(t: time) -> int:
    """Convert time to seconds since midnight."""
    return t.hour * 3600 + t.minute * 60 + t.second


def seconds_to_time(seconds: int) -> time:
    """Convert seconds since midnight to time."""
    hours = (seconds // 3600) % 24
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return time(hours, minutes, secs)


class GTFSParser:
    """Parser for GTFS transit data."""
    
    def __init__(self) -> None:
        """Initialize GTFS parser."""
        self.stops: Dict[str, GTFSStop] = {}
        self.routes: Dict[str, GTFSRoute] = {}
        self.trips: Dict[str, GTFSTrip] = {}
        self.stop_times: List[GTFSStopTime] = []
        
        # Index for efficient lookups
        self.stops_by_trip: Dict[str, List[GTFSStopTime]] = {}
        self.trips_by_stop: Dict[str, List[GTFSStopTime]] = {}
    
    def parse_gtfs_directory(self, gtfs_path: Union[str, Path]) -> None:
        """Parse GTFS files from a directory.
        
        Args:
            gtfs_path: Path to directory containing GTFS files
            
        Raises:
            FileNotFoundError: If required GTFS files are missing
            ValueError: If GTFS data is invalid
        """
        gtfs_dir = Path(gtfs_path)
        
        if not gtfs_dir.is_dir():
            raise FileNotFoundError(f"GTFS directory not found: {gtfs_dir}")
        
        # Parse required files
        self._parse_stops(gtfs_dir / "stops.txt")
        self._parse_routes(gtfs_dir / "routes.txt")
        self._parse_trips(gtfs_dir / "trips.txt")
        self._parse_stop_times(gtfs_dir / "stop_times.txt")
        
        # Build indices for efficient lookup
        self._build_indices()
    
    def _parse_stops(self, stops_file: Path) -> None:
        """Parse stops.txt file."""
        if not stops_file.exists():
            raise FileNotFoundError(f"Required file not found: {stops_file}")
        
        with open(stops_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stop = GTFSStop(
                        stop_id=row['stop_id'],
                        stop_name=row.get('stop_name', ''),
                        stop_lat=float(row['stop_lat']),
                        stop_lon=float(row['stop_lon']),
                        location_type=int(row.get('location_type', 0)),
                        parent_station=row.get('parent_station')
                    )
                    self.stops[stop.stop_id] = stop
                except (KeyError, ValueError) as e:
                    # Skip invalid stops but continue parsing
                    continue
    
    def _parse_routes(self, routes_file: Path) -> None:
        """Parse routes.txt file."""
        if not routes_file.exists():
            raise FileNotFoundError(f"Required file not found: {routes_file}")
        
        with open(routes_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    route = GTFSRoute(
                        route_id=row['route_id'],
                        route_short_name=row.get('route_short_name', ''),
                        route_long_name=row.get('route_long_name', ''),
                        route_type=int(row.get('route_type', 0)),
                        agency_id=row.get('agency_id')
                    )
                    self.routes[route.route_id] = route
                except (KeyError, ValueError):
                    # Skip invalid routes but continue parsing
                    continue
    
    def _parse_trips(self, trips_file: Path) -> None:
        """Parse trips.txt file."""
        if not trips_file.exists():
            raise FileNotFoundError(f"Required file not found: {trips_file}")
        
        with open(trips_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    trip = GTFSTrip(
                        trip_id=row['trip_id'],
                        route_id=row['route_id'],
                        service_id=row['service_id'],
                        direction_id=int(row['direction_id']) if row.get('direction_id') else None,
                        trip_headsign=row.get('trip_headsign')
                    )
                    self.trips[trip.trip_id] = trip
                except (KeyError, ValueError):
                    # Skip invalid trips but continue parsing
                    continue
    
    def _parse_stop_times(self, stop_times_file: Path) -> None:
        """Parse stop_times.txt file."""
        if not stop_times_file.exists():
            raise FileNotFoundError(f"Required file not found: {stop_times_file}")
        
        with open(stop_times_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stop_time = GTFSStopTime(
                        trip_id=row['trip_id'],
                        stop_id=row['stop_id'],
                        arrival_time=parse_time(row.get('arrival_time', '')),
                        departure_time=parse_time(row.get('departure_time', '')),
                        stop_sequence=int(row.get('stop_sequence', 0)),
                        pickup_type=int(row.get('pickup_type', 0)),
                        drop_off_type=int(row.get('drop_off_type', 0))
                    )
                    self.stop_times.append(stop_time)
                except (KeyError, ValueError):
                    # Skip invalid stop times but continue parsing
                    continue
    
    def _build_indices(self) -> None:
        """Build lookup indices for efficient querying."""
        # Group stop times by trip
        for stop_time in self.stop_times:
            if stop_time.trip_id not in self.stops_by_trip:
                self.stops_by_trip[stop_time.trip_id] = []
            self.stops_by_trip[stop_time.trip_id].append(stop_time)
        
        # Sort stop times by sequence for each trip
        for trip_id in self.stops_by_trip:
            self.stops_by_trip[trip_id].sort(key=lambda st: st.stop_sequence)
        
        # Group stop times by stop
        for stop_time in self.stop_times:
            if stop_time.stop_id not in self.trips_by_stop:
                self.trips_by_stop[stop_time.stop_id] = []
            self.trips_by_stop[stop_time.stop_id].append(stop_time)
        
        # Sort stop times by departure time for each stop
        for stop_id in self.trips_by_stop:
            self.trips_by_stop[stop_id].sort(
                key=lambda st: time_to_seconds(st.departure_time)
            )
    
    def get_nearby_stops(self, lat: float, lon: float, radius_km: float = 0.5) -> List[GTFSStop]:
        """Get stops within radius of given coordinates.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_km: Search radius in kilometers
            
        Returns:
            List of nearby stops sorted by distance
        """
        nearby_stops = []
        
        for stop in self.stops.values():
            distance = self._calculate_distance(lat, lon, stop.stop_lat, stop.stop_lon)
            if distance <= radius_km:
                nearby_stops.append((stop, distance))
        
        # Sort by distance
        nearby_stops.sort(key=lambda x: x[1])
        return [stop for stop, _ in nearby_stops]
    
    def get_departures_from_stop(
        self, 
        stop_id: str, 
        current_time_seconds: int, 
        next_hours: int = 2
    ) -> List[GTFSStopTime]:
        """Get departures from a stop within the next X hours.
        
        Args:
            stop_id: Stop ID to get departures from
            current_time_seconds: Current time in seconds since midnight
            next_hours: Number of hours to look ahead
            
        Returns:
            List of departures sorted by departure time
        """
        if stop_id not in self.trips_by_stop:
            return []
        
        end_time_seconds = current_time_seconds + (next_hours * 3600)
        departures = []
        
        for stop_time in self.trips_by_stop[stop_id]:
            departure_seconds = time_to_seconds(stop_time.departure_time)
            
            # Handle departures that span midnight
            if departure_seconds >= current_time_seconds and departure_seconds <= end_time_seconds:
                departures.append(stop_time)
            elif departure_seconds < current_time_seconds and end_time_seconds > 86400:
                # Check if departure is in the next day
                next_day_departure = departure_seconds + 86400
                if next_day_departure <= end_time_seconds:
                    departures.append(stop_time)
        
        return departures
    
    def get_next_stop_in_trip(
        self, 
        trip_id: str, 
        current_stop_sequence: int
    ) -> Optional[GTFSStopTime]:
        """Get the next stop in a trip sequence.
        
        Args:
            trip_id: Trip ID
            current_stop_sequence: Current stop sequence number
            
        Returns:
            Next stop time in the trip, or None if this is the last stop
        """
        if trip_id not in self.stops_by_trip:
            return None
        
        trip_stops = self.stops_by_trip[trip_id]
        
        for stop_time in trip_stops:
            if stop_time.stop_sequence > current_stop_sequence:
                return stop_time
        
        return None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        import math
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        earth_radius_km = 6371.0
        
        return earth_radius_km * c