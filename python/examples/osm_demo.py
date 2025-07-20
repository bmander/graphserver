#!/usr/bin/env python3
"""OSM Provider Demonstration

This script demonstrates the complete functionality of the OpenStreetMap
edge provider for Graphserver, including spatial indexing, edge generation,
and walking profiles.
"""

from graphserver import Engine, Vertex
from graphserver.providers.osm import OSMProvider
from graphserver.providers.osm.types import WalkingProfile


def main():
    """Demonstrate OSM provider functionality."""
    print("🗺️  OSM Provider Demonstration")
    print("=" * 50)

    # Check if we have OSM data
    import os

    if not os.path.exists("uw_campus.osm"):
        print("❌ OSM data file 'uw_campus.osm' not found")
        print("Run: python download_osm_data.py")
        return

    print("📂 Loading OSM data...")

    # Create walking profile optimized for campus navigation
    campus_profile = WalkingProfile(
        base_speed_ms=1.3,  # Comfortable walking pace
        avoid_stairs=False,  # Stairs are OK on campus
        avoid_busy_roads=True,  # Prefer pedestrian paths
        max_detour_factor=1.5,
    )

    # Initialize provider with spatial indexing
    provider = OSMProvider(
        "uw_campus.osm",
        walking_profile=campus_profile,
        search_radius_m=100.0,
        max_nearby_nodes=5,
        build_index=True,
    )

    print(
        f"✅ Loaded {provider.node_count:,} nodes, {provider.way_count:,} ways, {provider.edge_count:,} edges"
    )

    # Demonstrate spatial queries
    print("\n🔍 Spatial Query Demonstration")
    print("-" * 30)

    # Campus coordinates (adjust for your data)
    test_lat, test_lon = 47.65906510597771, -122.3043737809855

    # Find nearest node
    nearest = provider.find_nearest_node(test_lat, test_lon)
    if nearest:
        print(f"📍 Nearest node to ({test_lat}, {test_lon}):")
        print(f"   Node ID: {nearest['osm_node_id']}")
        print(f"   Location: ({nearest['lat']:.6f}, {nearest['lon']:.6f})")

        # Show any tags
        tags = {
            k: v for k, v in nearest.items() if k not in {"osm_node_id", "lat", "lon"}
        }
        if tags:
            print(f"   Tags: {tags}")

    # Demonstrate edge generation from coordinates
    print("\n🔗 Edge Generation from Coordinates")
    print("-" * 40)

    coord_vertex = Vertex({"lat": test_lat, "lon": test_lon})
    edges = provider(coord_vertex)

    print(f"Generated {len(edges)} edges from coordinates:")
    for i, (target, edge) in enumerate(edges):
        distance = edge.metadata.get("distance_m", 0)
        print(f"  {i + 1}. → Node {target['osm_node_id']}")
        print(f"     Distance: {distance:.1f}m, Time: {edge.cost:.1f}s")
        print(f"     Target: ({target['lat']:.6f}, {target['lon']:.6f})")

    # Demonstrate edge generation from node ID
    if nearest:
        print(f"\n🚶 Edge Generation from Node {nearest['osm_node_id']}")
        print("-" * 40)

        node_vertex = Vertex({"osm_node_id": nearest["osm_node_id"]})
        node_edges = provider(node_vertex)

        print(
            f"Found {len(node_edges)} connections from node {nearest['osm_node_id']}:"
        )
        for i, (target, edge) in enumerate(node_edges[:3]):  # Show first 3
            distance = edge.metadata.get("distance_m", 0)
            highway = edge.metadata.get("highway", "unknown")
            way_id = edge.metadata.get("way_id", "N/A")

            print(f"  {i + 1}. → Node {target['osm_node_id']} via {highway}")
            print(
                f"     Way ID: {way_id}, Distance: {distance:.1f}m, Cost: {edge.cost:.1f}s"
            )

        if len(node_edges) > 3:
            print(f"     ... and {len(node_edges) - 3} more connections")

    # Demonstrate Graphserver integration
    print("\n🚀 Graphserver Engine Integration")
    print("-" * 35)

    engine = Engine()
    engine.register_provider("osm", provider)

    print(f"✅ Provider registered with engine")
    print(f"   Available providers: {list(engine.providers.keys())}")

    # Test pathfinding (may not find path depending on connectivity)
    print("\n🛤️  Pathfinding Test")
    print("-" * 20)

    # Try to find a path between nearby points
    start_coord = Vertex({"lat": test_lat, "lon": test_lon})
    goal_coord = Vertex({"lat": test_lat + 0.001, "lon": test_lon + 0.001})

    print(f"Attempting to plan route:")
    print(f"  From: ({start_coord['lat']}, {start_coord['lon']})")
    print(f"  To:   ({goal_coord['lat']}, {goal_coord['lon']})")

    try:
        result = engine.plan(start=start_coord, goal=goal_coord)
        if result and len(result) > 0:
            print(f"✅ Path found: {len(result)} edges")
            print(
                f"   Total time: {result.total_cost:.1f}s ({result.total_cost / 60:.1f} minutes)"
            )
        else:
            print("⚠️  No path found (may be normal for disconnected areas)")
    except Exception as e:
        print(f"⚠️  Pathfinding error: {e}")
        print("   This is expected if C extension pathfinding is not fully implemented")

    # Show network statistics
    print("\n📊 Network Statistics")
    print("-" * 20)

    # Analyze highway types
    highway_stats = {}
    for way in provider.parser.ways.values():
        highway = way.tags.get("highway", "unknown")
        highway_stats[highway] = highway_stats.get(highway, 0) + 1

    print("Highway type distribution:")
    for highway, count in sorted(
        highway_stats.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / provider.way_count) * 100
        print(f"  {highway:15} {count:4d} ways ({percentage:5.1f}%)")

    print(f"\n🎉 OSM Provider Demo Complete!")
    print(f"   Total walkable network: {provider.edge_count:,} edges")
    print(
        f"   Spatial index: {len(provider.spatial_index):,} indexed nodes"
        if provider.spatial_index
        else "   No spatial index"
    )
    print(f"   Provider ready for routing applications!")


if __name__ == "__main__":
    main()
