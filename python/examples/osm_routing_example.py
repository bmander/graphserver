#!/usr/bin/env python3
"""OSM Routing Example

This example demonstrates how to use the OpenStreetMap edge provider
for pedestrian pathfinding with the Graphserver engine.

Requirements:
    pip install graphserver[osm]

Usage:
    python osm_routing_example.py path/to/your_area.osm
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import OSMProvider
    from graphserver.providers.osm.types import WalkingProfile
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install with: pip install graphserver[osm]")
    sys.exit(1)


def main() -> None:
    """Main example function."""
    if len(sys.argv) != 2:
        print("Usage: python osm_routing_example.py <osm_file>")
        print("Download OSM data from: https://www.openstreetmap.org/export")
        sys.exit(1)

    osm_file = Path(sys.argv[1])
    if not osm_file.exists():
        print(f"OSM file not found: {osm_file}")
        sys.exit(1)

    print(f"Loading OSM data from: {osm_file}")
    print("This may take a moment for large files...")

    # Create a custom walking profile
    walking_profile = WalkingProfile(
        base_speed_ms=1.2,  # Slightly slower walking (1.2 m/s = 4.3 km/h)
        avoid_stairs=False,  # Allow stairs
        avoid_busy_roads=True,  # Prefer dedicated pedestrian infrastructure
        max_detour_factor=1.5,  # Allow up to 50% detour
    )

    # Initialize OSM provider
    start_time = time.time()
    try:
        osm_provider = OSMProvider(
            osm_file,
            walking_profile=walking_profile,
            search_radius_m=150.0,  # Look for nodes within 150m of coordinates
            max_nearby_nodes=5,  # Consider up to 5 nearby nodes
            build_index=True,  # Build spatial index for performance
        )
    except Exception as e:
        print(f"Error loading OSM data: {e}")
        sys.exit(1)

    load_time = time.time() - start_time
    print(f"OSM data loaded in {load_time:.2f} seconds")
    print(
        f"Network: {osm_provider.node_count} nodes, {osm_provider.way_count} ways, {osm_provider.edge_count} edges"
    )

    # Create and configure the planning engine
    engine = Engine()
    engine.register_provider("osm", osm_provider)

    print("\\nOSM Provider registered with Graphserver engine")
    print("Provider supports two vertex types:")
    print('  1. Geographic coordinates: {"lat": 47.6062, "lon": -122.3321}')
    print('  2. OSM node IDs: {"osm_node_id": 12345}')

    # Example 1: Find nearest node to coordinates
    print("\\n" + "=" * 60)
    print("Example 1: Finding nearest OSM node to coordinates")
    print("=" * 60)

    # Use coordinates near the center of your OSM data
    # These are example coordinates for Seattle - adjust for your data
    example_lat, example_lon = 47.6062, -122.3321

    nearest_node = osm_provider.find_nearest_node(example_lat, example_lon)
    if nearest_node:
        print(
            f"Nearest node to ({example_lat}, {example_lon}): {nearest_node['osm_node_id']}"
        )
        print(f"Node location: ({nearest_node['lat']}, {nearest_node['lon']})")
        if "name" in nearest_node:
            print(f"Node name: {nearest_node['name']}")
    else:
        print(f"No nodes found near ({example_lat}, {example_lon})")
        print(
            "Try increasing search_radius_m or using coordinates within your OSM data"
        )

    # Example 2: Generate edges from coordinates
    print("\\n" + "=" * 60)
    print("Example 2: Generating edges from geographic coordinates")
    print("=" * 60)

    coord_vertex = Vertex({"lat": example_lat, "lon": example_lon})
    edges_from_coords = osm_provider(coord_vertex)

    print(f"Found {len(edges_from_coords)} edges from coordinates:")
    for i, (target_vertex, edge) in enumerate(edges_from_coords[:3]):  # Show first 3
        print(f"  Edge {i + 1}: to node {target_vertex['osm_node_id']}")
        print(f"    Distance: {edge.metadata.get('distance_m', 0):.1f}m")
        print(f"    Walking time: {edge.cost:.1f}s")
        print(f"    Target: ({target_vertex['lat']:.6f}, {target_vertex['lon']:.6f})")

    if len(edges_from_coords) > 3:
        print(f"  ... and {len(edges_from_coords) - 3} more edges")

    # Example 3: Generate edges from OSM node ID
    if nearest_node:
        print("\\n" + "=" * 60)
        print("Example 3: Generating edges from OSM node ID")
        print("=" * 60)

        node_vertex = Vertex({"osm_node_id": nearest_node["osm_node_id"]})
        edges_from_node = osm_provider(node_vertex)

        print(
            f"Found {len(edges_from_node)} edges from node {nearest_node['osm_node_id']}:"
        )
        for i, (target_vertex, edge) in enumerate(edges_from_node[:3]):  # Show first 3
            print(f"  Edge {i + 1}: to node {target_vertex['osm_node_id']}")
            print(f"    Way ID: {edge.metadata.get('way_id', 'N/A')}")
            print(f"    Highway type: {edge.metadata.get('highway', 'unknown')}")
            print(f"    Distance: {edge.metadata.get('distance_m', 0):.1f}m")
            print(f"    Walking time: {edge.cost:.1f}s")

        if len(edges_from_node) > 3:
            print(f"  ... and {len(edges_from_node) - 3} more edges")

    # Example 4: Pathfinding between coordinates
    print("\\n" + "=" * 60)
    print("Example 4: Pathfinding between coordinates")
    print("=" * 60)

    if edges_from_coords and len(edges_from_coords) >= 2:
        # Use first and last nearby nodes as start/goal
        start_vertex = edges_from_coords[0][0]  # First nearby node
        goal_vertex = edges_from_coords[-1][0]  # Last nearby node

        print(
            f"Planning route from node {start_vertex['osm_node_id']} to node {goal_vertex['osm_node_id']}"
        )

        try:
            planning_start = time.time()
            result = engine.plan(start=start_vertex, goal=goal_vertex)
            planning_time = time.time() - planning_start

            print(f"Pathfinding completed in {planning_time:.3f} seconds")
            if result and len(result) > 0:
                print(f"Path found: {len(result)} edges")
                print(
                    f"Total cost: {result.total_cost:.1f} seconds ({result.total_cost / 60:.1f} minutes)"
                )

                print("\\nPath details:")
                for i, path_edge in enumerate(result[:5]):  # Show first 5 edges
                    print(f"  Step {i + 1}: to node {path_edge.target['osm_node_id']}")
                    print(f"    Cost: {path_edge.edge.cost:.1f}s")
                    if "highway" in path_edge.edge.metadata:
                        print(f"    Highway: {path_edge.edge.metadata['highway']}")

                if len(result) > 5:
                    print(f"  ... and {len(result) - 5} more steps")
            else:
                print("No path found between the selected nodes")

        except Exception as e:
            print(f"Pathfinding failed: {e}")
            print(
                "This may be expected if the C extension pathfinding is not fully implemented"
            )
    else:
        print("Insufficient nearby nodes for pathfinding example")

    print("\\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    print("\\nNext steps:")
    print("- Try with your own OSM data from https://www.openstreetmap.org/export")
    print("- Experiment with different WalkingProfile settings")
    print("- Adjust search_radius_m and max_nearby_nodes for your use case")
    print("- Use the provider in your own pathfinding applications")


if __name__ == "__main__":
    main()
