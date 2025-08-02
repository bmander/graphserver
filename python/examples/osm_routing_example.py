#!/usr/bin/env python3
"""OSM Routing Example

This example demonstrates pathfinding between coordinates using the
OpenStreetMap providers with the Graphserver engine.

Requirements:
    pip install graphserver[osm]

Usage:
    python osm_routing_example.py <osm_file> <start_lat,start_lon> <end_lat,end_lon>

Example:
    python osm_routing_example.py uw_campus.osm 47.65906510597771,-122.3043737809855 47.65910,-122.30430
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    from graphserver import Engine
    from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
    from graphserver.providers.osm.types import WalkingProfile
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install with: pip install graphserver[osm]")
    sys.exit(1)


# Routing configuration constants
WALKING_SPEED = 1.2  # m/s walking speed
MAX_DETOUR_FACTOR = 1.5
SEARCH_RADIUS_M = 150.0
MAX_NEARBY_NODES = 5
MINUTES_PER_SECOND = 60
LAT_MIN = -90
LAT_MAX = 90
LON_MIN = -180
LON_MAX = 180


def _validate_latitude(lat: float) -> None:
    """Validate latitude is in valid range."""
    if not (LAT_MIN <= lat <= LAT_MAX):
        msg = f"Invalid latitude: {lat} (must be between {LAT_MIN} and {LAT_MAX})"
        raise ValueError(msg)


def _validate_longitude(lon: float) -> None:
    """Validate longitude is in valid range."""
    if not (LON_MIN <= lon <= LON_MAX):
        msg = f"Invalid longitude: {lon} (must be between {LON_MIN} and {LON_MAX})"
        raise ValueError(msg)


def _raise_coordinate_format_error(coord_str: str) -> None:
    """Raise coordinate format error."""
    msg = f"Invalid coordinate format: {coord_str} (expected: lat,lon)"
    raise ValueError(msg)


def parse_coordinates(coord_str: str) -> tuple[float, float]:
    """Parse lat,lon coordinates from string.

    Args:
        coord_str: String like "47.6540,-122.3100"

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        ValueError: If coordinates are invalid
    """
    try:
        lat_str, lon_str = coord_str.split(",", 1)
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())

        # Basic validation
        _validate_latitude(lat)
        _validate_longitude(lon)
    except ValueError as e:
        if "could not convert" in str(e) or "not enough values" in str(e):
            _raise_coordinate_format_error(coord_str)
        raise
    else:
        return lat, lon


def main() -> None:
    """Main pathfinding example."""
    required_args = 4
    if len(sys.argv) != required_args:
        print(
            "Usage: python osm_routing_example.py <osm_file> <start_lat,start_lon> <end_lat,end_lon>"
        )
        print(
            "Example: python osm_routing_example.py uw_campus.osm 47.65906510597771,-122.3043737809855 47.65910,-122.30430"
        )
        sys.exit(1)

    osm_file = Path(sys.argv[1])
    if not osm_file.exists():
        print(f"OSM file not found: {osm_file}")
        sys.exit(1)

    try:
        start_lat, start_lon = parse_coordinates(sys.argv[2])
        end_lat, end_lon = parse_coordinates(sys.argv[3])
    except ValueError as e:
        print(f"Error parsing coordinates: {e}")
        sys.exit(1)

    print(f"🗺️  Loading OSM data from: {osm_file}")
    print(f"📍 Start: ({start_lat}, {start_lon})")
    print(f"🎯 Goal:  ({end_lat}, {end_lon})")
    print()

    # Initialize OSM providers
    start_time = time.time()
    try:
        walking_profile = WalkingProfile(
            base_speed_ms=WALKING_SPEED,  # m/s walking speed
            avoid_stairs=False,
            avoid_busy_roads=True,
            max_detour_factor=MAX_DETOUR_FACTOR,
        )

        network_provider = OSMNetworkProvider(
            osm_file,
            walking_profile=walking_profile,
        )

        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
            walking_profile=walking_profile,
            search_radius_m=SEARCH_RADIUS_M,
            max_nearby_nodes=MAX_NEARBY_NODES,
            build_index=True,
        )
    except Exception as e:
        print(f"❌ Error loading OSM data: {e}")
        sys.exit(1)

    load_time = time.time() - start_time
    print(f"✅ OSM data loaded in {load_time:.2f}s")
    print(
        f"   Network: {network_provider.node_count} nodes, {network_provider.way_count} ways, {network_provider.edge_count} edges"
    )
    print()

    # Create and configure the planning engine
    engine = Engine()
    engine.register_provider("osm_network", network_provider)
    engine.register_provider("osm_access", access_provider)

    # Create vertices directly from coordinates (new simplified API)
    print("🔗 Creating route vertices...")
    from graphserver import Vertex

    start_vertex = Vertex({"lat": start_lat, "lon": start_lon})
    goal_vertex = Vertex({"lat": end_lat, "lon": end_lon})

    # Link both vertices to the OSM network for coordinate-to-coordinate routing
    access_provider.link(start_vertex, start_lat, start_lon)
    access_provider.link(goal_vertex, end_lat, end_lon)

    print(f"   Start vertex: ({start_lat}, {start_lon})")
    print(f"   Goal vertex:  ({end_lat}, {end_lon})")

    # Verify vertices are linked to OSM nodes
    start_edges = access_provider(start_vertex)
    goal_edges = access_provider(goal_vertex)
    print(
        f"   Linked start to {len(start_edges)} OSM nodes, goal to {len(goal_edges)} OSM nodes"
    )
    print()

    # Execute pathfinding with coordinate-to-coordinate routing workaround
    print("🚀 Planning route...")
    try:
        planning_start = time.time()

        # Since direct coordinate-to-coordinate routing isn't fully supported yet,
        # we'll find nearby OSM nodes and try routing between them
        if not start_edges or not goal_edges:
            error_msg = "Could not find nearby OSM nodes for start or goal coordinates"
            raise RuntimeError(error_msg)  # noqa: TRY301

        result = None
        best_cost = float("inf")

        # Try all combinations of nearby start and goal OSM nodes
        attempts = 0
        for start_osm_vertex, start_edge in start_edges:
            for goal_osm_vertex, goal_edge in goal_edges:
                attempts += 1
                try:
                    # Try routing between OSM nodes
                    osm_result = engine.plan(
                        start=start_osm_vertex, goal=goal_osm_vertex
                    )
                    if osm_result and len(osm_result) > 0:
                        # Calculate total cost including access edges
                        total_cost = (
                            start_edge.cost + osm_result.total_cost + goal_edge.cost
                        )
                        if total_cost < best_cost:
                            result = osm_result
                            best_cost = total_cost
                            # Store access edge costs for later reporting
                            result._start_access_cost = start_edge.cost
                            result._goal_access_cost = goal_edge.cost
                            break
                except Exception as e:
                    # Log and continue trying other node combinations
                    print(f"   Route planning failed for node combination: {e}")
                    continue
            if result:
                break

        if attempts > 1:
            print(f"   Tested {attempts} OSM node combinations")

        planning_time = time.time() - planning_start

        if result and len(result) > 0:
            # Calculate total cost including access edges
            access_cost = getattr(result, "_start_access_cost", 0) + getattr(
                result, "_goal_access_cost", 0
            )
            total_cost_with_access = result.total_cost + access_cost

            print(f"✅ Route found in {planning_time:.3f}s")
            print(f"   Path: {len(result)} OSM edges + access")
            print(
                f"   Total time: {total_cost_with_access:.1f}s ({total_cost_with_access / MINUTES_PER_SECOND:.1f} minutes)"
            )
            if access_cost > 0:
                print(f"   (includes {access_cost:.1f}s access time)")
            print()

            print("📋 Route details:")
            for i, path_edge in enumerate(result):
                target = path_edge.target
                edge = path_edge.edge

                # Determine target type
                if "osm_node_id" in target:
                    target_desc = f"OSM node {target['osm_node_id']}"
                elif "lat" in target and "lon" in target:
                    target_desc = (
                        f"coordinate ({target['lat']:.5f}, {target['lon']:.5f})"
                    )
                else:
                    target_desc = "unknown target"

                print(f"   {i + 1:2d}. → {target_desc}")
                print(f"       Cost: {edge.cost:.1f}s")

                if edge.metadata:
                    if "distance_m" in edge.metadata:
                        print(f"       Distance: {edge.metadata['distance_m']:.1f}m")
                    if "highway" in edge.metadata:
                        print(f"       Highway: {edge.metadata['highway']}")
        else:
            print("❌ No route found between the coordinates")
            print(
                "   This may happen if the coordinates are in disconnected areas of the OSM network"
            )

    except Exception as e:
        print(f"❌ Pathfinding failed: {e}")
        if "no path found" in str(e).lower():
            print(
                "   This may happen if the coordinates are in disconnected areas of the OSM network"
            )
        sys.exit(1)

    print()
    print("🎉 Pathfinding completed successfully!")


if __name__ == "__main__":
    main()
