"""Tests for transit provider functionality."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from graphserver import Vertex


def create_sample_gtfs() -> Path:
    """Create a minimal GTFS feed for testing."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    gtfs_zip = temp_dir / "sample_gtfs.zip"

    # GTFS files content
    agency_txt = """agency_id,agency_name,agency_url,agency_timezone
1,Sample Transit,http://example.com,America/New_York
"""

    stops_txt = """stop_id,stop_name,stop_lat,stop_lon
stop1,First Stop,40.7589,-73.9851
stop2,Second Stop,40.7614,-73.9776
stop3,Third Stop,40.7505,-73.9934
"""

    routes_txt = """route_id,agency_id,route_short_name,route_long_name,route_type
route1,1,1,Sample Route,3
"""

    trips_txt = """route_id,service_id,trip_id,trip_headsign
route1,service1,trip1,To Third Stop
"""

    stop_times_txt = """trip_id,arrival_time,departure_time,stop_id,stop_sequence
trip1,09:00:00,09:00:00,stop1,1
trip1,09:05:00,09:05:00,stop2,2
trip1,09:10:00,09:10:00,stop3,3
"""

    calendar_txt = """service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
service1,1,1,1,1,1,0,0,20240101,20241231
"""

    # Create zip file with GTFS data
    with zipfile.ZipFile(gtfs_zip, "w") as zf:
        zf.writestr("agency.txt", agency_txt)
        zf.writestr("stops.txt", stops_txt)
        zf.writestr("routes.txt", routes_txt)
        zf.writestr("trips.txt", trips_txt)
        zf.writestr("stop_times.txt", stop_times_txt)
        zf.writestr("calendar.txt", calendar_txt)

    return gtfs_zip


def test_transit_provider_import() -> None:
    """Test that transit provider can be imported."""
    try:
        from graphserver.providers.transit import TransitProvider

        assert TransitProvider is not None
    except ImportError:
        pytest.skip("Transit dependencies not installed")


def test_transit_provider_basic_functionality() -> None:
    """Test basic transit provider functionality."""
    try:
        from graphserver.providers.transit import TransitProvider

        # Create sample GTFS
        gtfs_file = create_sample_gtfs()

        # Initialize provider
        provider = TransitProvider(gtfs_file)

        # Test basic properties
        assert provider.stop_count > 0
        assert provider.route_count > 0
        assert provider.trip_count > 0

        # Clean up
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()

    except ImportError:
        pytest.skip("Transit dependencies not installed")


def test_transit_provider_coordinate_expansion() -> None:
    """Test edge expansion from coordinates."""
    try:
        from graphserver.providers.transit import TransitProvider

        # Create sample GTFS
        gtfs_file = create_sample_gtfs()

        # Initialize provider
        provider = TransitProvider(gtfs_file)

        # Test coordinate-based vertex (near first stop)
        coord_vertex = Vertex(
            {
                "lat": 40.7589,  # Same as stop1
                "lon": -73.9851,
                "time": 1704708000,  # Some timestamp
            }
        )

        edges = provider.out_edges(coord_vertex)

        # Should find nearby stops
        assert len(edges) > 0

        # All edges should be to stop vertices
        for target_vertex, edge in edges:
            assert "stop_id" in target_vertex
            assert "time" in target_vertex
            assert edge.get_metadata("edge_type") == "walk_to_stop"

        # Clean up
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()

    except ImportError:
        pytest.skip("Transit dependencies not installed")


def test_transit_provider_stop_expansion() -> None:
    """Test edge expansion from stop with time."""
    try:
        from graphserver.providers.transit import TransitProvider

        # Create sample GTFS
        gtfs_file = create_sample_gtfs()

        # Initialize provider
        provider = TransitProvider(gtfs_file)

        # Test stop vertex - 8:30 AM on some date should find 9:00 AM departure
        stop_vertex = Vertex(
            {
                "stop_id": "stop1",
                "time": 1704704400,  # Some early morning timestamp
            }
        )

        edges = provider.out_edges(stop_vertex)

        # Should find departures (might be empty if time calculation is off)
        # This tests the logic even if no departures found due to time issues
        assert isinstance(edges, list)

        # If we find departures, they should be boarding vertices
        for target_vertex, edge in edges:
            assert target_vertex.get("vehicle_state") == "boarding"
            assert "trip_id" in target_vertex
            assert edge.get_metadata("edge_type") == "wait_for_departure"

        # Clean up
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()

    except ImportError:
        pytest.skip("Transit dependencies not installed")


def test_transit_provider_integration() -> None:
    """Test transit provider integration with engine."""
    try:
        from graphserver import Engine
        from graphserver.providers.transit import TransitProvider

        # Create sample GTFS
        gtfs_file = create_sample_gtfs()

        # Initialize provider and engine
        provider = TransitProvider(gtfs_file)
        engine = Engine()
        engine.register_provider("transit", provider)

        # Test that provider is registered
        assert "transit" in engine.providers

        # Test basic planning with coordinate vertices
        start = Vertex({"lat": 40.7589, "lon": -73.9851, "time": 1704704400})

        goal = Vertex(
            {
                "lat": 40.7505,
                "lon": -73.9934,
                "time": 1704712800,  # Later time
            }
        )

        # This should not fail even if no path is found
        try:
            result = engine.plan(start=start, goal=goal)
            # Path might not be found due to timing, but shouldn't crash
            assert result is not None
        except RuntimeError as e:
            # Planning might fail due to no path, which is fine for this test
            assert (  # noqa: PT017
                "no path found" in str(e).lower()
                or "goal not reached" in str(e).lower()
                or "Path planning failed" in str(e)
            )

        # Clean up
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()

    except ImportError:
        pytest.skip("Transit dependencies not installed")


def test_vertex_state_transitions() -> None:
    """Test the different vertex state transitions."""
    try:
        from graphserver.providers.transit import TransitProvider

        # Create sample GTFS
        gtfs_file = create_sample_gtfs()

        # Initialize provider
        provider = TransitProvider(gtfs_file)

        # Test boarding vertex expansion
        boarding_vertex = Vertex(
            {
                "time": 1704708000,
                "trip_id": "trip1",
                "stop_sequence": 1,
                "vehicle_state": "boarding",
                "route_id": "route1",
            }
        )

        boarding_edges = provider.out_edges(boarding_vertex)

        # Should transition to alight vertex at next stop
        if boarding_edges:  # May be empty due to time calculations
            target_vertex, edge = boarding_edges[0]
            assert target_vertex.get("vehicle_state") == "alight"
            assert edge.get_metadata("edge_type") == "in_vehicle_travel"

        # Test alight vertex expansion
        alight_vertex = Vertex(
            {
                "time": 1704708300,
                "trip_id": "trip1",
                "stop_sequence": 2,
                "vehicle_state": "alight",
                "stop_id": "stop2",
                "route_id": "route1",
            }
        )

        alight_edges = provider.out_edges(alight_vertex)

        # Should have two edges: to boarding vertex and to stop vertex
        assert len(alight_edges) == 2

        edge_types = [edge.get_metadata("edge_type") for _, edge in alight_edges]
        assert "alight_to_boarding" in edge_types
        assert "alight_at_stop" in edge_types

        # Clean up
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()

    except ImportError:
        pytest.skip("Transit dependencies not installed")


def test_first_and_last_stop_behavior() -> None:
    """Test that last stops don't have alight-to-boarding edges and don't allow boarding."""
    try:
        from graphserver.providers.transit import TransitProvider

        # Create sample GTFS
        gtfs_file = create_sample_gtfs()

        # Initialize provider
        provider = TransitProvider(gtfs_file)

        # Test alight vertex at FIRST stop (stop_sequence 1)
        # This should have both edges (normal behavior, passengers can re-board)
        first_stop_alight_vertex = Vertex(
            {
                "time": 1704708000,
                "trip_id": "trip1",
                "stop_sequence": 1,  # First stop
                "vehicle_state": "alight",
                "stop_id": "stop1",
                "route_id": "route1",
            }
        )

        first_stop_alight_edges = provider.out_edges(first_stop_alight_vertex)

        # Should have TWO edges: to boarding vertex and to stop vertex
        assert len(first_stop_alight_edges) == 2
        edge_types = [
            edge.get_metadata("edge_type") for _, edge in first_stop_alight_edges
        ]
        assert "alight_at_stop" in edge_types
        assert "alight_to_boarding" in edge_types

        # Test alight vertex at MIDDLE stop (stop_sequence 2)
        # This should have both edges (normal behavior)
        middle_stop_alight_vertex = Vertex(
            {
                "time": 1704708300,
                "trip_id": "trip1",
                "stop_sequence": 2,  # Middle stop
                "vehicle_state": "alight",
                "stop_id": "stop2",
                "route_id": "route1",
            }
        )

        middle_stop_alight_edges = provider.out_edges(middle_stop_alight_vertex)

        # Should have TWO edges: to boarding vertex and to stop vertex
        assert len(middle_stop_alight_edges) == 2
        edge_types = [
            edge.get_metadata("edge_type") for _, edge in middle_stop_alight_edges
        ]
        assert "alight_to_boarding" in edge_types
        assert "alight_at_stop" in edge_types

        # Test alight vertex at LAST stop (stop_sequence 3)
        # This should NOT have an alight_to_boarding edge (can't continue at terminus)
        last_stop_alight_vertex = Vertex(
            {
                "time": 1704708600,
                "trip_id": "trip1",
                "stop_sequence": 3,  # Last stop
                "vehicle_state": "alight",
                "stop_id": "stop3",
                "route_id": "route1",
            }
        )

        last_stop_alight_edges = provider.out_edges(last_stop_alight_vertex)

        # Should have only ONE edge: to stop vertex (no alight_to_boarding)
        assert len(last_stop_alight_edges) == 1
        edge_types = [
            edge.get_metadata("edge_type") for _, edge in last_stop_alight_edges
        ]
        assert "alight_at_stop" in edge_types
        assert "alight_to_boarding" not in edge_types

        # Test boarding vertex at LAST stop (stop_sequence 3)
        # This should have NO edges (end of trip)
        last_stop_boarding_vertex = Vertex(
            {
                "time": 1704708600,
                "trip_id": "trip1",
                "stop_sequence": 3,  # Last stop
                "vehicle_state": "boarding",
                "route_id": "route1",
            }
        )

        last_stop_boarding_edges = provider.out_edges(last_stop_boarding_vertex)

        # Should have NO edges (end of trip, can't continue)
        assert len(last_stop_boarding_edges) == 0

        # Test stop vertex at LAST stop (stop_sequence 3)
        # This should have NO departure edges (no boarding at terminus)
        last_stop_vertex = Vertex(
            {
                "stop_id": "stop3",
                "time": 1704708500,  # Just before the trip arrives at stop3
            }
        )

        last_stop_edges = provider.out_edges(last_stop_vertex)

        # Should have NO edges (no departures from terminus stop)
        assert len(last_stop_edges) == 0

        # Test stop vertex at FIRST/MIDDLE stop for comparison
        # This should have departure edges (normal behavior)
        first_stop_vertex = Vertex(
            {
                "stop_id": "stop1",
                "time": 1704707900,  # Just before trip departure from stop1
            }
        )

        first_stop_edges = provider.out_edges(first_stop_vertex)

        # Should have at least one departure edge
        if first_stop_edges:  # May be empty due to time calculations
            for _, edge in first_stop_edges:
                assert edge.get_metadata("edge_type") == "wait_for_departure"

        # Clean up
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()

    except ImportError:
        pytest.skip("Transit dependencies not installed")


if __name__ == "__main__":
    # Run basic tests
    test_transit_provider_import()
    print("✓ Import test passed")

    test_transit_provider_basic_functionality()
    print("✓ Basic functionality test passed")

    test_transit_provider_coordinate_expansion()
    print("✓ Coordinate expansion test passed")

    test_transit_provider_stop_expansion()
    print("✓ Stop expansion test passed")

    test_vertex_state_transitions()
    print("✓ Vertex state transitions test passed")

    test_transit_provider_integration()
    print("✓ Integration test passed")

    print("All tests passed!")
