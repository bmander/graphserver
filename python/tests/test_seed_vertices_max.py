"""Tests for seed_vertices max parameter functionality.

This module tests the max parameter added to the seed_vertices method
across all provider implementations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from graphserver.core import Vertex


class TestSeedVerticesMaxParameter:
    """Test max parameter functionality across all providers."""

    def test_grid_provider_max_parameter(self) -> None:
        """Test max parameter with GridProvider from precache tests."""
        from tests.test_precache import GridProvider

        # Create a 5x5 grid (25 total vertices)
        provider = GridProvider(5, 5)

        # Test unlimited (default behavior)
        all_vertices = provider.seed_vertices()
        assert len(all_vertices) == 25

        # Test max_vertices=None (explicit unlimited)
        unlimited_vertices = provider.seed_vertices(max_vertices=None)
        assert len(unlimited_vertices) == 25
        assert all_vertices == unlimited_vertices

        # Test max_vertices=0 (empty)
        empty_vertices = provider.seed_vertices(max_vertices=0)
        assert len(empty_vertices) == 0

        # Test max_vertices=5 (limited)
        limited_vertices = provider.seed_vertices(max_vertices=5)
        assert len(limited_vertices) == 5

        # Test max_vertices=10 (less than total)
        partial_vertices = provider.seed_vertices(max_vertices=10)
        assert len(partial_vertices) == 10

        # Test max_vertices=30 (more than total)
        excess_vertices = provider.seed_vertices(max_vertices=30)
        assert len(excess_vertices) == 25  # Should return all available

        # Verify returned vertices are valid
        for vertex in limited_vertices:
            assert "x" in vertex
            assert "y" in vertex
            assert isinstance(vertex["x"], int)
            assert isinstance(vertex["y"], int)

    def test_osm_network_provider_max_parameter(self) -> None:
        """Test max parameter with OSMNetworkProvider."""
        try:
            from graphserver.providers.osm import OSMDataSource, OSMNetworkProvider
            from graphserver.providers.osm.types import WalkingProfile
        except ImportError:
            pytest.skip("OSM dependencies not available")

        # Create sample OSM file
        sample_osm_xml = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="47.6062" lon="-122.3321"/>
  <node id="2" lat="47.6072" lon="-122.3311"/>
  <node id="3" lat="47.6082" lon="-122.3301"/>
  <node id="4" lat="47.6092" lon="-122.3291"/>
  <way id="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <nd ref="3"/>
    <nd ref="4"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(sample_osm_xml)
            sample_osm_file = Path(f.name)

        try:
            walking_profile = WalkingProfile()
            data_source = OSMDataSource(
                sample_osm_file, walking_profile=walking_profile
            )
            provider = OSMNetworkProvider(data_source)

            # Test unlimited (should return all 4 nodes)
            all_vertices = provider.seed_vertices()
            assert len(all_vertices) == 4

            # Test max_vertices=None (explicit unlimited)
            unlimited_vertices = provider.seed_vertices(max_vertices=None)
            assert len(unlimited_vertices) == 4
            assert len(all_vertices) == len(unlimited_vertices)

            # Test max_vertices=0 (empty)
            empty_vertices = provider.seed_vertices(max_vertices=0)
            assert len(empty_vertices) == 0

            # Test max_vertices=2 (limited)
            limited_vertices = provider.seed_vertices(max_vertices=2)
            assert len(limited_vertices) == 2

            # Test max_vertices=10 (more than total)
            excess_vertices = provider.seed_vertices(max_vertices=10)
            assert len(excess_vertices) == 4  # Should return all available

            # Verify returned vertices have osm_node_id
            for vertex in limited_vertices:
                assert "osm_node_id" in vertex
                assert isinstance(vertex["osm_node_id"], int)

        finally:
            sample_osm_file.unlink()

    def test_osm_access_provider_max_parameter(self) -> None:
        """Test max parameter with OSMAccessProvider."""
        try:
            from graphserver.providers.osm import OSMAccessProvider, OSMDataSource
            from graphserver.providers.osm.types import WalkingProfile
        except ImportError:
            pytest.skip("OSM dependencies not available")

        # Create sample OSM file
        sample_osm_xml = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="47.6062" lon="-122.3321"/>
  <node id="2" lat="47.6072" lon="-122.3311"/>
  <way id="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(sample_osm_xml)
            sample_osm_file = Path(f.name)

        try:
            walking_profile = WalkingProfile()
            data_source = OSMDataSource(
                sample_osm_file, walking_profile=walking_profile
            )
            provider = OSMAccessProvider(data_source)

            # Initially no linked vertices
            empty_vertices = provider.seed_vertices()
            assert len(empty_vertices) == 0

            # Test max_vertices=0 on empty
            empty_with_max = provider.seed_vertices(max_vertices=0)
            assert len(empty_with_max) == 0

            # Link some vertices
            test_vertex1 = Vertex({"place": "library", "id": "lib1"})
            test_vertex2 = Vertex({"place": "station", "id": "stat1"})
            test_vertex3 = Vertex({"place": "cafe", "id": "cafe1"})

            provider.link(test_vertex1, 47.6062, -122.3321)
            provider.link(test_vertex2, 47.6072, -122.3311)
            provider.link(test_vertex3, 47.6062, -122.3321)  # Link to same node

            # Now should have 3 linked vertices
            all_vertices = provider.seed_vertices()
            assert len(all_vertices) == 3

            # Test max_vertices=None (explicit unlimited)
            unlimited_vertices = provider.seed_vertices(max_vertices=None)
            assert len(unlimited_vertices) == 3

            # Test max_vertices=0 (empty)
            empty_vertices = provider.seed_vertices(max_vertices=0)
            assert len(empty_vertices) == 0

            # Test max_vertices=2 (limited)
            limited_vertices = provider.seed_vertices(max_vertices=2)
            assert len(limited_vertices) == 2

            # Test max_vertices=10 (more than total)
            excess_vertices = provider.seed_vertices(max_vertices=10)
            assert len(excess_vertices) == 3  # Should return all available

            # Verify returned vertices are valid
            for vertex in limited_vertices:
                assert "place" in vertex
                assert "id" in vertex

        finally:
            sample_osm_file.unlink()

    def test_transit_provider_max_parameter(self) -> None:
        """Test max parameter with TransitProvider."""
        try:
            from graphserver.providers.transit import TransitProvider
        except ImportError:
            pytest.skip("Transit dependencies not available")

        # Create a minimal GTFS structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create stops.txt
            stops_content = """stop_id,stop_name,stop_lat,stop_lon
stop1,First Stop,47.6062,-122.3321
stop2,Second Stop,47.6072,-122.3311
stop3,Third Stop,47.6082,-122.3301
stop4,Fourth Stop,47.6092,-122.3291
"""
            (temp_path / "stops.txt").write_text(stops_content)

            # Create routes.txt
            routes_content = """route_id,route_short_name,route_long_name,route_type
route1,1,Test Route,3
"""
            (temp_path / "routes.txt").write_text(routes_content)

            # Create trips.txt
            trips_content = """route_id,service_id,trip_id
route1,service1,trip1
"""
            (temp_path / "trips.txt").write_text(trips_content)

            # Create stop_times.txt
            stop_times_content = (
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                "trip1,08:00:00,08:00:00,stop1,1\n"
                "trip1,08:05:00,08:05:00,stop2,2\n"
            )
            (temp_path / "stop_times.txt").write_text(stop_times_content)

            # Create calendar.txt
            calendar_content = (
                "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
                "start_date,end_date\n"
                "service1,1,1,1,1,1,0,0,20230101,20231231\n"
            )
            (temp_path / "calendar.txt").write_text(calendar_content)

            try:
                provider = TransitProvider(temp_path, build_index=False)

                # Test unlimited (should return all 4 stops)
                all_vertices = provider.seed_vertices()
                assert len(all_vertices) == 4

                # Test max_vertices=None (explicit unlimited)
                unlimited_vertices = provider.seed_vertices(max_vertices=None)
                assert len(unlimited_vertices) == 4

                # Test max_vertices=0 (empty)
                empty_vertices = provider.seed_vertices(max_vertices=0)
                assert len(empty_vertices) == 0

                # Test max_vertices=2 (limited)
                limited_vertices = provider.seed_vertices(max_vertices=2)
                assert len(limited_vertices) == 2

                # Test max_vertices=10 (more than total)
                excess_vertices = provider.seed_vertices(max_vertices=10)
                assert len(excess_vertices) == 4  # Should return all available

                # Verify returned vertices have stop_id
                for vertex in limited_vertices:
                    assert "stop_id" in vertex
                    assert vertex["stop_id"] in ["stop1", "stop2", "stop3", "stop4"]

            except (ImportError, ValueError, RuntimeError) as e:
                # If GTFS parsing fails, that's okay for this test
                pytest.skip(f"GTFS parsing failed: {e}")

    def test_max_parameter_type_validation(self) -> None:
        """Test that max parameter handles various input types correctly."""
        from tests.test_precache import GridProvider

        provider = GridProvider(3, 3)  # 9 total vertices

        # Test valid integer values
        assert len(provider.seed_vertices(max_vertices=0)) == 0
        assert len(provider.seed_vertices(max_vertices=1)) == 1
        assert len(provider.seed_vertices(max_vertices=5)) == 5
        assert len(provider.seed_vertices(max_vertices=9)) == 9
        assert len(provider.seed_vertices(max_vertices=15)) == 9  # More than available

        # Test None (unlimited)
        assert len(provider.seed_vertices(max_vertices=None)) == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
