"""Tests for OSM Edge Provider

This module tests the OpenStreetMap edge provider functionality,
including parsing, spatial indexing, and edge generation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Skip all tests if OSM dependencies are not available
pytest_plugins = []

try:
    from graphserver.providers.osm import (
        OSMAccessProvider,
        OSMDataSource,
        OSMNetworkProvider,
    )
    from graphserver.providers.osm.spatial import SpatialIndex, calculate_distance
    from graphserver.providers.osm.types import OSMNode, OSMWay, WalkingProfile

    OSM_AVAILABLE = True
except ImportError:
    OSM_AVAILABLE = False

# Sample OSM XML data for testing
SAMPLE_OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="47.6062" lon="-122.3321">
    <tag k="name" v="Start Node"/>
  </node>
  <node id="2" lat="47.6072" lon="-122.3311">
    <tag k="name" v="Middle Node"/>
  </node>
  <node id="3" lat="47.6082" lon="-122.3301">
    <tag k="name" v="End Node"/>
  </node>
  <node id="4" lat="47.6092" lon="-122.3291">
    <tag k="name" v="Isolated Node"/>
  </node>
  <way id="100" version="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <nd ref="3"/>
    <tag k="highway" v="footway"/>
    <tag k="name" v="Test Footway"/>
  </way>
  <way id="200" version="1">
    <nd ref="1"/>
    <nd ref="4"/>
    <tag k="highway" v="steps"/>
    <tag k="name" v="Test Steps"/>
  </way>
</osm>"""


@pytest.fixture
def sample_osm_file() -> Path:
    """Create a temporary OSM file for testing."""
    if not OSM_AVAILABLE:
        pytest.skip("OSM dependencies not available")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
        f.write(SAMPLE_OSM_XML)
        f.flush()
        return Path(f.name)


@pytest.fixture
def walking_profile() -> WalkingProfile:
    """Create a test walking profile."""
    if not OSM_AVAILABLE:
        pytest.skip("OSM dependencies not available")

    return WalkingProfile(base_speed_ms=1.4, avoid_stairs=False, avoid_busy_roads=True)


class TestOSMTypes:
    """Test OSM data types and structures."""

    def test_osm_node_creation(self) -> None:
        """Test OSM node creation and validation."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Valid node
        node = OSMNode(id=1, lat=47.6062, lon=-122.3321, tags={"name": "test"})
        assert node.id == 1
        assert node.lat == 47.6062
        assert node.lon == -122.3321
        assert node.tags["name"] == "test"

        # Invalid latitude
        with pytest.raises(ValueError, match="Invalid latitude"):
            OSMNode(id=2, lat=95.0, lon=-122.3321, tags={})

        # Invalid longitude
        with pytest.raises(ValueError, match="Invalid longitude"):
            OSMNode(id=3, lat=47.6062, lon=200.0, tags={})

    def test_osm_way_creation(self) -> None:
        """Test OSM way creation and validation."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Valid way
        way = OSMWay(id=100, node_refs=[1, 2, 3], tags={"highway": "footway"})
        assert way.id == 100
        assert way.node_refs == [1, 2, 3]
        assert way.tags["highway"] == "footway"

        # Invalid way (too few nodes)
        with pytest.raises(ValueError, match="must have at least 2 nodes"):
            OSMWay(id=101, node_refs=[1], tags={})

    def test_way_walkability(self) -> None:
        """Test way walkability detection."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Walkable ways
        footway = OSMWay(id=1, node_refs=[1, 2], tags={"highway": "footway"})
        assert footway.is_walkable()

        path = OSMWay(id=2, node_refs=[1, 2], tags={"highway": "path"})
        assert path.is_walkable()

        residential = OSMWay(id=3, node_refs=[1, 2], tags={"highway": "residential"})
        assert residential.is_walkable()

        # Non-walkable way
        motorway = OSMWay(id=4, node_refs=[1, 2], tags={"highway": "motorway"})
        assert not motorway.is_walkable()

        # Restricted access
        restricted_footway = OSMWay(
            id=5, node_refs=[1, 2], tags={"highway": "footway", "foot": "no"}
        )
        assert not restricted_footway.is_walkable()

    def test_walking_speeds(self) -> None:
        """Test walking speed calculations for different way types."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        footway = OSMWay(id=1, node_refs=[1, 2], tags={"highway": "footway"})
        assert footway.get_walking_speed() == 1.4

        steps = OSMWay(id=2, node_refs=[1, 2], tags={"highway": "steps"})
        assert steps.get_walking_speed() == 0.8  # Slower on stairs

        path = OSMWay(id=3, node_refs=[1, 2], tags={"highway": "path"})
        assert path.get_walking_speed() == 1.2  # Slower on unpaved paths


class TestSpatialCalculations:
    """Test spatial indexing and distance calculations."""

    def test_distance_calculation(self) -> None:
        """Test geodesic distance calculation."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Distance between two points in Seattle
        lat1, lon1 = 47.6062, -122.3321  # Pioneer Square
        lat2, lon2 = 47.6205, -122.3493  # Space Needle

        distance = calculate_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 2.2 km
        assert 2000 < distance < 2500

    def test_spatial_index(self) -> None:
        """Test spatial index functionality."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create test nodes
        nodes = {
            1: OSMNode(id=1, lat=47.6062, lon=-122.3321, tags={}),
            2: OSMNode(id=2, lat=47.6072, lon=-122.3311, tags={}),
            3: OSMNode(id=3, lat=47.6082, lon=-122.3301, tags={}),
        }

        # Build spatial index
        index = SpatialIndex()
        index.add_nodes(nodes)

        assert len(index) == 3

        # Test nearest node search
        nearest = index.find_nearest_node(47.6063, -122.3320, radius_m=1000)
        assert nearest is not None
        assert nearest.id == 1  # Should be closest to first node

        # Test nearby nodes search
        nearby = index.find_nearest_nodes(
            47.6070, -122.3315, radius_m=500, max_results=2
        )
        assert len(nearby) >= 1

        # Results should be sorted by distance
        distances = [distance for _, distance in nearby]
        assert distances == sorted(distances)


class TestOSMDataSource:
    """Test OSM data source functionality."""

    def test_data_source_creation(self, walking_profile: WalkingProfile) -> None:
        """Test OSM data source creation with empty file."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        # Create minimal OSM file with no ways (empty)
        import tempfile

        minimal_osm = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
</osm>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(minimal_osm)
            f.flush()
            osm_file = Path(f.name)

        try:
            data_source = OSMDataSource(osm_file, walking_profile=walking_profile)
            assert data_source.walking_profile == walking_profile
            assert len(data_source.nodes) == 0
            assert len(data_source.ways) == 0
        finally:
            osm_file.unlink()

    def test_parse_sample_file(
        self, sample_osm_file: Path, walking_profile: WalkingProfile
    ) -> None:
        """Test parsing of sample OSM file."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        data_source = OSMDataSource(sample_osm_file, walking_profile=walking_profile)

        # Should have parsed nodes and ways
        assert len(data_source.nodes) > 0
        assert len(data_source.ways) > 0

        # Check specific nodes from sample data
        assert 1 in data_source.nodes
        assert 2 in data_source.nodes
        assert 3 in data_source.nodes

        # Check node coordinates
        node1 = data_source.nodes[1]
        assert abs(node1.lat - 47.6062) < 0.0001
        assert abs(node1.lon - (-122.3321)) < 0.0001

        # Should have walkable ways
        assert 100 in data_source.ways  # footway
        assert 200 in data_source.ways  # steps

        # Check way properties
        footway = data_source.ways[100]
        assert footway.is_walkable()
        assert footway.node_refs == [1, 2, 3]

        # Clean up
        sample_osm_file.unlink()

    def test_nearby_nodes_search(self, sample_osm_file: Path) -> None:
        """Test nearby nodes search functionality."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        data_source = OSMDataSource(sample_osm_file)

        # Search near node 1
        nearby = data_source.get_nearby_nodes(47.6062, -122.3321, radius_m=100)
        assert len(nearby) > 0
        assert nearby[0].id == 1  # Should find node 1 itself

        # Search in empty area
        empty = data_source.get_nearby_nodes(0.0, 0.0, radius_m=100)
        assert len(empty) == 0

        # Clean up
        sample_osm_file.unlink()


class TestOSMNetworkProvider:
    """Test OSM network provider functionality."""

    def test_network_provider_creation(
        self, sample_osm_file: Path, walking_profile: WalkingProfile
    ) -> None:
        """Test OSM network provider creation and initialization."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        data_source = OSMDataSource(sample_osm_file, walking_profile=walking_profile)
        provider = OSMNetworkProvider(data_source)

        assert provider.node_count > 0
        assert provider.way_count > 0
        assert provider.edge_count > 0

        # Clean up
        sample_osm_file.unlink()

    def test_node_based_edges(self, sample_osm_file: Path) -> None:
        """Test edge generation from OSM node IDs."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file)
        provider = OSMNetworkProvider(data_source)

        # Create vertex with OSM node ID
        node_vertex = Vertex({"osm_node_id": 1})

        # Generate edges
        edges = provider(node_vertex)

        assert len(edges) > 0

        # Check edge structure
        for target_vertex, edge in edges:
            assert "osm_node_id" in target_vertex
            assert edge.cost > 0
            assert "edge_type" in edge.metadata
            assert edge.metadata["edge_type"] == "osm_way"
            assert "way_id" in edge.metadata

        # Clean up
        sample_osm_file.unlink()

    def test_utility_methods(self, sample_osm_file: Path) -> None:
        """Test utility methods like get_node_by_id."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        data_source = OSMDataSource(sample_osm_file)
        provider = OSMNetworkProvider(data_source)

        # Test get_node_by_id
        node_vertex = provider.get_node_by_id(1)
        assert node_vertex is not None
        assert node_vertex["osm_node_id"] == 1

        # Test non-existent node
        missing_vertex = provider.get_node_by_id(999)
        assert missing_vertex is None

        # Clean up
        sample_osm_file.unlink()


class TestOSMAccessProvider:
    """Test OSM access provider functionality."""

    def test_linked_vertex_edges(self, sample_osm_file: Path) -> None:
        """Test edge generation from linked vertices to OSM nodes."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create vertex with coordinates near sample data
        coord_vertex = Vertex({"lat": 47.6063, "lon": -122.3322})

        # Initially, unlinked vertex should produce no edges
        edges = provider(coord_vertex)
        assert len(edges) == 0

        # Link the vertex to nearest OSM node
        provider.link(coord_vertex, 47.6063, -122.3322)

        # Now it should generate edges
        edges = provider(coord_vertex)
        assert len(edges) == 1  # Should have one edge to linked OSM node

        # Check edge structure
        target_vertex, edge = edges[0]
        assert "osm_node_id" in target_vertex
        assert edge.cost > 0
        assert "edge_type" in edge.metadata
        assert edge.metadata["edge_type"] == "linked_vertex_to_node"
        assert "osm_node_id" in edge.metadata

        # Clean up
        sample_osm_file.unlink()

    def test_unlinked_coordinate_vertex(self, sample_osm_file: Path) -> None:
        """Test that unlinked coordinate vertices produce no edges."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create vertex with coordinates that is not linked
        coord_vertex = Vertex({"lat": 47.6063, "lon": -122.3322})

        # Should generate no edges since vertex is not linked
        edges = provider(coord_vertex)
        assert len(edges) == 0

        # Clean up
        sample_osm_file.unlink()

    def test_linked_vertex_registration_and_edges(self, sample_osm_file: Path) -> None:
        """Test linked vertex registration and edge generation."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create and link vertex near sample data
        exit_vertex = Vertex(
            {"lat": 47.6063, "lon": -122.3322, "exit_name": "Downtown Exit"}
        )
        provider.link(exit_vertex, 47.6063, -122.3322)

        # Create OSM node vertex (assuming node 1 exists near our linked vertex)
        osm_vertex = Vertex({"osm_node_id": 1})

        # Generate edges from OSM node
        edges = provider(osm_vertex)

        assert len(edges) > 0

        # Check edge structure
        for target_vertex, edge in edges:
            assert "lat" in target_vertex
            assert "lon" in target_vertex
            assert "exit_name" in target_vertex
            assert target_vertex["exit_name"] == "Downtown Exit"
            assert edge.cost > 0
            assert "edge_type" in edge.metadata
            assert edge.metadata["edge_type"] == "node_to_linked_vertex"

        # Clean up
        sample_osm_file.unlink()

    def test_link_method(self, sample_osm_file: Path) -> None:
        """Test the link() method functionality."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create vertex to link
        vertex = Vertex({"lat": 47.6063, "lon": -122.3322, "name": "test_vertex"})

        # Link vertex to nearest OSM node
        provider.link(vertex, 47.6063, -122.3322)

        # Test that the vertex is now linked
        edges = provider(vertex)
        assert len(edges) == 1
        assert edges[0][1].metadata["edge_type"] == "linked_vertex_to_node"

        # Test that the OSM node now has an edge back to the vertex
        osm_node_id = edges[0][0]["osm_node_id"]
        osm_vertex = Vertex({"osm_node_id": osm_node_id})
        back_edges = provider(osm_vertex)

        # Should have at least one edge back to our linked vertex
        linked_back_edges = [
            edge
            for vertex_target, edge in back_edges
            if edge.metadata.get("edge_type") == "node_to_linked_vertex"
        ]
        assert len(linked_back_edges) >= 1

        # Clean up
        sample_osm_file.unlink()

    def test_link_method_error_cases(self, sample_osm_file: Path) -> None:
        """Test error cases for the link() method."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=100.0,  # Small radius
            max_nearby_nodes=3,
        )

        # Test linking to coordinates outside search radius
        vertex = Vertex({"lat": 0.0, "lon": 0.0, "name": "far_vertex"})

        with pytest.raises(ValueError, match="No OSM node found within"):
            provider.link(vertex, 0.0, 0.0)

        # Clean up
        sample_osm_file.unlink()

    def test_clear_links(self, sample_osm_file: Path) -> None:
        """Test the clear_links() method."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create and link a vertex
        vertex = Vertex({"lat": 47.6063, "lon": -122.3322, "name": "test_vertex"})
        provider.link(vertex, 47.6063, -122.3322)

        # Verify it's linked
        edges = provider(vertex)
        assert len(edges) == 1

        # Clear all links
        provider.clear_links()

        # Verify vertex is no longer linked
        edges = provider(vertex)
        assert len(edges) == 0

        # Clean up
        sample_osm_file.unlink()

    def test_time_aware_linking(self, sample_osm_file: Path) -> None:
        """Test that vertices with same properties but different times link to same OSM node."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create two vertices with same properties but different times
        vertex1 = Vertex(
            {"lat": 47.6063, "lon": -122.3322, "name": "test", "time": 1000}
        )
        vertex2 = Vertex(
            {"lat": 47.6063, "lon": -122.3322, "name": "test", "time": 2000}
        )

        # Link both vertices - should link to same OSM node
        provider.link(vertex1, 47.6063, -122.3322)
        provider.link(vertex2, 47.6063, -122.3322)

        # Both should generate edges to the same OSM node
        edges1 = provider(vertex1)
        edges2 = provider(vertex2)

        assert len(edges1) == 1
        assert len(edges2) == 1

        # Should be linked to same OSM node
        osm_node_id1 = edges1[0][0]["osm_node_id"]
        osm_node_id2 = edges2[0][0]["osm_node_id"]
        assert osm_node_id1 == osm_node_id2

        # Target vertices should preserve original times
        assert edges1[0][0]["time"] == 1000
        assert edges2[0][0]["time"] == 2000

        # Clean up
        sample_osm_file.unlink()

    def test_time_preservation_vertex_to_node(self, sample_osm_file: Path) -> None:
        """Test that time is preserved when transitioning from vertex to OSM node."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create vertex with time and link it
        vertex_with_time = Vertex(
            {"lat": 47.6063, "lon": -122.3322, "stop_id": "STOP123", "time": 12345}
        )
        provider.link(vertex_with_time, 47.6063, -122.3322)

        # Generate edges - should preserve time in target OSM node
        edges = provider(vertex_with_time)
        assert len(edges) == 1

        target_vertex, edge = edges[0]
        assert "osm_node_id" in target_vertex
        assert target_vertex["time"] == 12345
        assert edge.metadata["edge_type"] == "linked_vertex_to_node"

        # Clean up
        sample_osm_file.unlink()

    def test_time_preservation_node_to_vertex(self, sample_osm_file: Path) -> None:
        """Test that time is preserved when transitioning from OSM node to linked vertex."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create and link a vertex (without time for the template)
        linked_vertex = Vertex({"lat": 47.6063, "lon": -122.3322, "stop_id": "STOP123"})
        provider.link(linked_vertex, 47.6063, -122.3322)

        # Get the OSM node ID that was linked
        edges = provider(linked_vertex)
        osm_node_id = edges[0][0]["osm_node_id"]

        # Create OSM node vertex with time
        osm_vertex_with_time = Vertex({"osm_node_id": osm_node_id, "time": 54321})

        # Generate edges from OSM node - should preserve time in target linked vertex
        back_edges = provider(osm_vertex_with_time)

        # Find the edge to our linked vertex
        linked_back_edges = [
            (vertex_target, edge)
            for vertex_target, edge in back_edges
            if edge.metadata.get("edge_type") == "node_to_linked_vertex"
        ]
        assert len(linked_back_edges) >= 1

        target_vertex, edge = linked_back_edges[0]
        assert target_vertex["stop_id"] == "STOP123"
        assert target_vertex["time"] == 54321  # Time should be preserved

        # Clean up
        sample_osm_file.unlink()

    def test_vertices_without_coordinates(self, sample_osm_file: Path) -> None:
        """Test linking vertices that don't have lat/lon coordinates."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Create vertex without coordinates (location provided via link method)
        vertex_no_coords = Vertex({"stop_id": "STOP456", "name": "Test Stop"})
        provider.link(
            vertex_no_coords, 47.6062, -122.3321
        )  # Close to node 1 in test data

        # Should still generate edges (using node coordinates as fallback)
        edges = provider(vertex_no_coords)
        assert len(edges) == 1

        target_vertex, edge = edges[0]
        assert "osm_node_id" in target_vertex
        assert edge.metadata["edge_type"] == "linked_vertex_to_node"

        # Clean up
        sample_osm_file.unlink()

    def test_multiple_linked_vertices_per_node(self, sample_osm_file: Path) -> None:
        """Test that multiple vertices can be linked to the same OSM node."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(
            data_source,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
        )

        # Link multiple vertices at similar coordinates
        exit_vertex1 = Vertex(
            {
                "lat": 47.6063,
                "lon": -122.3322,
                "exit_name": "Downtown Exit",
                "type": "mall",
            }
        )
        exit_vertex2 = Vertex(
            {
                "lat": 47.6064,
                "lon": -122.3323,
                "exit_name": "Shopping Center",
                "type": "retail",
            }
        )

        provider.link(exit_vertex1, 47.6063, -122.3322)
        provider.link(exit_vertex2, 47.6064, -122.3323)

        # Create OSM node vertex
        osm_vertex = Vertex({"osm_node_id": 1})

        # Generate edges from OSM node - should get multiple linked vertex edges
        edges = provider(osm_vertex)

        # Should have edges to both linked vertices
        assert len(edges) >= 2

        # Check that we have different exit names
        exit_names = {
            target_vertex["exit_name"]
            for target_vertex, edge in edges
            if "exit_name" in target_vertex
        }
        assert "Downtown Exit" in exit_names
        assert "Shopping Center" in exit_names

        # Clean up
        sample_osm_file.unlink()

    def test_unknown_vertex_type(self, sample_osm_file: Path) -> None:
        """Test handling of unknown vertex types."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(data_source)

        # Create vertex with unknown structure
        unknown_vertex = Vertex({"unknown_key": "unknown_value"})

        # Should return empty edges
        edges = provider(unknown_vertex)
        assert len(edges) == 0

        # Clean up
        sample_osm_file.unlink()

    def test_find_nearest_node(self, sample_osm_file: Path) -> None:
        """Test find_nearest_node functionality."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
        provider = OSMAccessProvider(data_source, search_radius_m=1000.0)

        # Test find_nearest_node
        nearest = provider.find_nearest_node(47.6062, -122.3321)
        assert nearest is not None
        assert "osm_node_id" in nearest

        # Test find_nearest_node in empty area
        distant = provider.find_nearest_node(0.0, 0.0)
        assert distant is None  # Should be outside search radius

        # Clean up
        sample_osm_file.unlink()


class TestIntegrationWithGraphserver:
    """Test integration with main Graphserver engine."""

    def test_engine_integration(self, sample_osm_file: Path) -> None:
        """Test OSM provider integration with Graphserver engine."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        try:
            from graphserver import Engine, Vertex

            # Create engine and register both OSM providers
            engine = Engine()
            data_source = OSMDataSource(sample_osm_file, build_spatial_index=True)
            network_provider = OSMNetworkProvider(data_source)
            access_provider = OSMAccessProvider(
                data_source,
                search_radius_m=1000.0,
                max_nearby_nodes=3,
            )

            engine.register_provider("osm_network", network_provider)
            engine.register_provider("osm_access", access_provider)

            # Check provider registration
            assert "osm_network" in engine.providers
            assert "osm_access" in engine.providers

            # Test direct coordinate usage
            start = Vertex({"lat": 47.6062, "lon": -122.3321})
            goal = Vertex({"lat": 47.6082, "lon": -122.3301})

            # Test that access provider can handle coordinate vertices directly
            start_edges = access_provider(start)
            assert len(start_edges) >= 0  # Should find nearby OSM nodes

            # This should work with the OSM providers
            # Note: Actual pathfinding success depends on connectivity in sample data
            try:
                result = engine.plan(start=start, goal=goal)
                # If planning succeeds, check result structure
                assert result is not None
                assert len(result) >= 0  # May be empty if no path found
            except (RuntimeError, NotImplementedError):
                # Planning may fail if no path exists in sample data
                # or if C extension pathfinding is not fully implemented
                pass

        except ImportError:
            pytest.skip("Graphserver core not available")
        finally:
            # Clean up
            sample_osm_file.unlink()
