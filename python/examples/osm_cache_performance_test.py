#!/usr/bin/env python3
"""OSM Cache Performance Test

This script demonstrates and benchmarks the edge caching functionality
with real OpenStreetMap data, showing performance improvements for repeated
routing queries.

Requirements:
    pip install graphserver[osm]

Usage:
    python osm_cache_performance_test.py <osm_file> [num_routes]

Examples:
    python osm_cache_performance_test.py uw_campus.osm
    python osm_cache_performance_test.py uw_campus.osm 20
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path
from typing import Any

try:
    from graphserver import Engine, EngineStats
    from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
    from graphserver.providers.osm.types import WalkingProfile
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install with: pip install graphserver[osm]")
    sys.exit(1)


# Performance test constants
DEFAULT_NUM_ROUTES = 10
DEFAULT_REPETITIONS = 3
SEARCH_RADIUS_M = 150.0
MAX_NEARBY_NODES = 5
BASE_WALKING_SPEED = 1.4
MAX_DETOUR_FACTOR = 1.3
EXCELLENT_SPEEDUP_THRESHOLD = 2.0
GOOD_SPEEDUP_THRESHOLD = 1.5
MODERATE_SPEEDUP_THRESHOLD = 1.1
EXCELLENT_HIT_RATIO = 50
GOOD_HIT_RATIO = 25


def create_test_routes(
    num_routes: int = DEFAULT_NUM_ROUTES,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Create test route pairs for benchmarking.

    Args:
        num_routes: Number of route pairs to create

    Returns:
        List of ((start_lat, start_lon), (goal_lat, goal_lon)) coordinate pairs
    """
    # For UW campus, use coordinates in connected areas based on working examples
    campus_routes = [
        # Main campus routes - using coordinates known to work with UW campus data
        (
            (47.65906510597771, -122.3043737809855),
            (47.65910, -122.30430),
        ),  # Actually working route 1 - nearby coordinates
        ((47.65880000, -122.30450000), (47.65930000, -122.30400000)),  # Working route 2
        ((47.65850000, -122.30500000), (47.65950000, -122.30350000)),  # Working route 3
        ((47.65900000, -122.30440000), (47.65950000, -122.30390000)),  # Working route 4
        ((47.65870000, -122.30460000), (47.65920000, -122.30410000)),  # Working route 5
        # Variations to test cache efficiency
        (
            (47.65906510597771, -122.3043737809855),
            (47.65880000, -122.30450000),
        ),  # Overlapping start
        (
            (47.65880000, -122.30450000),
            (47.65930000, -122.30400000),
        ),  # Connected segments
        (
            (47.65930000, -122.30400000),
            (47.65906510597771, -122.3043737809855),
        ),  # Reverse route
        (
            (47.65950000, -122.30350000),
            (47.65900000, -122.30440000),
        ),  # Cross connections
        ((47.65870000, -122.30460000), (47.65920000, -122.30410000)),  # Local area
    ]

    routes = []
    for i in range(min(num_routes, len(campus_routes))):
        start_coords, goal_coords = campus_routes[i]
        routes.append((start_coords, goal_coords))

    return routes


def _load_providers(
    osm_file: Path, walking_profile: WalkingProfile
) -> tuple[OSMNetworkProvider | None, OSMAccessProvider | None, float]:
    """Load OSM providers for benchmarking."""

    start_time = time.time()
    try:
        network_provider = OSMNetworkProvider(
            osm_file,
            walking_profile=walking_profile,
        )
        access_provider = OSMAccessProvider(
            network_provider.parser,
            walking_profile=walking_profile,
            search_radius_m=SEARCH_RADIUS_M,
            max_nearby_nodes=MAX_NEARBY_NODES,
        )
    except Exception as e:  # pragma: no cover - demo helper
        print(f"❌ Error loading OSM data: {e}")
        return None, None, 0.0

    load_time = time.time() - start_time
    print(f"✅ OSM data loaded in {load_time:.2f} seconds")
    print(
        f"   Network: {network_provider.node_count} nodes, {network_provider.way_count} ways"
    )

    return network_provider, access_provider, load_time


def _benchmark_engine(
    engine: Engine,
    routes: list[tuple[tuple[float, float], tuple[float, float]]],
    repetitions: int,
) -> tuple[list[float], int, EngineStats]:
    """Benchmark a planning engine."""

    times: list[float] = []
    successful = 0

    # Get access provider to link vertices
    access_provider = engine.providers.get("osm_access")

    for rep in range(repetitions):
        print(f"   Repetition {rep + 1}/{repetitions}...")
        rep_start = time.time()

        for i, (start_coords, goal_coords) in enumerate(routes):
            route_start = time.time()
            try:
                from graphserver import Vertex

                start_vertex = Vertex({"lat": start_coords[0], "lon": start_coords[1]})
                goal_vertex = Vertex({"lat": goal_coords[0], "lon": goal_coords[1]})

                # Link vertices for coordinate-to-coordinate routing
                if access_provider:
                    access_provider.link(start_vertex, start_coords[0], start_coords[1])
                    access_provider.link(goal_vertex, goal_coords[0], goal_coords[1])

                # Use OSM node pathfinding workaround like in osm_routing_example.py
                result = None
                if access_provider:
                    start_edges = access_provider.out_edges(start_vertex)
                    goal_edges = access_provider.out_edges(goal_vertex)

                    if start_edges and goal_edges:
                        best_cost = float("inf")
                        # Try combinations of nearby OSM nodes
                        for start_osm_vertex, start_edge in start_edges:
                            for goal_osm_vertex, goal_edge in goal_edges:
                                try:
                                    osm_result = engine.plan(
                                        start=start_osm_vertex, goal=goal_osm_vertex
                                    )
                                    if osm_result and len(osm_result) > 0:
                                        total_cost = (
                                            start_edge.cost
                                            + osm_result.total_cost
                                            + goal_edge.cost
                                        )
                                        if total_cost < best_cost:
                                            result = osm_result
                                            best_cost = total_cost
                                            break
                                except Exception:  # noqa: S112
                                    continue
                            if result:
                                break

                if result and len(result) > 0:
                    successful += 1
                times.append(time.time() - route_start)
            except Exception as e:  # pragma: no cover - diagnostic
                print(f"      Route {i + 1} failed: {e}")
                continue

        print(f"      Completed in {time.time() - rep_start:.3f}s")

        # Clear links after each repetition to avoid conflicts
        if access_provider:
            access_provider.clear_links()

    return times, successful, engine.get_stats()


def _calculate_metrics(
    no_cache_times: list[float],
    cache_times: list[float],
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Compute benchmark metrics."""

    if not no_cache_times or not cache_times:
        return {}

    no_cache_mean = statistics.mean(no_cache_times)
    cache_mean = statistics.mean(cache_times)
    speedup = no_cache_mean / cache_mean if cache_mean > 0 else 0.0

    return {
        "no_cache": {
            "mean_time": no_cache_mean,
            "total_time": sum(no_cache_times),
            "successful_routes": stats["no_cache"]["successful"],
            "stats": stats["no_cache"]["stats"],
        },
        "cache": {
            "mean_time": cache_mean,
            "total_time": sum(cache_times),
            "successful_routes": stats["cache"]["successful"],
            "speedup": speedup,
            "stats": stats["cache"]["stats"],
        },
    }


def benchmark_routing_performance(
    osm_file: Path,
    num_routes: int = DEFAULT_NUM_ROUTES,
    repetitions: int = DEFAULT_REPETITIONS,
) -> dict[str, Any]:
    """Benchmark routing performance with and without caching.

    Args:
        osm_file: Path to OSM file
        num_routes: Number of different routes to test
        repetitions: Number of times to repeat each route

    Returns:
        Dictionary with performance results
    """
    print(f"\\n🏗️  Setting up OSM providers from {osm_file}")

    # Create walking profile
    walking_profile = WalkingProfile(
        base_speed_ms=BASE_WALKING_SPEED,  # Normal walking speed
        avoid_stairs=False,
        avoid_busy_roads=True,
        max_detour_factor=MAX_DETOUR_FACTOR,
    )

    # Load OSM data
    network_provider, access_provider, load_time = _load_providers(
        osm_file, walking_profile
    )
    if network_provider is None or access_provider is None:
        return {}

    # Create test routes
    routes = create_test_routes(num_routes)
    print(f"\\n📍 Created {len(routes)} test routes for benchmarking")

    results = {
        "osm_file": str(osm_file),
        "num_routes": len(routes),
        "repetitions": repetitions,
        "load_time": load_time,
        "network_stats": {
            "nodes": network_provider.node_count,
            "ways": network_provider.way_count,
            "edges": network_provider.edge_count,
        },
    }

    # Benchmark WITHOUT caching
    print("\\n🚫 Benchmarking WITHOUT cache...")
    no_cache_engine = Engine(enable_edge_caching=False)
    no_cache_engine.register_provider("osm_network", network_provider)
    no_cache_engine.register_provider("osm_access", access_provider)
    no_cache_times, no_cache_successful, no_cache_stats = _benchmark_engine(
        no_cache_engine, routes, repetitions
    )

    # Benchmark WITH caching
    print("\\n✅ Benchmarking WITH cache...")
    cache_engine = Engine(enable_edge_caching=True)
    cache_engine.register_provider("osm_network", network_provider)
    cache_engine.register_provider("osm_access", access_provider)
    cache_times, cache_successful, cache_stats = _benchmark_engine(
        cache_engine, routes, repetitions
    )

    # Calculate performance metrics
    stats = {
        "no_cache": {
            "successful": no_cache_successful,
            "stats": no_cache_stats,
        },
        "cache": {
            "successful": cache_successful,
            "stats": cache_stats,
        },
    }
    results.update(_calculate_metrics(no_cache_times, cache_times, stats))

    return results


def print_performance_results(results: dict[str, Any]) -> None:
    """Print formatted performance benchmark results.

    Args:
        results: Results dictionary from benchmark_routing_performance
    """
    if not results:
        print("❌ No results to display")
        return

    print("\\n" + "=" * 60)
    print("🎯 OSM CACHE PERFORMANCE RESULTS")
    print("=" * 60)

    print("\\n📊 Test Configuration:")
    print(f"   OSM file: {results['osm_file']}")
    print(f"   Test routes: {results['num_routes']}")
    print(f"   Repetitions: {results['repetitions']}")
    print(f"   OSM load time: {results['load_time']:.2f}s")

    network = results["network_stats"]
    print("\\n🗺️  Network Statistics:")
    print(f"   Nodes: {network['nodes']:,}")
    print(f"   Ways: {network['ways']:,}")
    print(f"   Edges: {network['edges']:,}")

    if "no_cache" in results and "cache" in results:
        no_cache = results["no_cache"]
        cache = results["cache"]

        print("\\n⏱️  Routing Performance:")
        print("   WITHOUT Cache:")
        print(f"     Average route time: {no_cache['mean_time']:.4f}s")
        print(f"     Total time: {no_cache['total_time']:.3f}s")
        print(f"     Successful routes: {no_cache['successful_routes']}")

        print("   WITH Cache:")
        print(f"     Average route time: {cache['mean_time']:.4f}s")
        print(f"     Total time: {cache['total_time']:.3f}s")
        print(f"     Successful routes: {cache['successful_routes']}")
        print(f"     🚀 Speedup: {cache['speedup']:.1f}x")

        print("\\n📈 Cache Statistics:")
        cache_stats = cache["stats"]
        total_cache_ops = cache_stats.cache_hits + cache_stats.cache_misses
        hit_ratio = (
            cache_stats.cache_hits / total_cache_ops * 100 if total_cache_ops > 0 else 0
        )

        print(f"   Cache hits: {cache_stats.cache_hits}")
        print(f"   Cache misses: {cache_stats.cache_misses}")
        print(f"   Cache puts: {cache_stats.cache_puts}")
        print(f"   Hit ratio: {hit_ratio:.1f}%")
        print(f"   Vertices expanded: {cache_stats.vertices_expanded}")
        print(f"   Providers called: {cache_stats.providers_called}")

        # Cache efficiency analysis
        if cache["speedup"] >= EXCELLENT_SPEEDUP_THRESHOLD:
            print(f"\\n✅ EXCELLENT: Cache provides {cache['speedup']:.1f}x speedup!")
        elif cache["speedup"] >= GOOD_SPEEDUP_THRESHOLD:
            print(f"\\n✅ GOOD: Cache provides {cache['speedup']:.1f}x speedup")
        elif cache["speedup"] >= MODERATE_SPEEDUP_THRESHOLD:
            print(f"\\n⚠️  MODERATE: Cache provides {cache['speedup']:.1f}x speedup")
        else:
            print(f"\\n❌ LIMITED: Cache speedup is only {cache['speedup']:.1f}x")

        if hit_ratio >= EXCELLENT_HIT_RATIO:
            print(
                f"   Cache hit ratio of {hit_ratio:.1f}% is excellent for real-world scenarios"
            )
        elif hit_ratio >= GOOD_HIT_RATIO:
            print(
                f"   Cache hit ratio of {hit_ratio:.1f}% shows good cache utilization"
            )
        else:
            print(
                f"   Cache hit ratio of {hit_ratio:.1f}% suggests routes have little overlap"
            )


def main() -> None:
    """Main function."""
    min_args = 2
    if len(sys.argv) < min_args:
        print("Usage: python osm_cache_performance_test.py <osm_file> [num_routes]")
        print("\\nExample:")
        print("  python osm_cache_performance_test.py uw_campus.osm")
        print("  python osm_cache_performance_test.py uw_campus.osm 20")
        sys.exit(1)

    osm_file = Path(sys.argv[1])
    if not osm_file.exists():
        print(f"❌ OSM file not found: {osm_file}")
        sys.exit(1)

    num_routes = DEFAULT_NUM_ROUTES
    optional_args = 3
    if len(sys.argv) >= optional_args:
        try:
            num_routes = int(sys.argv[2])
        except ValueError:
            print(f"❌ Invalid number of routes: {sys.argv[2]}")
            sys.exit(1)

    print("🧪 Starting OSM Cache Performance Test")
    print(f"   OSM file: {osm_file}")
    print(f"   Routes to test: {num_routes}")
    print(f"   Repetitions: {DEFAULT_REPETITIONS}")

    # Run performance benchmark
    results = benchmark_routing_performance(
        osm_file, num_routes, repetitions=DEFAULT_REPETITIONS
    )

    # Display results
    print_performance_results(results)

    print("\\n🎉 Performance test completed!")


if __name__ == "__main__":
    main()
