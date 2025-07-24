#!/usr/bin/env python3
"""Debug test to inspect offramp generation in detail"""

import tempfile
from pathlib import Path

from graphserver import Engine
from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
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

        # Register access point and analyze the process
        goal_lat, goal_lon = 0.0001, 0.0011
        print(f"Registering access point at: ({goal_lat}, {goal_lon})")
        goal_ap_id = access_provider.register_access_point(goal_lat, goal_lon)
        goal_vertex = access_provider.get_access_point_vertex(goal_ap_id)

        print(f"Goal access point ID: {goal_ap_id}")
        print(f"Goal vertex: {goal_vertex}")

        # Register the engine with providers to enable routing
        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        # Test access from each OSM node by getting their offramps
        print("\n--- Testing access from OSM nodes ---")
        for node_id in [1, 2]:
            print(f"\n--- Node {node_id} Analysis ---")

            # Get the node's lat/lon from the network provider
            node_data = network_provider.parser.nodes.get(node_id)
            if node_data:
                node_lat, node_lon = node_data.lat, node_data.lon
                print(f"OSM Node {node_id} location: ({node_lat}, {node_lon})")

                # Register this as an access point too to test routing
                start_ap_id = access_provider.register_access_point(node_lat, node_lon)
                start_vertex = access_provider.get_access_point_vertex(start_ap_id)

                print(f"Start access point ID: {start_ap_id}")
                print(f"Start vertex: {start_vertex}")

                # Try to find a route
                try:
                    result = engine.plan(start=start_vertex, goal=goal_vertex)
                    print(f"✅ Route found with {len(result)} edges")
                    for i, path_edge in enumerate(result):
                        print(
                            f"  Edge {i + 1}: cost={path_edge.edge.cost}, metadata={path_edge.edge.metadata}"
                        )
                        print(f"    Target vertex: {path_edge.target}")
                except Exception as e:
                    print(f"❌ No route found: {e}")
            else:
                print(f"Node {node_id} not found in network")

    finally:
        osm_file.unlink()


if __name__ == "__main__":
    debug_offramp_generation()
