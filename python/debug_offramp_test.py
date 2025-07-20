#!/usr/bin/env python3
"""Debug test to inspect offramp generation in detail"""

import tempfile
from pathlib import Path

from graphserver import Engine, Vertex
from graphserver.providers.osm import OSMNetworkProvider, OSMAccessProvider
from graphserver.providers.osm.types import WalkingProfile

# Simple OSM data: single road from (0,0) to (0,0.001)
SIMPLE_OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="debug">
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
    <tag k="name" v="Test Road"/>
  </way>
</osm>"""

def debug_offramp_generation():
    print("🔍 Debug: Offramp Generation Detailed Analysis")
    print("=" * 60)

    # Create temporary OSM file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
        f.write(SIMPLE_OSM_XML)
        f.flush()
        osm_file = Path(f.name)

    try:
        # Create providers
        walking_profile = WalkingProfile(base_speed_ms=1.0)
        
        network_provider = OSMNetworkProvider(osm_file, walking_profile=walking_profile)
        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
            walking_profile=walking_profile,
            search_radius_m=1000.0,
            max_nearby_nodes=5,
            build_index=True,
        )

        # Set up goal coordinate manually
        goal_lat, goal_lon = 0.0001, 0.0011
        print(f"Setting goal coordinate: ({goal_lat}, {goal_lon})")
        access_provider.set_target_coordinate(goal_lat, goal_lon)
        
        print(f"Stored target coordinates: {access_provider._target_coordinates}")

        # Test offramps from each OSM node
        for node_id in [1, 2]:
            print(f"\n--- Testing offramps from OSM Node {node_id} ---")
            
            osm_vertex = Vertex({"osm_node_id": node_id})
            offramps = access_provider(osm_vertex)
            
            print(f"Generated {len(offramps)} offramps")
            
            for i, (target_vertex, edge) in enumerate(offramps):
                print(f"  Offramp {i+1}:")
                print(f"    Target vertex keys: {list(target_vertex.keys())}")
                print(f"    Target coordinates: ({target_vertex.get('lat', 'N/A')}, {target_vertex.get('lon', 'N/A')})")
                print(f"    Target identity hash: {target_vertex.get('_id_hash', 'MISSING')}")
                print(f"    Edge cost: {edge.cost}")
                print(f"    Edge distance: {edge.metadata.get('distance_m', 'N/A')}m")
                
                # Check if this target matches our goal
                expected_goal_hash = f"coord:{round(goal_lat, 5)},{round(goal_lon, 5)}"
                target_hash = target_vertex.get('_id_hash', '')
                is_match = target_hash == expected_goal_hash
                print(f"    Matches goal hash? {is_match} (expected: {expected_goal_hash})")

        # Test what happens when we add the goal vertex identity hash manually
        print(f"\n--- Manual Goal Hash Test ---")
        engine = Engine()
        goal_vertex = Vertex({"lat": goal_lat, "lon": goal_lon})
        goal_with_hash = engine._add_identity_hash_to_vertex(goal_vertex)
        print(f"Goal vertex with hash: {goal_with_hash.get('_id_hash', 'MISSING')}")

    finally:
        osm_file.unlink()

if __name__ == "__main__":
    debug_offramp_generation()