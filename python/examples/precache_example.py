#!/usr/bin/env python3
"""Example demonstrating Graphserver precaching functionality.

This example shows how to use precaching to improve routing performance
by pre-populating the edge cache with frequently used areas.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from typing import Any

from graphserver import Edge, Engine, Vertex


class CityGridProvider:
    """Simulated city grid provider for demonstration.

    This provider creates a grid-based street network with some
    areas having higher costs (simulating traffic, construction, etc.).
    """

    def __init__(self, width: int, height: int):
        """Initialize city grid.

        Args:
            width: Grid width (number of blocks)
            height: Grid height (number of blocks)
        """
        self.width = width
        self.height = height
        self.call_count = 0

        # Define some high-traffic areas with higher costs
        self.high_traffic_zones = {
            (10, 10): 2.0,  # Downtown center
            (15, 8): 1.5,  # Business district
            (5, 15): 1.8,  # Shopping area
        }

    def __call__(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Generate edges for city grid navigation."""
        self.call_count += 1

        x = vertex.get("x", 0)
        y = vertex.get("y", 0)

        edges = []

        # Generate edges to adjacent intersections (N, S, E, W)
        for dx, dy, direction in [
            (0, 1, "north"),
            (0, -1, "south"),
            (1, 0, "east"),
            (-1, 0, "west"),
        ]:
            new_x = x + dx
            new_y = y + dy

            # Check bounds
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                target = Vertex({"x": new_x, "y": new_y, "type": "intersection"})

                # Base cost is distance (1 block)
                base_cost = 1.0

                # Add traffic multiplier for high-traffic zones
                traffic_multiplier = self.high_traffic_zones.get((new_x, new_y), 1.0)
                final_cost = base_cost * traffic_multiplier

                edge = Edge(
                    cost=final_cost,
                    metadata={
                        "direction": direction,
                        "street_type": "city_street",
                        "traffic_level": traffic_multiplier,
                    },
                )
                edges.append((target, edge))

        return edges

    def reset_stats(self) -> None:
        """Reset call statistics."""
        self.call_count = 0


def create_high_traffic_seeds(width: int, height: int) -> list[Vertex]:
    """Create seed vertices for high-traffic areas.

    Args:
        width: Grid width
        height: Grid height

    Returns:
        List of seed vertices for precaching
    """
    seeds = []

    # Downtown core area
    seeds.extend(
        Vertex({"x": x, "y": y, "type": "intersection"})
        for x in range(8, 13)
        for y in range(8, 13)
    )

    # Business district
    seeds.extend(
        Vertex({"x": x, "y": y, "type": "intersection"})
        for x in range(13, 18)
        for y in range(6, 11)
    )

    # Shopping area
    seeds.extend(
        Vertex({"x": x, "y": y, "type": "intersection"})
        for x in range(3, 8)
        for y in range(13, 18)
    )

    return seeds


def benchmark_routing_performance(
    engine: Engine, provider: CityGridProvider, test_routes: list[tuple[Vertex, Vertex]]
) -> dict[str, Any]:
    """Benchmark routing performance with given test routes.

    Args:
        engine: Graphserver engine
        provider: City grid provider
        test_routes: List of (start, goal) vertex pairs

    Returns:
        Dictionary with performance metrics
    """
    provider.reset_stats()
    start_time = time.time()

    successful_routes = 0
    total_route_length = 0

    for start, goal in test_routes:
        try:
            result = engine.plan(start=start, goal=goal)
            if len(result) > 0:
                successful_routes += 1
                total_route_length += len(result)
        except Exception as e:
            # Route failed, continue with others
            print(f"Route planning failed: {e}", file=sys.stderr)

    end_time = time.time()

    stats = engine.get_stats()

    return {
        "elapsed_time": end_time - start_time,
        "successful_routes": successful_routes,
        "total_routes": len(test_routes),
        "avg_route_length": total_route_length / max(successful_routes, 1),
        "provider_calls": provider.call_count,
        "cache_hits": stats.get("cache_hits", 0),
        "cache_misses": stats.get("cache_misses", 0),
        "cache_puts": stats.get("cache_puts", 0),
    }


def create_test_routes(
    width: int, height: int, num_routes: int = 20
) -> list[tuple[Vertex, Vertex]]:
    """Create test routes for benchmarking.

    Args:
        width: Grid width
        height: Grid height
        num_routes: Number of test routes to create

    Returns:
        List of (start, goal) vertex pairs
    """
    import random

    routes = []
    random.seed(42)  # For reproducible results

    for _ in range(num_routes):
        start_x = random.randint(0, width - 1)  # noqa: S311
        start_y = random.randint(0, height - 1)  # noqa: S311
        goal_x = random.randint(0, width - 1)  # noqa: S311
        goal_y = random.randint(0, height - 1)  # noqa: S311

        start = Vertex({"x": start_x, "y": start_y, "type": "intersection"})
        goal = Vertex({"x": goal_x, "y": goal_y, "type": "intersection"})
        routes.append((start, goal))

    return routes


def demonstrate_precaching():
    """Main demonstration of precaching functionality."""
    print("🚗 Graphserver Precaching Performance Demo")
    print("=" * 50)

    # Create city grid (20x20 blocks)
    print("📍 Creating 20x20 city grid...")
    provider = CityGridProvider(width=20, height=20)

    # Create test routes
    test_routes = create_test_routes(20, 20, num_routes=50)
    print(f"🛣️  Generated {len(test_routes)} test routes")

    print("\n" + "=" * 50)
    print("🧪 PHASE 1: Routing WITHOUT Precaching")
    print("=" * 50)

    # Test without precaching
    engine_no_cache = Engine(enable_edge_caching=True)
    engine_no_cache.register_provider("city", provider)

    metrics_no_precache = benchmark_routing_performance(
        engine_no_cache, provider, test_routes
    )

    print(f"⏱️  Time elapsed: {metrics_no_precache['elapsed_time']:.3f} seconds")
    print(
        f"✅ Successful routes: {metrics_no_precache['successful_routes']}/{metrics_no_precache['total_routes']}"
    )
    print(
        f"📏 Average route length: {metrics_no_precache['avg_route_length']:.1f} edges"
    )
    print(f"🔄 Provider calls: {metrics_no_precache['provider_calls']}")
    print(f"💾 Cache hits: {metrics_no_precache['cache_hits']}")
    print(f"❌ Cache misses: {metrics_no_precache['cache_misses']}")

    print("\n" + "=" * 50)
    print("🧪 PHASE 2: Routing WITH Precaching")
    print("=" * 50)

    # Test with precaching
    engine_with_cache = Engine(enable_edge_caching=True)
    engine_with_cache.register_provider("city", provider)

    # Perform strategic precaching
    print("🎯 Identifying high-traffic areas for precaching...")
    high_traffic_seeds = create_high_traffic_seeds(20, 20)
    print(f"🌱 Created {len(high_traffic_seeds)} seed vertices")

    print("⚡ Precaching high-traffic areas...")
    precache_start = time.time()

    # Precache with reasonable limits
    engine_with_cache.precache_subgraph(
        provider_name="city",
        seed_vertices=high_traffic_seeds,
        max_depth=3,  # 3 blocks from each seed
        max_vertices=500,  # Reasonable cache size limit
    )

    precache_time = time.time() - precache_start
    precache_stats = engine_with_cache.get_stats()

    print(f"⏱️  Precaching time: {precache_time:.3f} seconds")
    print(f"💾 Vertices cached: {precache_stats['cache_puts']}")
    print(f"🔄 Provider calls during precaching: {precache_stats['providers_called']}")

    print("\n🚀 Running test routes with precached data...")

    metrics_with_precache = benchmark_routing_performance(
        engine_with_cache, provider, test_routes
    )

    print(f"⏱️  Time elapsed: {metrics_with_precache['elapsed_time']:.3f} seconds")
    print(
        f"✅ Successful routes: {metrics_with_precache['successful_routes']}/{metrics_with_precache['total_routes']}"
    )
    print(
        f"📏 Average route length: {metrics_with_precache['avg_route_length']:.1f} edges"
    )
    print(f"🔄 Provider calls: {metrics_with_precache['provider_calls']}")
    print(f"💾 Cache hits: {metrics_with_precache['cache_hits']}")
    print(f"❌ Cache misses: {metrics_with_precache['cache_misses']}")

    print("\n" + "=" * 50)
    print("📊 PERFORMANCE COMPARISON")
    print("=" * 50)

    # Calculate improvements
    time_improvement = (
        (metrics_no_precache["elapsed_time"] - metrics_with_precache["elapsed_time"])
        / metrics_no_precache["elapsed_time"]
        * 100
    )
    call_reduction = (
        (
            metrics_no_precache["provider_calls"]
            - metrics_with_precache["provider_calls"]
        )
        / metrics_no_precache["provider_calls"]
        * 100
    )

    print(f"🚀 Speed improvement: {time_improvement:+.1f}%")
    print(f"📞 Provider call reduction: {call_reduction:+.1f}%")

    if metrics_with_precache["cache_hits"] > 0:
        hit_rate = (
            metrics_with_precache["cache_hits"]
            / (
                metrics_with_precache["cache_hits"]
                + metrics_with_precache["cache_misses"]
            )
            * 100
        )
        print(f"🎯 Cache hit rate: {hit_rate:.1f}%")

    print(f"💾 Total precaching overhead: {precache_time:.3f} seconds")

    # Calculate break-even point
    if time_improvement > 0:
        break_even_routes = (
            precache_time
            / (
                metrics_no_precache["elapsed_time"]
                - metrics_with_precache["elapsed_time"]
            )
            * len(test_routes)
        )
        print(f"⚖️  Break-even point: ~{break_even_routes:.0f} routes")

    print("\n" + "=" * 50)
    print("💡 RECOMMENDATIONS")
    print("=" * 50)

    if time_improvement > 10:
        print("✅ Precaching shows significant performance benefits!")
        print("   Consider using precaching for:")
        print("   - High-traffic routing areas")
        print("   - Frequently accessed transit hubs")
        print("   - Dense urban cores")
    elif time_improvement > 0:
        print("⚠️  Precaching shows modest benefits.")
        print("   Best for applications with:")
        print("   - Many repeated routes in same areas")
        print("   - Long-running services")
        print("   - Predictable traffic patterns")
    else:
        print("❌ Precaching overhead exceeds benefits for this scenario.")
        print("   Consider:")
        print("   - Smaller precaching areas (reduce max_depth)")
        print("   - More targeted seed selection")
        print("   - Evaluating if your use case benefits from caching")

    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    demonstrate_precaching()
