"""Tests for GraphServer precaching functionality.

This module contains comprehensive tests for the precaching system,
including basic operations, error handling, and integration with providers.

Note: Some tests focus on functional verification rather than statistics
due to a known limitation where precaching doesn't update engine statistics.
"""

from __future__ import annotations

import gc
from collections.abc import Sequence

import pytest

from graphserver import Edge, Engine, Vertex


class GridProvider:
    """Grid provider for testing precaching behavior."""

    def __init__(self, width: int, height: int):
        """Initialize grid provider.

        Args:
            width: Grid width
            height: Grid height
        """
        self.width = width
        self.height = height
        self.call_count = 0
        self.called_with: list[Vertex] = []

    def __call__(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Grid provider implementation."""
        self.call_count += 1
        self.called_with.append(vertex)

        # Get vertex coordinates
        x = vertex.get("x", 0)
        y = vertex.get("y", 0)

        edges = []
        # Generate edges to adjacent cells (north, south, east, west)
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x = x + dx
            new_y = y + dy

            # Check bounds
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                target = Vertex({"x": new_x, "y": new_y})
                edge = Edge(cost=1.0)
                edges.append((target, edge))

        return edges

    def reset(self) -> None:
        """Reset call tracking."""
        self.call_count = 0
        self.called_with.clear()


class TestPrecacheBasic:
    """Test basic precaching functionality."""

    def test_precache_single_seed(self):
        """Test precaching with a single seed vertex."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(5, 5)
        engine.register_provider("grid", provider)

        # Create seed vertex
        seed = Vertex({"x": 2, "y": 2})

        # Test precaching with depth limit
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=[seed],
            max_depth=2,
        )

        # Provider should have been called multiple times
        assert provider.call_count > 1

        # Verify that cache statistics show cache puts
        stats = engine.get_stats()
        assert stats["cache_puts"] > 0

    def test_precache_multiple_seeds(self):
        """Test precaching with multiple seed vertices."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(10, 10)
        engine.register_provider("grid", provider)

        # Create multiple seed vertices
        seeds = [
            Vertex({"x": 0, "y": 0}),
            Vertex({"x": 9, "y": 9}),
            Vertex({"x": 5, "y": 5}),
        ]

        # Test precaching with multiple seeds
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=seeds,
            max_depth=3,
        )

        # Provider should have been called multiple times
        assert provider.call_count > len(seeds)

        # Verify cache statistics
        stats = engine.get_stats()
        assert stats["cache_puts"] > 0

    def test_precache_vertex_limit(self):
        """Test precaching with vertex limit."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(20, 20)
        engine.register_provider("grid", provider)

        seed = Vertex({"x": 10, "y": 10})

        # Test with small vertex limit
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=[seed],
            max_vertices=10,
        )

        # Should respect the vertex limit
        stats = engine.get_stats()
        assert stats["cache_puts"] <= 10

    def test_precache_depth_limit(self):
        """Test precaching with depth limit."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(10, 10)
        engine.register_provider("grid", provider)

        seed = Vertex({"x": 5, "y": 5})

        # Test with depth limit of 1 (only immediate neighbors)
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=[seed],
            max_depth=1,
        )

        # Should cache seed vertex plus its immediate neighbors (at most 5 vertices)
        stats = engine.get_stats()
        assert 1 <= stats["cache_puts"] <= 5


class TestPrecacheErrors:
    """Test error conditions for precaching."""

    def test_precache_cache_disabled(self):
        """Test precaching with caching disabled."""
        engine = Engine(enable_edge_caching=False)
        provider = GridProvider(5, 5)
        engine.register_provider("grid", provider)

        seed = Vertex({"x": 0, "y": 0})

        # Should raise ValueError since caching is disabled
        with pytest.raises(ValueError, match="Edge caching must be enabled"):
            engine.precache_subgraph(
                provider_name="grid",
                seed_vertices=[seed],
            )

    def test_precache_provider_not_found(self):
        """Test precaching with non-existent provider."""
        engine = Engine(enable_edge_caching=True)

        seed = Vertex({"x": 0, "y": 0})

        # Should raise ValueError for non-existent provider
        with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
            engine.precache_subgraph(
                provider_name="nonexistent",
                seed_vertices=[seed],
            )

    def test_precache_empty_seeds(self):
        """Test precaching with empty seed list."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(5, 5)
        engine.register_provider("grid", provider)

        # Should raise ValueError for empty seed list
        with pytest.raises(ValueError, match="At least one seed vertex is required"):
            engine.precache_subgraph(
                provider_name="grid",
                seed_vertices=[],
            )

    def test_precache_invalid_seed_type(self):
        """Test precaching with invalid seed vertex type."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(5, 5)
        engine.register_provider("grid", provider)

        # Should raise TypeError for non-Vertex objects
        with pytest.raises(
            TypeError, match="Seed vertex at index 0 must be a Vertex object"
        ):
            engine.precache_subgraph(
                provider_name="grid",
                seed_vertices=[{"x": 0, "y": 0}],  # Dictionary instead of Vertex
            )

    def test_precache_mixed_invalid_seeds(self):
        """Test precaching with mix of valid and invalid seeds."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(5, 5)
        engine.register_provider("grid", provider)

        seeds = [
            Vertex({"x": 0, "y": 0}),  # Valid
            {"x": 1, "y": 1},  # Invalid - dictionary
        ]

        # Should raise TypeError for the invalid seed
        with pytest.raises(
            TypeError, match="Seed vertex at index 1 must be a Vertex object"
        ):
            engine.precache_subgraph(
                provider_name="grid",
                seed_vertices=seeds,
            )


class TestPrecacheIntegration:
    """Test integration with existing cache functionality."""

    def test_precache_improves_performance(self):
        """Test that precaching improves subsequent operations."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(20, 20)
        engine.register_provider("grid", provider)

        # Create seed and goal vertices
        seed = Vertex({"x": 0, "y": 0})
        goal = Vertex({"x": 5, "y": 5})

        # Reset provider call count
        provider.reset()

        # First, do a plan without precaching
        result1 = engine.plan(start=seed, goal=goal)
        calls_without_precache = provider.call_count

        # Reset and precache the area
        provider.reset()
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=[seed],
            max_depth=10,  # Should cover the path to goal
        )

        # Now do the same plan - should use cached edges
        result2 = engine.plan(start=seed, goal=goal)
        calls_with_precache = provider.call_count

        # Both plans should succeed
        assert len(result1) > 0
        assert len(result2) > 0

        # Precaching should reduce provider calls for subsequent planning
        # Note: We compare provider call counts rather than engine stats
        # because planning resets statistics
        assert calls_with_precache < calls_without_precache

    def test_precache_cache_statistics(self):
        """Test that precaching updates cache statistics correctly."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(10, 10)
        engine.register_provider("grid", provider)

        # Get initial stats
        initial_stats = engine.get_stats()

        # Perform precaching
        seed = Vertex({"x": 5, "y": 5})
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=[seed],
            max_depth=2,
        )

        # Get stats after precaching
        final_stats = engine.get_stats()

        # Cache puts should have increased
        assert final_stats["cache_puts"] > initial_stats["cache_puts"]

        # Providers called should have increased
        assert final_stats["providers_called"] > initial_stats["providers_called"]

        # Edges generated should have increased
        assert final_stats["edges_generated"] > initial_stats["edges_generated"]

    def test_precache_with_unlimited_parameters(self):
        """Test precaching with unlimited depth and vertices."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(5, 5)  # Small grid to avoid infinite precaching
        engine.register_provider("grid", provider)

        seed = Vertex({"x": 2, "y": 2})

        # Test with unlimited parameters (0 = unlimited)
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=[seed],
            max_depth=0,
            max_vertices=0,
        )

        # Should cache some vertices
        stats = engine.get_stats()
        assert stats["cache_puts"] > 0

        # For a 5x5 grid, should cache at most 25 vertices
        assert stats["cache_puts"] <= 25


class TestPrecacheMemory:
    """Test memory management during precaching."""

    def test_precache_memory_cleanup(self):
        """Test that precaching doesn't leak memory."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(10, 10)
        engine.register_provider("grid", provider)

        # Force garbage collection before test
        gc.collect()

        # Perform multiple precaching operations
        for i in range(5):
            seed = Vertex({"x": i, "y": i})
            engine.precache_subgraph(
                provider_name="grid",
                seed_vertices=[seed],
                max_depth=3,
            )

        # Force garbage collection after test
        gc.collect()

        # Test should complete without memory errors
        # (Actual memory leak detection would require external tools)
        stats = engine.get_stats()
        assert stats["cache_puts"] > 0

    def test_precache_large_seed_list(self):
        """Test precaching with a large number of seeds."""
        engine = Engine(enable_edge_caching=True)
        provider = GridProvider(20, 20)
        engine.register_provider("grid", provider)

        # Create many seed vertices
        seeds = [
            Vertex({"x": x, "y": y}) for x in range(0, 20, 2) for y in range(0, 20, 2)
        ]

        # Should handle large seed list without issues
        engine.precache_subgraph(
            provider_name="grid",
            seed_vertices=seeds,
            max_depth=1,  # Keep depth small to avoid excessive computation
        )

        stats = engine.get_stats()
        assert stats["cache_puts"] > 0
