"""Tests for Transit Edge Provider

This module tests the GTFS-based transit edge provider functionality,
including GTFS parsing, vertex expansion, and edge generation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from graphserver.core import Vertex

# Import the transit provider modules
try:
    from graphserver.providers.transit import TransitProvider
    from graphserver.providers.transit.gtfs_parser import (
        GTFSParser, GTFSStop, GTFSRoute, GTFSTrip, GTFSStopTime,
        parse_time, time_to_seconds, seconds_to_time
    )
    TRANSIT_AVAILABLE = True
except ImportError:
    TRANSIT_AVAILABLE = False

# Sample GTFS data for testing
SAMPLE_STOPS_CSV = """stop_id,stop_name,stop_lat,stop_lon,location_type
stop1,Main St Station,40.7589,-73.9851,0
stop2,Park Ave Station,40.7614,-73.9776,0
stop3,Grand Central,40.7527,-73.9772,0
"""

SAMPLE_ROUTES_CSV = """route_id,route_short_name,route_long_name,route_type
route1,6,Lexington Ave Express,1
route2,4,Lexington Ave Local,1
"""

SAMPLE_TRIPS_CSV = """trip_id,route_id,service_id,direction_id,trip_headsign
trip1,route1,service1,0,Downtown
trip2,route1,service1,1,Uptown
trip3,route2,service1,0,Downtown Local
"""

SAMPLE_STOP_TIMES_CSV = """trip_id,stop_id,arrival_time,departure_time,stop_sequence
trip1,stop1,08:00:00,08:00:30,1
trip1,stop2,08:05:00,08:05:30,2
trip1,stop3,08:10:00,08:10:30,3
trip2,stop3,09:00:00,09:00:30,1
trip2,stop2,09:05:00,09:05:30,2
trip2,stop1,09:10:00,09:10:30,3
trip3,stop1,08:15:00,08:15:30,1
trip3,stop2,08:20:00,08:20:30,2
trip3,stop3,08:25:00,08:25:30,3
"""


@pytest.fixture
def sample_gtfs_dir():
    """Create a temporary directory with sample GTFS files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gtfs_path = Path(tmpdir)
        
        # Write sample GTFS files
        (gtfs_path / "stops.txt").write_text(SAMPLE_STOPS_CSV)
        (gtfs_path / "routes.txt").write_text(SAMPLE_ROUTES_CSV)
        (gtfs_path / "trips.txt").write_text(SAMPLE_TRIPS_CSV)
        (gtfs_path / "stop_times.txt").write_text(SAMPLE_STOP_TIMES_CSV)
        
        yield gtfs_path


@pytest.mark.skipif(not TRANSIT_AVAILABLE, reason="Transit provider not available")
class TestGTFSParser:
    """Test GTFS parsing functionality."""
    
    def test_parse_time(self):
        """Test GTFS time parsing."""
        assert parse_time("08:30:45").hour == 8
        assert parse_time("08:30:45").minute == 30
        assert parse_time("08:30:45").second == 45
        
        # Test times >= 24:00:00
        assert parse_time("25:30:00").hour == 1
        assert parse_time("25:30:00").minute == 30
        
        # Test invalid times
        assert parse_time("").hour == 0
        assert parse_time("invalid").hour == 0
    
    def test_time_conversion(self):
        """Test time to seconds conversion."""
        # 08:30:45 = 8*3600 + 30*60 + 45 = 30645
        t = parse_time("08:30:45")
        assert time_to_seconds(t) == 30645
        
        # Convert back
        assert seconds_to_time(30645).hour == 8
        assert seconds_to_time(30645).minute == 30
        assert seconds_to_time(30645).second == 45
    
    def test_parse_gtfs_directory(self, sample_gtfs_dir):
        """Test parsing complete GTFS directory."""
        parser = GTFSParser()
        parser.parse_gtfs_directory(sample_gtfs_dir)
        
        # Check stops
        assert len(parser.stops) == 3
        assert "stop1" in parser.stops
        assert parser.stops["stop1"].stop_name == "Main St Station"
        assert parser.stops["stop1"].stop_lat == 40.7589
        
        # Check routes
        assert len(parser.routes) == 2
        assert "route1" in parser.routes
        assert parser.routes["route1"].route_short_name == "6"
        
        # Check trips
        assert len(parser.trips) == 3
        assert "trip1" in parser.trips
        assert parser.trips["trip1"].route_id == "route1"
        
        # Check stop times
        assert len(parser.stop_times) == 9
        
        # Check indices are built
        assert "trip1" in parser.stops_by_trip
        assert len(parser.stops_by_trip["trip1"]) == 3
        assert "stop1" in parser.trips_by_stop
    
    def test_get_nearby_stops(self, sample_gtfs_dir):
        """Test finding nearby stops."""
        parser = GTFSParser()
        parser.parse_gtfs_directory(sample_gtfs_dir)
        
        # Find stops near Main St Station
        nearby = parser.get_nearby_stops(40.7589, -73.9851, radius_km=1.0)
        assert len(nearby) >= 1
        assert nearby[0].stop_id == "stop1"  # Should be closest to itself
    
    def test_get_departures_from_stop(self, sample_gtfs_dir):
        """Test getting departures from a stop."""
        parser = GTFSParser()
        parser.parse_gtfs_directory(sample_gtfs_dir)
        
        # Get departures from stop1 starting at 07:00:00 (25200 seconds)
        departures = parser.get_departures_from_stop("stop1", 7 * 3600, next_hours=2)
        
        # Should find trip1 and trip3 departures
        assert len(departures) >= 2
        trip_ids = [d.trip_id for d in departures]
        assert "trip1" in trip_ids
        assert "trip3" in trip_ids
    
    def test_get_next_stop_in_trip(self, sample_gtfs_dir):
        """Test getting next stop in trip."""
        parser = GTFSParser()
        parser.parse_gtfs_directory(sample_gtfs_dir)
        
        # Get next stop after stop1 (sequence 1) in trip1
        next_stop = parser.get_next_stop_in_trip("trip1", 1)
        assert next_stop is not None
        assert next_stop.stop_id == "stop2"
        assert next_stop.stop_sequence == 2
        
        # Last stop should return None
        last_stop = parser.get_next_stop_in_trip("trip1", 3)
        assert last_stop is None


@pytest.mark.skipif(not TRANSIT_AVAILABLE, reason="Transit provider not available")
class TestTransitProvider:
    """Test Transit provider functionality."""
    
    def test_init(self, sample_gtfs_dir):
        """Test provider initialization."""
        provider = TransitProvider(sample_gtfs_dir)
        
        assert provider.stop_count == 3
        assert provider.route_count == 2
        assert provider.trip_count == 3
    
    def test_edges_from_coordinates(self, sample_gtfs_dir):
        """Test edge generation from coordinates."""
        provider = TransitProvider(sample_gtfs_dir, search_radius_km=1.0)
        
        # Vertex near Main St Station with time
        vertex = Vertex({
            "lat": 40.7589,
            "lon": -73.9851,
            "time": 8 * 3600,  # 08:00:00
        })
        
        edges = provider(vertex)
        
        # Should find nearby stops
        assert len(edges) > 0
        
        # Check first edge
        target_vertex, edge = edges[0]
        assert "stop_id" in target_vertex
        assert "time" in target_vertex  # Arrival time
        assert edge.metadata["edge_type"] == "coordinate_to_stop"
    
    def test_edges_from_stop(self, sample_gtfs_dir):
        """Test edge generation from stop."""
        provider = TransitProvider(sample_gtfs_dir)
        
        # Vertex at stop1 with time before departures
        vertex = Vertex({
            "stop_id": "stop1",
            "time": 7 * 3600,  # 07:00:00, before first departure
        })
        
        edges = provider(vertex)
        
        # Should find departures
        assert len(edges) >= 2  # trip1 and trip3
        
        # Check boarding vertices
        for target_vertex, edge in edges:
            assert target_vertex["vehicle_state"] == "boarding"
            assert "trip_id" in target_vertex
            assert "stop_sequence" in target_vertex
            assert edge.metadata["edge_type"] == "stop_to_boarding"
    
    def test_edges_from_boarding_vertex(self, sample_gtfs_dir):
        """Test edge generation from boarding vertex."""
        provider = TransitProvider(sample_gtfs_dir)
        
        # Boarding vertex for trip1 at stop1
        vertex = Vertex({
            "time": 8 * 3600,  # 08:00:00
            "trip_id": "trip1",
            "stop_sequence": 1,
            "vehicle_state": "boarding",
            "stop_id": "stop1",
        })
        
        edges = provider(vertex)
        
        # Should have one edge to next stop
        assert len(edges) == 1
        
        target_vertex, edge = edges[0]
        assert target_vertex["vehicle_state"] == "alright"
        assert target_vertex["stop_id"] == "stop2"  # Next stop in trip1
        assert target_vertex["stop_sequence"] == 2
        assert edge.metadata["edge_type"] == "boarding_to_alright"
    
    def test_edges_from_alright_vertex(self, sample_gtfs_dir):
        """Test edge generation from alright vertex."""
        provider = TransitProvider(sample_gtfs_dir)
        
        # Alright vertex at stop2
        vertex = Vertex({
            "time": 8 * 3600 + 5 * 60,  # 08:05:00
            "trip_id": "trip1",
            "stop_sequence": 2,
            "vehicle_state": "alright",
            "stop_id": "stop2",
        })
        
        edges = provider(vertex)
        
        # Should have two edges: to boarding vertex and to stop vertex
        assert len(edges) == 2
        
        edge_types = [edge.metadata["edge_type"] for _, edge in edges]
        assert "alright_to_boarding" in edge_types
        assert "alright_to_stop" in edge_types
    
    def test_unknown_vertex_type(self, sample_gtfs_dir):
        """Test handling of unknown vertex types."""
        provider = TransitProvider(sample_gtfs_dir)
        
        # Unknown vertex type
        vertex = Vertex({"unknown_field": "value"})
        
        edges = provider(vertex)
        assert len(edges) == 0
    
    def test_get_stop_by_id(self, sample_gtfs_dir):
        """Test getting stop by ID."""
        provider = TransitProvider(sample_gtfs_dir)
        
        stop_vertex = provider.get_stop_by_id("stop1")
        assert stop_vertex is not None
        assert stop_vertex["stop_id"] == "stop1"
        assert stop_vertex["stop_name"] == "Main St Station"
        
        # Non-existent stop
        assert provider.get_stop_by_id("nonexistent") is None
    
    def test_find_nearest_stop(self, sample_gtfs_dir):
        """Test finding nearest stop."""
        provider = TransitProvider(sample_gtfs_dir)
        
        # Find stop near Main St Station coordinates
        nearest = provider.find_nearest_stop(40.7589, -73.9851)
        assert nearest is not None
        assert nearest["stop_id"] == "stop1"
        
        # No stops in very small radius
        provider_small_radius = TransitProvider(sample_gtfs_dir, search_radius_km=0.001)
        assert provider_small_radius.find_nearest_stop(0.0, 0.0) is None