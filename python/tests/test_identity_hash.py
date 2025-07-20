"""Test identity hash system for vertex matching."""

import pytest

from graphserver import Engine, Vertex
from graphserver.providers.osm import OSMAccessProvider


def test_coordinate_identity_hash_matching():
    """Test that nearby coordinates get the same identity hash."""
    engine = Engine()

    # Test coordinate vertices with small differences
    coord1 = Vertex({"lat": 0.000001, "lon": 0.000001})  # Very close to origin
    coord2 = Vertex({"lat": 0.000002, "lon": 0.000002})  # Also very close to origin
    coord3 = Vertex({"lat": 0.001000, "lon": 0.001000})  # 1km away

    # Add identity hashes
    coord1_with_hash = engine._add_identity_hash_to_vertex(coord1)
    coord2_with_hash = engine._add_identity_hash_to_vertex(coord2)
    coord3_with_hash = engine._add_identity_hash_to_vertex(coord3)

    # Coordinates within ~1 meter should get the same hash (rounding to 5 decimal places)
    assert coord1_with_hash["_id_hash"] == coord2_with_hash["_id_hash"]

    # Coordinates 1km apart should get different hashes
    assert coord1_with_hash["_id_hash"] != coord3_with_hash["_id_hash"]

    print(f"Close coordinates hash: {coord1_with_hash['_id_hash']}")
    print(f"Distant coordinate hash: {coord3_with_hash['_id_hash']}")


def test_osm_node_identity_hash():
    """Test that OSM node vertices get consistent identity hashes."""
    engine = Engine()

    # Test OSM node vertices
    node1 = Vertex({"osm_node_id": 123, "lat": 47.6062, "lon": -122.3321})
    node2 = Vertex({"osm_node_id": 123, "lat": 47.6062, "lon": -122.3321})  # Same node
    node3 = Vertex(
        {"osm_node_id": 456, "lat": 47.6062, "lon": -122.3321}
    )  # Different node

    # Add identity hashes
    node1_with_hash = engine._add_identity_hash_to_vertex(node1)
    node2_with_hash = engine._add_identity_hash_to_vertex(node2)
    node3_with_hash = engine._add_identity_hash_to_vertex(node3)

    # Same OSM node ID should get same hash
    assert node1_with_hash["_id_hash"] == node2_with_hash["_id_hash"]

    # Different OSM node IDs should get different hashes
    assert node1_with_hash["_id_hash"] != node3_with_hash["_id_hash"]

    print(f"Node 123 hash: {node1_with_hash['_id_hash']}")
    print(f"Node 456 hash: {node3_with_hash['_id_hash']}")


def test_provider_generated_identity_hashes():
    """Test that providers generate identity hashes correctly."""
    # This test would need actual OSM data, so we'll skip it if not available
    try:
        from graphserver.providers.osm.parser import OSMParser
        from graphserver.providers.osm.types import WalkingProfile

        # Create a mock parser for testing (minimal setup)
        walking_profile = WalkingProfile()
        parser = OSMParser(walking_profile)
        parser.nodes = {}  # Empty for testing

        # Create a simple access provider with the mock parser
        access_provider = OSMAccessProvider(parser=parser)

        # Test the hash generation methods directly
        coord_hash = access_provider._create_coordinate_identity_hash(
            47.6062, -122.3321
        )
        assert coord_hash == "coord:47.6062,-122.3321"

        # Test adding identity hash to vertex data
        coord_data = {
            "lat": 47.606201,
            "lon": -122.332102,
        }  # Slightly different precision
        coord_with_hash = access_provider._add_identity_hash(coord_data)
        assert (
            coord_with_hash["_id_hash"] == "coord:47.6062,-122.3321"
        )  # Should round to same value

        osm_data = {"osm_node_id": 12345, "lat": 47.6062, "lon": -122.3321}
        osm_with_hash = access_provider._add_identity_hash(osm_data)
        assert osm_with_hash["_id_hash"] == "osm:12345"  # OSM node ID takes priority

        print(f"Coordinate hash: {coord_with_hash['_id_hash']}")
        print(f"OSM node hash (priority): {osm_with_hash['_id_hash']}")

    except ImportError:
        pytest.skip("OSM dependencies not available")


if __name__ == "__main__":
    test_coordinate_identity_hash_matching()
    test_osm_node_identity_hash()
    test_provider_generated_identity_hashes()
    print("✅ All identity hash tests passed!")
