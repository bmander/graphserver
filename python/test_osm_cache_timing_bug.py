#!/usr/bin/env python3
"""Test demonstrating the OSM cache timing bug.

This test shows that when an OSM node is expanded and cached BEFORE
vertices are linked to it, the cached edges don't include the later-linked
vertices, causing routing failures.
"""

import tempfile
from pathlib import Path

try:
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import OSMAccessProvider, OSMDataSource, OSMNetworkProvider
    from graphserver.providers.osm.types import WalkingProfile
    
    # Simple OSM XML with two connected nodes
    TEST_OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="47.6062" lon="-122.3321"/>
  <node id="2" lat="47.6072" lon="-122.3311"/>
  <way id="100" version="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""

    def test_cache_timing_bug():
        """Demonstrate the cache timing bug."""
        
        # Create temporary OSM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
            f.write(TEST_OSM_XML)
            f.flush()
            osm_file = Path(f.name)
        
        try:
            # Create data source and providers
            walking_profile = WalkingProfile(base_speed_ms=1.4)
            data_source = OSMDataSource(osm_file, walking_profile=walking_profile)
            
            network_provider = OSMNetworkProvider(data_source)
            access_provider = OSMAccessProvider(data_source, search_radius_m=200.0)
            
            # Create engine with caching enabled
            engine = Engine(enable_edge_caching=True)
            engine.register_provider("network", network_provider)
            engine.register_provider("access", access_provider)
            
            print(f"Cache enabled: {engine.cache_enabled}")
            
            # Get OSM nodes with proper identity hashes
            # We need to create them the same way the providers would
            def make_osm_vertex(node_id):
                data = {"osm_node_id": node_id}
                # Calculate identity hash the same way providers do
                hash_str = f"osm:{node_id}"
                identity_hash = hash(hash_str) & 0xFFFFFFFFFFFFFFFF
                return Vertex(data, hash_value=identity_hash)
            
            osm_node_1 = make_osm_vertex(1)
            osm_node_2 = make_osm_vertex(2)
            
            # CRITICAL: Expand OSM node 1 BEFORE linking any vertices
            # This populates the cache with edges that don't include access vertices
            print("\n1. Expanding OSM node 1 (before linking any vertices)...")
            # Do a pathfinding query to populate the cache
            try:
                engine.plan(start=osm_node_1, goal=osm_node_2)
                print("   Pathfinding query completed - cache populated")
            except RuntimeError:
                print("   Pathfinding failed, but cache may still be populated")
            
            # Now link an access vertex to OSM node 1
            print("\n2. Linking access vertex to OSM node 1...")
            access_vertex = Vertex({"id": "ACCESS", "type": "offramp"})
            access_provider.link(access_vertex, 47.6062, -122.3321)  # Same coords as node 1
            
            # Check what edges the provider would generate now
            print("\n3. Checking provider-generated edges (bypassing cache)...")
            provider_edges = access_provider.out_edges(osm_node_1)
            print(f"   Provider edges from node 1: {len(provider_edges)}")
            for i, (target, edge) in enumerate(provider_edges):
                print(f"     Edge {i}: to {target}")
            
            # The engine will use cached edges which don't include the access vertex
            print("\n4. Engine will use cached edges (which don't include access vertex)...")
            
            # Try to find a path from OSM node 1 to the access vertex
            print("\n5. Attempting to find path from OSM node 1 to access vertex...")
            path = engine.plan(start=osm_node_1, goal=access_vertex)
            
            if path:
                print(f"   SUCCESS: Found path with {len(path)} edges")
            else:
                print("   FAILURE: No path found (cache timing bug!)")
                print("   The cached edges don't include the access vertex!")
            
            # Clear cache and try again
            print("\n6. Clearing cache and trying again...")
            engine.clear_cache()
            
            path_after_clear = engine.plan(start=osm_node_1, goal=access_vertex)
            if path_after_clear:
                print(f"   SUCCESS: Found path with {len(path_after_clear)} edges after clearing cache")
            else:
                print("   FAILURE: Still no path found")
            
            return path is not None
            
        finally:
            # Clean up
            osm_file.unlink()
    
    if __name__ == "__main__":
        print("Testing OSM cache timing bug...")
        print("=" * 60)
        success = test_cache_timing_bug()
        print("=" * 60)
        print(f"Test {'PASSED' if success else 'FAILED - Cache timing bug detected!'}")

except ImportError as e:
    print(f"OSM dependencies not available: {e}")