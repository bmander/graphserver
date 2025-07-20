#!/usr/bin/env python3
"""OSM Routing Example

This example demonstrates how to use the OpenStreetMap edge provider
for pedestrian pathfinding with the Graphserver engine.

Requirements:
    pip install graphserver[osm]

Usage:
    python osm_routing_example.py <osm_file> [start_lat,start_lon] [end_lat,end_lon]

    If start/end coordinates are not provided, you'll be prompted to enter them interactively.

Examples:
    python osm_routing_example.py campus.osm
    python osm_routing_example.py campus.osm 47.6540,-122.3100 47.6550,-122.3090
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import OSMNetworkProvider, OSMAccessProvider
    from graphserver.providers.osm.types import WalkingProfile
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install with: pip install graphserver[osm]")
    sys.exit(1)


def get_coordinates(prompt: str) -> tuple[float, float]:
    """Get lat,lon coordinates from user input.

    Args:
        prompt: Prompt to show the user

    Returns:
        Tuple of (latitude, longitude)
    """
    while True:
        try:
            coord_input = input(f"{prompt} (lat,lon): ").strip()
            if "," in coord_input:
                lat_str, lon_str = coord_input.split(",", 1)
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())

                # Basic validation
                if not (-90 <= lat <= 90):
                    print(f"Invalid latitude: {lat} (must be between -90 and 90)")
                    continue
                if not (-180 <= lon <= 180):
                    print(f"Invalid longitude: {lon} (must be between -180 and 180)")
                    continue

                return lat, lon
            else:
                print("Please enter coordinates as: lat,lon (e.g., 47.6540,-122.3100)")
        except ValueError:
            print("Invalid format. Please enter numeric coordinates as: lat,lon")
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)


def main() -> None:
    """Main example function."""
    if len(sys.argv) < 2:
        print(
            "Usage: python osm_routing_example.py <osm_file> [start_lat,start_lon] [end_lat,end_lon]"
        )
        print("Download OSM data from: https://www.openstreetmap.org/export")
        sys.exit(1)

    osm_file = Path(sys.argv[1])
    if not osm_file.exists():
        print(f"OSM file not found: {osm_file}")
        sys.exit(1)

    # Parse optional start/end coordinates from command line
    start_coords = None
    end_coords = None

    if len(sys.argv) >= 3:
        try:
            start_lat, start_lon = map(float, sys.argv[2].split(","))
            start_coords = (start_lat, start_lon)
        except ValueError:
            print(f"Invalid start coordinates: {sys.argv[2]}")
            sys.exit(1)

    if len(sys.argv) >= 4:
        try:
            end_lat, end_lon = map(float, sys.argv[3].split(","))
            end_coords = (end_lat, end_lon)
        except ValueError:
            print(f"Invalid end coordinates: {sys.argv[3]}")
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

    # Initialize OSM providers
    start_time = time.time()
    try:
        # Create network provider for OSM-to-OSM navigation
        network_provider = OSMNetworkProvider(
            osm_file,
            walking_profile=walking_profile,
        )
        
        # Create access provider for coordinate-to-OSM connections (shares parser)
        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
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
        f"Network: {network_provider.node_count} nodes, {network_provider.way_count} ways, {network_provider.edge_count} edges"
    )

    # Create and configure the planning engine
    engine = Engine()
    engine.register_provider("osm_network", network_provider)
    engine.register_provider("osm_access", access_provider)

    print("\\nOSM Providers registered with Graphserver engine")
    print("Two providers handle different routing aspects:")
    print('  1. osm_access: Connects coordinates to OSM network')
    print('  2. osm_network: Navigates between OSM nodes via streets')
    print("Vertex types:")
    print('  - Geographic coordinates: {"lat": 47.6062, "lon": -122.3321}')
    print('  - OSM node IDs: {"osm_node_id": 12345}')

    # Get coordinates for demonstration
    if start_coords is None:
        print("\\nTo test the provider, we need some coordinates within your OSM data.")
        print("You can find coordinates by:")
        print("  - Using www.openstreetmap.org and right-clicking to copy coordinates")
        print("  - Looking at your OSM data's geographic bounds")
        print("  - Using GPS coordinates from the area")
        start_coords = get_coordinates("Enter start coordinates")

    example_lat, example_lon = start_coords

    # Example 1: Find nearest node to coordinates
    print("\\n" + "=" * 60)
    print("Example 1: Finding nearest OSM node to coordinates")
    print("=" * 60)

    nearest_node = access_provider.find_nearest_node(example_lat, example_lon)
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
    print("Example 2: Generating access edges from geographic coordinates")
    print("=" * 60)

    coord_vertex = Vertex({"lat": example_lat, "lon": example_lon})
    edges_from_coords = access_provider(coord_vertex)

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
        print("Example 3: Generating network edges from OSM node ID")
        print("=" * 60)

        node_vertex = Vertex({"osm_node_id": nearest_node["osm_node_id"]})
        edges_from_node = network_provider(node_vertex)

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

    # Example 4: Pathfinding between coordinates using both providers
    print("\\n" + "=" * 60)
    print("Example 4: Pathfinding between coordinates (using both providers)")
    print("=" * 60)

    # Get goal coordinates for pathfinding
    if end_coords is None:
        print("\\nFor pathfinding demonstration, we need a destination coordinate.")
        end_coords = get_coordinates("Enter destination coordinates")

    goal_lat, goal_lon = end_coords

    # Create vertices from the coordinates
    start_vertex = Vertex({"lat": example_lat, "lon": example_lon})
    goal_vertex = Vertex({"lat": goal_lat, "lon": goal_lon})

    print(
        f"Planning route from ({example_lat}, {example_lon}) to ({goal_lat}, {goal_lon})"
    )
    print("Route will use:")
    print("  1. osm_access: coordinate → OSM network (onramp)")
    print("  2. osm_network: navigation between OSM nodes")
    print("  3. osm_access: OSM network → coordinate (offramp)")

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
            print("No path found between the selected coordinates")

    except Exception as e:
        print(f"Pathfinding failed: {e}")
        print(
            "This may be expected if the C extension pathfinding is not fully implemented"
        )

    print("\\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)
    print("\\nNext steps:")
    print("- Try with your own OSM data from https://www.openstreetmap.org/export")
    print("- Experiment with different WalkingProfile settings")
    print("- Adjust search_radius_m and max_nearby_nodes for your use case")
    print("- Register both providers in your own pathfinding applications")
    print("- Note: Both osm_network and osm_access providers are required for complete functionality")


if __name__ == "__main__":
    main()
