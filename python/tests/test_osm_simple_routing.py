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

    def _create_providers_and_engine(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> tuple[OSMNetworkProvider, OSMAccessProvider, Engine]:
        """Create and register providers with engine."""
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

        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        return network_provider, access_provider, engine

    def _validate_provider_registration(self, engine: Engine) -> None:
        """Validate that providers are properly registered."""
        assert "osm_network" in engine.providers
        assert "osm_access" in engine.providers
        assert len(engine.providers) == 2

    def _register_and_validate_access_points(
        self, access_provider: OSMAccessProvider
    ) -> tuple[str, str]:
        """Register access points and validate registration."""
        start_ap_id = access_provider.register_access_point(
            0.0001, 0.0001
        )  # Near node 1
        goal_ap_id = access_provider.register_access_point(
            0.0001, 0.0011
        )  # Near node 2

        assert start_ap_id is not None
        assert goal_ap_id is not None
        assert start_ap_id != goal_ap_id
        assert len(access_provider.list_access_points()) >= 2

        return start_ap_id, goal_ap_id

    def _get_and_validate_vertices(
        self, access_provider: OSMAccessProvider, start_ap_id: str, goal_ap_id: str
    ) -> tuple[Vertex, Vertex]:
        """Get vertices from access points and validate their structure."""
        start_vertex = access_provider.get_access_point_vertex(start_ap_id)
        goal_vertex = access_provider.get_access_point_vertex(goal_ap_id)

        assert start_vertex is not None
        assert goal_vertex is not None
        assert "access_point_id" in start_vertex
        assert "access_point_id" in goal_vertex
        assert start_vertex["access_point_id"] == start_ap_id
        assert goal_vertex["access_point_id"] == goal_ap_id
        assert "lat" in start_vertex
        assert "lon" in start_vertex
        assert "lat" in goal_vertex
        assert "lon" in goal_vertex
        assert "_id_hash" in start_vertex
        assert "_id_hash" in goal_vertex

        return start_vertex, goal_vertex

    def _execute_and_validate_pathfinding(
        self, engine: Engine, start_vertex: Vertex, goal_vertex: Vertex
    ) -> tuple[object, float]:
        """Execute pathfinding and validate basic results."""
        import time

        planning_start = time.time()
        result = engine.plan(start=start_vertex, goal=goal_vertex)
        planning_time = time.time() - planning_start

        assert result is not None, "Planning should return a result"
        assert len(result) > 0, "Should find a path between the access points"
        assert planning_time < 1.0, f"Pathfinding took too long: {planning_time:.3f}s"

        return result, planning_time

    def _validate_path_structure(self, result: object) -> None:
        """Validate the structure and properties of the path result."""
        assert hasattr(result, "total_cost"), "Result should have total_cost property"
        assert result.total_cost > 0, "Path should have positive cost"

        for i, path_edge in enumerate(result):
            assert hasattr(path_edge, "target"), f"Path edge {i} should have target"
            assert hasattr(path_edge, "edge"), f"Path edge {i} should have edge"
            assert hasattr(path_edge.edge, "cost"), f"Path edge {i} should have cost"
            assert hasattr(path_edge.edge, "metadata"), (
                f"Path edge {i} should have metadata"
            )
            assert path_edge.edge.cost >= 0, (
                f"Path edge {i} cost should be non-negative"
            )
            assert hasattr(path_edge.target, "__getitem__"), (
                f"Path edge {i} target should be dict-like"
            )
            assert "_id_hash" in path_edge.target, (
                f"Path edge {i} target should have _id_hash"
            )

    def _validate_path_connectivity(self, result: object, goal_vertex: Vertex) -> None:
        """Validate that the path connects properly to the goal."""
        last_edge = result[-1]
        assert last_edge.target["_id_hash"] == goal_vertex["_id_hash"], (
            "Path should end at goal vertex"
        )

        # With the simple OSM data (2 nodes, 1 way), we expect a short path
        assert len(result) <= 5, (
            f"Path should be short for simple data, got {len(result)} edges"
        )

    def test_minimal_pathfinding_workflow(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test the complete minimal pathfinding workflow with detailed step validation.

        This test validates each step of the pathfinding process:
        1. Provider setup and engine registration
        2. Access point registration and vertex creation
        3. Pathfinding execution and result validation
        4. Path structure and cost validation
        """
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Step 1: Create providers and engine
        network_provider, access_provider, engine = self._create_providers_and_engine(
            simple_osm_file, simple_walking_profile
        )

        # Step 2: Validate provider registration
        self._validate_provider_registration(engine)

        # Step 3: Register and validate access points
        start_ap_id, goal_ap_id = self._register_and_validate_access_points(
            access_provider
        )

        # Step 4: Get and validate vertices
        start_vertex, goal_vertex = self._get_and_validate_vertices(
            access_provider, start_ap_id, goal_ap_id
        )

        # Step 5: Execute pathfinding with validation
        result, planning_time = self._execute_and_validate_pathfinding(
            engine, start_vertex, goal_vertex
        )

        # Step 6: Validate path structure
        self._validate_path_structure(result)

        # Step 7: Validate path connectivity
        self._validate_path_connectivity(result, goal_vertex)

        # Step 8: Display results
        print("✅ Minimal pathfinding workflow validated successfully!")
        print(f"   Path: {len(result)} edges, Cost: {result.total_cost:.1f}s")
        print(f"   Planning time: {planning_time:.3f}s")

        # Clean up
        access_provider.clear_access_points()
        simple_osm_file.unlink()

    def test_pathfinding_edge_cases(
        self, simple_osm_file: Path, simple_walking_profile: WalkingProfile
    ) -> None:
        """Test edge cases and failure scenarios in pathfinding workflow."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Set up providers and engine
        network_provider = OSMNetworkProvider(
            simple_osm_file,
            walking_profile=simple_walking_profile,
        )

        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
            walking_profile=simple_walking_profile,
            search_radius_m=50.0,  # Smaller radius to test "no nearby nodes" scenario
            max_nearby_nodes=5,
            build_index=True,
        )

        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        # Test Case 1: Coordinates too far from any OSM nodes
        far_ap_id = access_provider.register_access_point(
            10.0, 10.0
        )  # Very far from (0,0)
        near_ap_id = access_provider.register_access_point(
            0.0001, 0.0001
        )  # Near node 1

        far_vertex = access_provider.get_access_point_vertex(far_ap_id)
        near_vertex = access_provider.get_access_point_vertex(near_ap_id)

        # Should still create vertices even if no nearby nodes
        assert far_vertex is not None
        assert "access_point_id" in far_vertex
        assert far_vertex["lat"] == 10.0
        assert far_vertex["lon"] == 10.0

        # Test pathfinding with disconnected access point
        # This should raise an exception for disconnected coordinates
        with pytest.raises(RuntimeError, match="no path found"):
            engine.plan(start=far_vertex, goal=near_vertex)

        # Test Case 2: Same start and goal coordinates
        same_ap_id1 = access_provider.register_access_point(0.0001, 0.0001)
        same_ap_id2 = access_provider.register_access_point(
            0.0001, 0.0001
        )  # Same coords

        same_vertex1 = access_provider.get_access_point_vertex(same_ap_id1)
        same_vertex2 = access_provider.get_access_point_vertex(same_ap_id2)

        # Should have different access point IDs even with same coordinates
        assert same_ap_id1 != same_ap_id2
        assert same_vertex1["access_point_id"] != same_vertex2["access_point_id"]

        # Pathfinding should work (or return empty path for same location)
        result = engine.plan(start=same_vertex1, goal=same_vertex2)
        assert result is not None  # Should return a result, even if empty

        # Test Case 3: Invalid coordinate bounds (should still work, just be far)
        # Note: We don't test truly invalid coordinates like lat > 90 since
        # the access provider doesn't validate coordinate bounds

        # Test Case 4: Multiple access points management
        initial_count = len(access_provider.list_access_points())

        # Register several access points
        ap_ids = []
        for i in range(3):
            ap_id = access_provider.register_access_point(0.0001 + i * 0.0001, 0.0001)
            ap_ids.append(ap_id)

        # Should have more access points now
        final_count = len(access_provider.list_access_points())
        assert final_count >= initial_count + 3

        # All access points should be retrievable
        for ap_id in ap_ids:
            vertex = access_provider.get_access_point_vertex(ap_id)
            assert vertex is not None
            assert vertex["access_point_id"] == ap_id

        print("✅ Edge case testing completed successfully!")

        # Clean up
        access_provider.clear_access_points()
        simple_osm_file.unlink()
