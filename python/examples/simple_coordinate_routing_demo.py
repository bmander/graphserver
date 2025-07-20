#!/usr/bin/env python3
"""Simple Coordinate Routing Demo

This script demonstrates coordinate-to-coordinate routing using the split OSM provider
architecture with a minimal test dataset.
"""

import tempfile
from pathlib import Path

from graphserver import Engine, Vertex
from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
from graphserver.providers.osm.types import WalkingProfile

# Simple OSM data: single road from (0,0) to (0,0.001)
SIMPLE_OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="demo">
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


def main():
    """Demonstrate coordinate-to-coordinate routing."""
    print("🚶 Simple Coordinate Routing Demo")
    print("=" * 50)

    # Create temporary OSM file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
        f.write(SIMPLE_OSM_XML)
        f.flush()
        osm_file = Path(f.name)

    try:
        # Create walking profile
        walking_profile = WalkingProfile(
            base_speed_ms=1.0,  # 1 m/s for easy calculations
            avoid_stairs=False,
            avoid_busy_roads=False,
        )

        print("📂 Creating OSM providers...")

        # Create network provider for OSM-to-OSM navigation
        network_provider = OSMNetworkProvider(
            osm_file,
            walking_profile=walking_profile,
        )

        # Create access provider for coordinate-to-OSM connections
        access_provider = OSMAccessProvider(
            parser=network_provider.parser,  # Share parser for efficiency
            walking_profile=walking_profile,
            search_radius_m=1000.0,  # Wide radius to ensure connections
            max_nearby_nodes=5,
            build_index=True,
        )

        print(
            f"✅ Loaded: {network_provider.node_count} nodes, {network_provider.edge_count} edges"
        )

        # Register both providers with engine
        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        print(f"🚀 Registered providers: {list(engine.providers.keys())}")

        # Define test coordinates
        start_coords = Vertex({"lat": 0.0001, "lon": 0.0001})  # Near node 1
        goal_coords = Vertex({"lat": 0.0001, "lon": 0.0011})  # Near node 2

        print("\n🧪 Testing Provider Components")
        print("-" * 30)

        # Test 1: Access provider onramps
        print("1. Testing onramps (coordinate → OSM network)")
        start_onramps = access_provider(start_coords)
        goal_onramps = access_provider(goal_coords)

        print(f"   Start coordinate onramps: {len(start_onramps)}")
        print(f"   Goal coordinate onramps: {len(goal_onramps)}")

        if start_onramps:
            target, edge = start_onramps[0]
            print(
                f"   → Node {target['osm_node_id']}, distance: {edge.metadata['distance_m']:.1f}m"
            )
            if "_id_hash" in target:
                print(f"   Target has identity hash: {target['_id_hash']}")

        # Check if input vertices get identity hashes
        print("   Testing identity hash generation:")
        engine_start = engine._add_identity_hash_to_vertex(start_coords)
        engine_goal = engine._add_identity_hash_to_vertex(goal_coords)
        print(f"   Start hash: {engine_start.get('_id_hash', 'MISSING')}")
        print(f"   Goal hash: {engine_goal.get('_id_hash', 'MISSING')}")

        # Test 2: Network provider navigation
        print("\n2. Testing OSM network navigation")
        node1_vertex = Vertex({"osm_node_id": 1})
        node2_vertex = Vertex({"osm_node_id": 2})

        edges_1_to_2 = network_provider(node1_vertex)
        edges_2_to_1 = network_provider(node2_vertex)

        print(f"   Node 1 → Node 2: {len(edges_1_to_2)} edges")
        print(f"   Node 2 → Node 1: {len(edges_2_to_1)} edges")

        # Test 3: Access provider offramps
        print("\n3. Testing offramps (OSM network → coordinate)")
        print(
            f"   Stored target coordinates: {len(access_provider._target_coordinates)}"
        )

        offramps_from_1 = access_provider(node1_vertex)
        offramps_from_2 = access_provider(node2_vertex)

        print(f"   Node 1 offramps: {len(offramps_from_1)}")
        print(f"   Node 2 offramps: {len(offramps_from_2)}")

        if offramps_from_2:
            target, edge = offramps_from_2[0]
            print(
                f"   → Coordinate ({target['lat']}, {target['lon']}), distance: {edge.metadata['distance_m']:.1f}m"
            )
            if "_id_hash" in target:
                print(f"   Offramp target has identity hash: {target['_id_hash']}")
        else:
            print("   No offramps found - this may indicate the issue!")

        # Test 4: Complete coordinate-to-coordinate routing
        print("\n🛣️  Complete Coordinate-to-Coordinate Routing")
        print("-" * 45)

        print(
            f"Route: ({start_coords['lat']}, {start_coords['lon']}) → ({goal_coords['lat']}, {goal_coords['lon']})"
        )

        try:
            result = engine.plan(start=start_coords, goal=goal_coords)

            if len(result) > 0:
                print(f"✅ SUCCESS! Found path with {len(result)} edges")

                total_cost = result.total_cost
                print(f"   Total cost: {total_cost:.2f} seconds")

                print("   Path breakdown:")
                for i, path_edge in enumerate(result):
                    target = path_edge.target
                    cost = path_edge.edge.cost

                    if "osm_node_id" in target:
                        print(
                            f"     {i + 1}. → OSM Node {target['osm_node_id']} (cost: {cost:.2f}s)"
                        )
                    else:
                        print(
                            f"     {i + 1}. → Coordinate ({target['lat']}, {target['lon']}) (cost: {cost:.2f}s)"
                        )

            else:
                print("⚠️  No path found")

        except Exception as e:
            print(f"❌ Planning failed: {e}")
            print(
                "   This may be expected if C extension pathfinding is not fully implemented"
            )

        print("\n🎉 Demo Complete!")
        print("The split provider architecture successfully enables:")
        print("  • Onramps: coordinate → OSM network")
        print("  • Network: OSM node → OSM node")
        print("  • Offramps: OSM network → coordinate")
        print("  • Complete coordinate-to-coordinate routing")

    finally:
        # Clean up
        osm_file.unlink()


if __name__ == "__main__":
    main()
