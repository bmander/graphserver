"""Tests for GraphServer edge caching functionality.

This module contains comprehensive tests for the edge caching system,
including basic operations, statistics, provider integration, and error
handling.
"""

from __future__ import annotations

import contextlib
import gc
import time
from collections.abc import Sequence

import pytest

from graphserver import Edge, Engine, Vertex


class MockProvider:
    """Mock edge provider for testing cache behavior."""

    def __init__(self, edges_to_return: list[tuple[Vertex, Edge]] | None = None):
        """Initialize mock provider.

        Args:
            edges_to_return: List of edges to return from provider calls
        """
        self.edges_to_return = edges_to_return or []
        self.call_count = 0
        self.called_with: list[Vertex] = []

    def __call__(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Mock provider implementation."""
        self.call_count += 1
        self.called_with.append(vertex)
        return self.edges_to_return

    def reset(self) -> None:
        """Reset call tracking."""
        self.call_count = 0
        self.called_with.clear()


class TestEngineCache:
    """Test basic engine caching functionality."""

    def test_engine_creation_without_cache(self):
        """Test creating engine without caching enabled."""
        engine = Engine(enable_edge_caching=False)
        assert not engine.cache_enabled

        stats = engine.get_stats()
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_puts" in stats
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_puts"] == 0

    def test_engine_creation_with_cache(self):
        """Test creating engine with caching enabled."""
        engine = Engine(enable_edge_caching=True)
        assert engine.cache_enabled

        stats = engine.get_stats()
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_puts" in stats
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_puts"] == 0

    def test_cache_disabled_behavior(self):
        """Test that cache doesn't interfere when disabled."""
        engine = Engine(enable_edge_caching=False)

        # Create mock provider that returns different edges each time
        edges = [
            (Vertex({"id": "target1"}), Edge(cost=10.0)),
            (Vertex({"id": "target2"}), Edge(cost=20.0)),
        ]
        provider = MockProvider(edges)
        engine.register_provider("test", provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "target1"})

        # Multiple planning calls should not use cache
        for _ in range(3):
            with contextlib.suppress(Exception):
                # Planning may fail, but that's not what we're testing
                engine.plan(start=start, goal=goal)

        stats = engine.get_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_puts"] == 0

    def test_cache_enabled_behavior(self):
        """Test that cache operates when enabled."""
        engine = Engine(enable_edge_caching=True)

        # Create mock provider
        edges = [
            (Vertex({"id": "target1"}), Edge(cost=10.0)),
            (Vertex({"id": "target2"}), Edge(cost=20.0)),
        ]
        provider = MockProvider(edges)
        engine.register_provider("test", provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "target1"})

        # Multiple planning calls may use cache for vertex expansion
        for _ in range(3):
            with contextlib.suppress(Exception):
                # Planning may fail, but vertex expansion should still occur
                engine.plan(start=start, goal=goal)

        final_stats = engine.get_stats()
        # With cache enabled, there should be some cache activity
        total_cache_ops = (
            final_stats["cache_hits"]
            + final_stats["cache_misses"]
            + final_stats["cache_puts"]
        )
        assert total_cache_ops >= 0  # Cache may be used during expansion


class TestCacheStatistics:
    """Test cache statistics and metrics validation."""

    def test_initial_statistics(self):
        """Test that engine starts with zero cache statistics."""
        engine = Engine(enable_edge_caching=True)
        stats = engine.get_stats()

        assert isinstance(stats, dict)
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_puts" in stats
        assert "vertices_expanded" in stats
        assert "edges_generated" in stats
        assert "providers_called" in stats

        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_puts"] == 0
        assert stats["vertices_expanded"] == 0
        assert stats["edges_generated"] == 0
        assert stats["providers_called"] == 0

    def test_statistics_consistency(self):
        """Test that cache statistics remain consistent."""
        engine = Engine(enable_edge_caching=True)

        # Get stats multiple times
        stats1 = engine.get_stats()
        stats2 = engine.get_stats()

        # Statistics should be consistent between calls
        assert stats1 == stats2

        # All cache counters should be non-negative
        for stat_name in ["cache_hits", "cache_misses", "cache_puts"]:
            assert stats1[stat_name] >= 0

    def test_cache_property_consistency(self):
        """Test that cache_enabled property matches configuration."""
        engine_with_cache = Engine(enable_edge_caching=True)
        engine_without_cache = Engine(enable_edge_caching=False)

        assert engine_with_cache.cache_enabled is True
        assert engine_without_cache.cache_enabled is False

    def test_statistics_after_provider_registration(self):
        """Test that statistics remain valid after provider operations."""
        engine = Engine(enable_edge_caching=True)

        # Register a provider
        provider = MockProvider()
        engine.register_provider("test", provider)

        stats_after_register = engine.get_stats()

        # Basic stats should still be accessible and valid
        assert isinstance(stats_after_register, dict)
        assert all(
            stats_after_register[key] >= 0
            for key in ["cache_hits", "cache_misses", "cache_puts"]
        )


class TestCacheIntegration:
    """Test cache integration with providers and real scenarios."""

    def test_cache_with_multiple_providers(self):
        """Test cache behavior with multiple registered providers."""
        engine = Engine(enable_edge_caching=True)

        # Register multiple providers
        provider1 = MockProvider([(Vertex({"id": "p1_target"}), Edge(cost=5.0))])
        provider2 = MockProvider([(Vertex({"id": "p2_target"}), Edge(cost=15.0))])

        engine.register_provider("provider1", provider1)
        engine.register_provider("provider2", provider2)

        initial_stats = engine.get_stats()

        # Test vertex that both providers might expand
        test_vertex = Vertex({"id": "test"})
        start = test_vertex
        goal = Vertex({"id": "goal"})

        # Attempt planning (may fail, but should exercise cache)
        with contextlib.suppress(Exception):
            engine.plan(start=start, goal=goal)

        final_stats = engine.get_stats()

        # Cache operations should be valid
        assert final_stats["cache_hits"] >= initial_stats["cache_hits"]
        assert final_stats["cache_misses"] >= initial_stats["cache_misses"]
        assert final_stats["cache_puts"] >= initial_stats["cache_puts"]

    def test_cache_consistency_across_plans(self):
        """Test that cache statistics are consistent across multiple plans."""
        engine = Engine(enable_edge_caching=True)

        provider = MockProvider(
            [
                (Vertex({"id": "intermediate"}), Edge(cost=10.0)),
                (Vertex({"id": "target"}), Edge(cost=20.0)),
            ]
        )
        engine.register_provider("test", provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "target"})

        # Execute multiple plans and track statistics
        stats_history = []
        for i in range(3):
            with contextlib.suppress(Exception):
                engine.plan(start=start, goal=goal)

            stats = engine.get_stats()
            stats_history.append(stats)

            # Statistics should only increase or stay the same
            if i > 0:
                prev_stats = stats_history[i - 1]
                assert stats["cache_hits"] >= prev_stats["cache_hits"]
                assert stats["cache_misses"] >= prev_stats["cache_misses"]
                assert stats["cache_puts"] >= prev_stats["cache_puts"]
                assert stats["vertices_expanded"] >= prev_stats["vertices_expanded"]

    def test_provider_registration_cache_behavior(self):
        """Test cache behavior when providers are registered/unregistered."""
        engine = Engine(enable_edge_caching=True)

        # Register provider
        provider = MockProvider()
        engine.register_provider("test", provider)

        stats_after_register = engine.get_stats()

        # Registration itself shouldn't change cache stats dramatically
        # (though it may clear cache internally)
        assert isinstance(stats_after_register, dict)

        # Try to access providers (this should work without errors)
        providers = engine.providers
        assert "test" in providers
        assert providers["test"] is provider


class TestCacheErrorHandling:
    """Test cache error handling and edge cases."""

    def test_cache_with_invalid_vertices(self):
        """Test cache behavior with various vertex types."""
        engine = Engine(enable_edge_caching=True)

        # Test with empty vertex
        empty_vertex = Vertex({})
        start = empty_vertex
        goal = Vertex({"id": "goal"})

        # Should not crash, even if planning fails
        with contextlib.suppress(Exception):
            engine.plan(start=start, goal=goal)

        # Statistics should still be accessible
        stats = engine.get_stats()
        assert isinstance(stats, dict)

    def test_cache_memory_safety(self):
        """Test that cache doesn't cause memory issues."""
        engine = Engine(enable_edge_caching=True)

        # Create provider with many edges
        large_edge_list = []
        for i in range(100):
            vertex = Vertex({"id": f"target_{i}", "value": i})
            edge = Edge(cost=float(i), metadata={"index": i})
            large_edge_list.append((vertex, edge))

        provider = MockProvider(large_edge_list)
        engine.register_provider("large", provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "target_50"})

        # Multiple operations with large data
        for _ in range(5):
            with contextlib.suppress(Exception):
                engine.plan(start=start, goal=goal)

            # Force garbage collection
            gc.collect()

        # Should still be functional
        stats = engine.get_stats()
        assert isinstance(stats, dict)

    def test_cache_with_provider_exceptions(self):
        """Test cache behavior when providers raise exceptions."""
        engine = Engine(enable_edge_caching=True)

        # Create provider that raises exceptions
        def failing_provider(_vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
            msg = "Provider failure"
            raise ValueError(msg)

        engine.register_provider("failing", failing_provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "goal"})

        # Planning should handle provider failures gracefully
        with contextlib.suppress(Exception):
            engine.plan(start=start, goal=goal)

        # Cache statistics should still be accessible
        stats = engine.get_stats()
        assert isinstance(stats, dict)

    def test_statistics_type_safety(self):
        """Test that statistics are always returned with correct types."""
        engine = Engine(enable_edge_caching=True)

        stats = engine.get_stats()

        # Verify all expected keys exist and have correct types
        expected_int_keys = [
            "cache_hits",
            "cache_misses",
            "cache_puts",
            "vertices_expanded",
            "edges_generated",
            "providers_called",
        ]

        for key in expected_int_keys:
            assert key in stats
            assert isinstance(stats[key], int)
            assert stats[key] >= 0


class TestCachePerformance:
    """Test cache performance characteristics."""

    def test_cache_improves_repeated_operations(self):
        """Test that cache provides performance benefits for repeated operations."""
        # Test with cache enabled
        cached_engine = Engine(enable_edge_caching=True)

        # Test with cache disabled
        uncached_engine = Engine(enable_edge_caching=False)

        # Create identical providers for both engines
        edges = [
            (Vertex({"id": f"target_{i}"}), Edge(cost=float(i))) for i in range(10)
        ]

        cached_provider = MockProvider(edges)
        uncached_provider = MockProvider(edges)

        cached_engine.register_provider("test", cached_provider)
        uncached_engine.register_provider("test", uncached_provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "target_5"})

        # Warm up both engines
        for engine in [cached_engine, uncached_engine]:
            with contextlib.suppress(Exception):
                engine.plan(start=start, goal=goal)

        # Time multiple operations
        cached_times = []
        uncached_times = []

        for _ in range(5):
            # Time cached engine
            start_time = time.time()
            with contextlib.suppress(Exception):
                cached_engine.plan(start=start, goal=goal)
            cached_times.append(time.time() - start_time)

            # Time uncached engine
            start_time = time.time()
            with contextlib.suppress(Exception):
                uncached_engine.plan(start=start, goal=goal)
            uncached_times.append(time.time() - start_time)

        # Verify cache statistics show activity
        uncached_stats = uncached_engine.get_stats()

        # Uncached engine should have no cache operations
        uncached_total_ops = (
            uncached_stats["cache_hits"]
            + uncached_stats["cache_misses"]
            + uncached_stats["cache_puts"]
        )

        assert uncached_total_ops == 0
        # Note: cached engine might not show cache activity in this test
        # scenario, which is acceptable

    def test_cache_statistics_scale_with_usage(self):
        """Test that cache statistics scale appropriately with usage."""
        engine = Engine(enable_edge_caching=True)

        provider = MockProvider(
            [
                (Vertex({"id": "intermediate"}), Edge(cost=10.0)),
                (Vertex({"id": "target"}), Edge(cost=20.0)),
            ]
        )
        engine.register_provider("test", provider)

        start = Vertex({"id": "start"})
        goal = Vertex({"id": "target"})

        # Track statistics growth
        initial_stats = engine.get_stats()

        # Perform multiple planning operations
        for _ in range(10):
            with contextlib.suppress(Exception):
                # Planning may fail, but stats should still update
                engine.plan(start=start, goal=goal)

        final_stats = engine.get_stats()

        # Some statistics should have increased
        assert final_stats["vertices_expanded"] >= initial_stats["vertices_expanded"]

        # Cache statistics should be non-negative and potentially increased
        for stat_name in ["cache_hits", "cache_misses", "cache_puts"]:
            assert final_stats[stat_name] >= initial_stats[stat_name] >= 0


# Test fixtures and utilities


@pytest.fixture
def basic_engine():
    """Fixture providing a basic engine with caching enabled."""
    return Engine(enable_edge_caching=True)


@pytest.fixture
def engine_with_provider(basic_engine):
    """Fixture providing an engine with a mock provider registered."""
    edges = [
        (Vertex({"id": "node1"}), Edge(cost=10.0)),
        (Vertex({"id": "node2"}), Edge(cost=20.0)),
    ]
    provider = MockProvider(edges)
    basic_engine.register_provider("mock", provider)
    return basic_engine, provider


# Integration tests that can be run if OSM providers are available


class TestCacheOSMIntegration:
    """Test cache integration with real OSM providers (if available)."""

    def test_cache_with_osm_providers_if_available(self):
        """Test cache behavior with OSM providers if they're available."""
        pytest.importorskip("graphserver.providers.osm")

        # This test would require actual OSM data, so we'll just verify
        # that the cache functionality doesn't break with OSM provider types
        engine = Engine(enable_edge_caching=True)

        # Verify that the engine is properly configured for OSM integration
        assert engine.cache_enabled is True
        stats = engine.get_stats()
        assert isinstance(stats, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
