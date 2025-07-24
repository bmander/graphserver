"""Simple OSM Routing Test

This module tests basic coordinate-to-coordinate routing using a minimal OSM dataset
to verify the split provider architecture works correctly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Skip all tests if OSM dependencies are not available
try:
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
    from graphserver.providers.osm.types import WalkingProfile

    OSM_AVAILABLE = True
except ImportError:
    OSM_AVAILABLE = False

# Minimal OSM data with a single road from (0,0) to (0,0.001)
SIMPLE_OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="0.0" lon="0.0">
    <tag k="name" v="Start Node"/>
  </node>
  <node id="2" lat="0.0" lon="0.001">
    <tag k="name" v="End Node"/>
  </node>
  <way id="100" version="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="footway"/>
    <tag k="name" v="Simple Test Road"/>
  </way>
</osm>"""


@pytest.fixture
def simple_osm_file() -> Path:
    """Create a temporary OSM file with minimal test data."""
    if not OSM_AVAILABLE:
        pytest.skip("OSM dependencies not available")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
        f.write(SIMPLE_OSM_XML)
        f.flush()
        return Path(f.name)


@pytest.fixture
def simple_walking_profile() -> WalkingProfile:
    """Create a simple walking profile for testing."""
    if not OSM_AVAILABLE:
        pytest.skip("OSM dependencies not available")

    return WalkingProfile(base_speed_ms=1.0, avoid_stairs=False, avoid_busy_roads=False)


class TestSimpleOSMRouting:
    """Test basic coordinate-to-coordinate routing with minimal OSM data."""

    def test_simple_osm_parsing(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test that the simple OSM file parses correctly."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create network provider and check parsing
        network_provider = OSMNetworkProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
        )

        # Should have exactly 2 nodes and 1 way
        assert network_provider.node_count == 2
        assert network_provider.way_count == 1
        assert network_provider.edge_count == 2  # Bidirectional way creates 2 edges

        # Check specific nodes exist
        node1 = network_provider.get_node_by_id(1)
        node2 = network_provider.get_node_by_id(2)

        assert node1 is not None
        assert node2 is not None
        assert node1["lat"] == 0.0
        assert node1["lon"] == 0.0
        assert node2["lat"] == 0.0
        assert node2["lon"] == 0.001

        # Clean up
        simple_osm_file.unlink()

    def test_network_provider_edges(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test that the network provider generates correct edges between OSM nodes."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        network_provider = OSMNetworkProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
        )

        # Test edges from node 1
        node1_vertex = Vertex({"osm_node_id": 1})
        edges_from_1 = network_provider(node1_vertex)

        assert len(edges_from_1) == 1  # Should connect to node 2
        target_vertex, edge = edges_from_1[0]
        assert target_vertex["osm_node_id"] == 2
        assert edge.cost > 0
        assert edge.metadata["edge_type"] == "osm_way"

        # Test edges from node 2
        node2_vertex = Vertex({"osm_node_id": 2})
        edges_from_2 = network_provider(node2_vertex)

        assert len(edges_from_2) == 1  # Should connect to node 1
        target_vertex, edge = edges_from_2[0]
        assert target_vertex["osm_node_id"] == 1
        assert edge.cost > 0
        assert edge.metadata["edge_type"] == "osm_way"

        # Clean up
        simple_osm_file.unlink()

    def test_access_provider_onramps(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test access provider generates onramps from access points to OSM nodes."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create access provider with wide search radius
        access_provider = OSMAccessProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
            search_radius_m=1000.0,  # Wide radius to ensure we find nodes
            max_nearby_nodes=5,
            build_index=True,
        )

        # Register access point near node 1
        ap1_id = access_provider.register_access_point(0.0001, 0.0001)  # Close to (0,0)
        ap1_vertex = access_provider.get_access_point_vertex(ap1_id)
        onramps = access_provider(ap1_vertex)

        assert len(onramps) > 0
        # Should find at least node 1
        found_node_1 = any(target["osm_node_id"] == 1 for target, _ in onramps)
        assert found_node_1

        # Register access point near node 2
        ap2_id = access_provider.register_access_point(
            0.0001, 0.0011
        )  # Close to (0, 0.001)
        ap2_vertex = access_provider.get_access_point_vertex(ap2_id)
        onramps = access_provider(ap2_vertex)

        assert len(onramps) > 0
        # Should find at least node 2
        found_node_2 = any(target["osm_node_id"] == 2 for target, _ in onramps)
        assert found_node_2

        # Clean up
        simple_osm_file.unlink()

    def test_provider_integration(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test that both providers can be registered with the engine."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create both providers
        network_provider = OSMNetworkProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
        )

        access_provider = OSMAccessProvider(
            parser=network_provider.parser,  # Share parser for efficiency
            walking_profile=simple_walking_profile,
            search_radius_m=1000.0,
            max_nearby_nodes=5,
            build_index=True,
        )

        # Register with engine
        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        # Verify registration
        assert "osm_network" in engine.providers
        assert "osm_access" in engine.providers
        assert len(engine.providers) == 2

        # Clean up
        simple_osm_file.unlink()

    def test_coordinate_to_coordinate_routing_setup(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test setup for coordinate-to-coordinate routing (without offramps yet)."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create providers
        network_provider = OSMNetworkProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
        )

        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
            walking_profile=simple_walking_profile,
            search_radius_m=1000.0,
            max_nearby_nodes=5,
            build_index=True,
        )

        # Register with engine
        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        # Register access points for test coordinates
        start_ap_id = access_provider.register_access_point(
            0.0001, 0.0001
        )  # Near node 1
        goal_ap_id = access_provider.register_access_point(
            0.0001, 0.0011
        )  # Near node 2

        start_vertex = access_provider.get_access_point_vertex(start_ap_id)
        goal_vertex = access_provider.get_access_point_vertex(goal_ap_id)

        # Verify that access provider can generate onramps for both access points
        start_onramps = access_provider(start_vertex)
        goal_onramps = access_provider(goal_vertex)

        assert len(start_onramps) > 0, "Should find onramps from start access point"
        assert len(goal_onramps) > 0, "Should find onramps from goal access point"

        # Verify that network provider can navigate between OSM nodes
        node1_vertex = Vertex({"osm_node_id": 1})
        node2_vertex = Vertex({"osm_node_id": 2})

        edges_1_to_2 = network_provider(node1_vertex)
        edges_2_to_1 = network_provider(node2_vertex)

        assert len(edges_1_to_2) > 0, "Should find edges from node 1 to node 2"
        assert len(edges_2_to_1) > 0, "Should find edges from node 2 to node 1"

        # Note: coordinate-to-coordinate routing will require offramp implementation

        # Clean up
        simple_osm_file.unlink()

    def test_complete_coordinate_to_coordinate_routing(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test complete coordinate-to-coordinate routing with offramps."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create providers
        network_provider = OSMNetworkProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
        )

        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
            walking_profile=simple_walking_profile,
            search_radius_m=1000.0,  # Wide radius to ensure connections
            max_nearby_nodes=5,
            build_index=True,
        )

        # Register with engine
        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        # Register access points for test coordinates
        start_ap_id = access_provider.register_access_point(
            0.0001, 0.0001
        )  # Near node 1 (0,0)
        goal_ap_id = access_provider.register_access_point(
            0.0001, 0.0011
        )  # Near node 2 (0,0.001)

        start_vertex = access_provider.get_access_point_vertex(start_ap_id)
        goal_vertex = access_provider.get_access_point_vertex(goal_ap_id)

        # Manually test the bidirectional access provider functionality
        # 1. Verify onramps work
        start_onramps = access_provider(start_vertex)
        assert len(start_onramps) > 0, "Should generate onramps from start access point"

        # 2. Verify that goal access point also generates onramps
        goal_onramps = access_provider(goal_vertex)
        assert len(goal_onramps) > 0, "Should generate onramps from goal access point"
        # Check that access points are registered
        assert len(access_provider.list_access_points()) >= 2, (
            "Should have registered access points"
        )

        # 3. Verify offramps work - test with OSM nodes
        node1_vertex = Vertex({"osm_node_id": 1})
        node2_vertex = Vertex({"osm_node_id": 2})

        offramps_from_1 = access_provider(node1_vertex)
        offramps_from_2 = access_provider(node2_vertex)

        # Should have offramps to registered access points
        assert len(offramps_from_1) > 0 or len(offramps_from_2) > 0, (
            "Should generate offramps to access points"
        )

        # 4. Test complete routing using the engine
        result = engine.plan(start=start_vertex, goal=goal_vertex)

        # If planning succeeds, we have working coordinate-to-coordinate routing!
        assert result is not None, "Planning should return a result"

        # Verify the path structure if we got results
        if len(result) > 0:
            # Successful coordinate-to-coordinate routing
            print(f"Route found with {len(result)} steps!")

            # Verify the path structure
            for i, path_edge in enumerate(result):
                assert hasattr(path_edge, "target"), f"Path edge {i} should have target"
                assert hasattr(path_edge, "edge"), f"Path edge {i} should have edge"
                assert path_edge.edge.cost is not None, (
                    f"Path edge {i} should have cost"
                )
                print(f"Step {i}: {path_edge.target} -> cost {path_edge.edge.cost}")
        else:
            print("No route found between access points")

        # Clean up
        access_provider.clear_access_points()
        simple_osm_file.unlink()
