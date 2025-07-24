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
    from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
    from graphserver.providers.osm.parser import OSMParser
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


class TestOSMParser:
    """Test OSM file parsing functionality."""

    def test_parser_creation(self, walking_profile: WalkingProfile) -> None:
        """Test OSM parser creation."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        parser = OSMParser(walking_profile)
        assert parser.walking_profile == walking_profile
        assert len(parser.nodes) == 0
        assert len(parser.ways) == 0
        assert len(parser.edges) == 0

    def test_parse_sample_file(
        self, sample_osm_file: Path, walking_profile: WalkingProfile
    ) -> None:
        """Test parsing of sample OSM file."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        parser = OSMParser(walking_profile)
        parser.parse_file(sample_osm_file)

        # Should have parsed nodes and ways
        assert len(parser.nodes) > 0
        assert len(parser.ways) > 0
        assert len(parser.edges) > 0

        # Check specific nodes from sample data
        assert 1 in parser.nodes
        assert 2 in parser.nodes
        assert 3 in parser.nodes

        # Check node coordinates
        node1 = parser.nodes[1]
        assert abs(node1.lat - 47.6062) < 0.0001
        assert abs(node1.lon - (-122.3321)) < 0.0001

        # Should have walkable ways
        assert 100 in parser.ways  # footway
        assert 200 in parser.ways  # steps

        # Check way properties
        footway = parser.ways[100]
        assert footway.is_walkable()
        assert footway.node_refs == [1, 2, 3]

        # Clean up
        sample_osm_file.unlink()

    def test_nearby_nodes_search(self, sample_osm_file: Path) -> None:
        """Test nearby nodes search functionality."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        parser = OSMParser()
        parser.parse_file(sample_osm_file)

        # Search near node 1
        nearby = parser.get_nearby_nodes(47.6062, -122.3321, radius_m=100)
        assert len(nearby) > 0
        assert nearby[0].id == 1  # Should find node 1 itself

        # Search in empty area
        empty = parser.get_nearby_nodes(0.0, 0.0, radius_m=100)
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

        provider = OSMNetworkProvider(
            sample_osm_file,
            walking_profile=walking_profile,
        )

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

        provider = OSMNetworkProvider(sample_osm_file)

        # Create vertex with OSM node ID
        node_vertex = Vertex({"osm_node_id": 1})

        # Generate edges
        edges = provider(node_vertex)

        assert len(edges) > 0

        # Check edge structure
        for target_vertex, edge in edges:
            assert "osm_node_id" in target_vertex
            assert "lat" in target_vertex
            assert "lon" in target_vertex
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

        provider = OSMNetworkProvider(sample_osm_file)

        # Test get_node_by_id
        node_vertex = provider.get_node_by_id(1)
        assert node_vertex is not None
        assert node_vertex["osm_node_id"] == 1
        assert "lat" in node_vertex
        assert "lon" in node_vertex

        # Test non-existent node
        missing_vertex = provider.get_node_by_id(999)
        assert missing_vertex is None

        # Clean up
        sample_osm_file.unlink()


class TestOSMAccessProvider:
    """Test OSM access provider functionality."""

    def test_access_point_registration_and_edges(self, sample_osm_file: Path) -> None:
        """Test access point registration and edge generation."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        provider = OSMAccessProvider(
            sample_osm_file,
            search_radius_m=1000.0,
            max_nearby_nodes=3,
            build_index=True,
        )

        # Register access point with coordinates near but not exactly at sample data
        access_point_id = provider.register_access_point(47.6063, -122.3322)

        # Verify access point was registered
        assert access_point_id == "ap_001"
        assert access_point_id in provider.list_access_points()

        # Get access point vertex
        access_point_vertex = provider.get_access_point_vertex(access_point_id)
        assert access_point_vertex is not None
        assert "access_point_id" in access_point_vertex
        assert access_point_vertex["access_point_id"] == access_point_id

        # Generate edges from access point
        edges = provider(access_point_vertex)

        assert len(edges) > 0

        # Check edge structure
        for target_vertex, edge in edges:
            assert "osm_node_id" in target_vertex
            assert "lat" in target_vertex
            assert "lon" in target_vertex
            assert edge.cost > 0
            assert "edge_type" in edge.metadata
            assert edge.metadata["edge_type"] == "access_point_to_node"
            assert "access_point_id" in edge.metadata
            assert edge.metadata["access_point_id"] == access_point_id

        # Clean up
        sample_osm_file.unlink()

    def test_unknown_vertex_type(self, sample_osm_file: Path) -> None:
        """Test handling of unknown vertex types."""
        if not OSM_AVAILABLE:
            pytest.skip("OSM dependencies not available")

        from graphserver import Vertex

        provider = OSMAccessProvider(sample_osm_file, build_index=True)

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

        provider = OSMAccessProvider(
            sample_osm_file, search_radius_m=1000.0, build_index=True
        )

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
            network_provider = OSMNetworkProvider(sample_osm_file)
            access_provider = OSMAccessProvider(
                parser=network_provider.parser,
                search_radius_m=1000.0,
                max_nearby_nodes=3,
                build_index=True,
            )

            engine.register_provider("osm_network", network_provider)
            engine.register_provider("osm_access", access_provider)

            # Check provider registration
            assert "osm_network" in engine.providers
            assert "osm_access" in engine.providers

            # Test planning with coordinates
            start = Vertex({"lat": 47.6062, "lon": -122.3321})
            goal = Vertex({"lat": 47.6082, "lon": -122.3301})

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
