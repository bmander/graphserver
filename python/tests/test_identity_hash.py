"""Test identity hash system for vertex matching."""

import pytest

from graphserver.providers.osm import OSMAccessProvider, OSMDataSource


def test_coordinate_identity_hash_matching():
    """Test that access provider generates consistent identity hashes for coordinates."""
    try:
        import tempfile
        from pathlib import Path

        # Create minimal OSM XML for testing
        minimal_osm = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="0.0" lon="0.0"/>
  <way id="100" version="1">
    <nd ref="1"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""

        # Create temporary OSM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(minimal_osm)
            f.flush()
            osm_file = Path(f.name)

        try:
            # Create data source and access provider
            data_source = OSMDataSource(osm_file, build_spatial_index=True)
            access_provider = OSMAccessProvider(data_source)

            # Test coordinate hash generation directly
            hash1 = access_provider._create_coordinate_identity_hash(0.000001, 0.000001)
            hash2 = access_provider._create_coordinate_identity_hash(0.000002, 0.000002)
            hash3 = access_provider._create_coordinate_identity_hash(0.001000, 0.001000)

            # Coordinates within ~1 meter should get the same hash (rounding to 5 decimal places)
            assert hash1 == hash2

            # Coordinates 1km apart should get different hashes
            assert hash1 != hash3

            print(f"Close coordinates hash: {hash1}")
            print(f"Distant coordinate hash: {hash3}")

        finally:
            osm_file.unlink()

    except ImportError:
        pytest.skip("OSM dependencies not available")


def test_osm_node_identity_hash():
    """Test that OSM providers generate consistent identity hashes for nodes."""
    try:
        import tempfile
        from pathlib import Path

        # Create minimal OSM XML for testing
        minimal_osm = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="0.0" lon="0.0"/>
  <way id="100" version="1">
    <nd ref="1"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""

        # Create temporary OSM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(minimal_osm)
            f.flush()
            osm_file = Path(f.name)

        try:
            # Create data source and access provider
            data_source = OSMDataSource(osm_file, build_spatial_index=True)
            access_provider = OSMAccessProvider(data_source)

            # Test OSM node hash generation via vertex creation
            node1_data = {"osm_node_id": 123, "lat": 47.6062, "lon": -122.3321}
            node2_data = {
                "osm_node_id": 123,
                "lat": 47.6062,
                "lon": -122.3321,
            }  # Same node
            node3_data = {
                "osm_node_id": 456,
                "lat": 47.6062,
                "lon": -122.3321,
            }  # Different node

            # Create vertices with identity hashes
            hash1 = access_provider._get_identity_hash(node1_data)
            hash2 = access_provider._get_identity_hash(node2_data)
            hash3 = access_provider._get_identity_hash(node3_data)

            # Same OSM node ID should get same hash
            assert hash1 == hash2

            # Different OSM node IDs should get different hashes
            assert hash1 != hash3

            print(f"Node 123 hash: {hash1}")
            print(f"Node 456 hash: {hash3}")

        finally:
            osm_file.unlink()

    except ImportError:
        pytest.skip("OSM dependencies not available")


def test_provider_generated_identity_hashes():
    """Test that providers generate identity hashes correctly."""
    # This test would need actual OSM data, so we'll skip it if not available
    try:
        import tempfile
        from pathlib import Path

        # Create minimal OSM XML for testing
        minimal_osm = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="0.0" lon="0.0"/>
  <way id="100" version="1">
    <nd ref="1"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""

        # Create temporary OSM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(minimal_osm)
            f.flush()
            osm_file = Path(f.name)

        try:
            # Create data source and access provider
            data_source = OSMDataSource(osm_file, build_spatial_index=True)
            access_provider = OSMAccessProvider(data_source)

            # Test the hash generation methods directly
            coord_hash = access_provider._create_coordinate_identity_hash(
                47.6062, -122.3321
            )
            assert coord_hash == "coord:47.6062,-122.3321"

            # Test generating identity hash for vertex data
            coord_data = {
                "lat": 47.606201,
                "lon": -122.332102,
            }  # Slightly different precision
            coord_identity_hash = access_provider._get_identity_hash(coord_data)
            expected_coord_hash = hash("coord:47.6062,-122.3321") & 0xFFFFFFFFFFFFFFFF
            assert (
                coord_identity_hash == expected_coord_hash
            )  # Should round to same value

            osm_data = {"osm_node_id": 12345, "lat": 47.6062, "lon": -122.3321}
            osm_identity_hash = access_provider._get_identity_hash(osm_data)
            expected_osm_hash = hash("osm:12345") & 0xFFFFFFFFFFFFFFFF
            assert osm_identity_hash == expected_osm_hash  # OSM node ID takes priority

            print(f"Coordinate hash: {coord_identity_hash}")
            print(f"OSM node hash (priority): {osm_identity_hash}")

        finally:
            osm_file.unlink()

    except ImportError:
        pytest.skip("OSM dependencies not available")


if __name__ == "__main__":
    test_coordinate_identity_hash_matching()
    test_osm_node_identity_hash()
    test_provider_generated_identity_hashes()
    print("✅ All identity hash tests passed!")
