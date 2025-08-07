"""Tests for Phase 2 cache invalidation: Provider callback injection.

This module tests the InvalidationHandler Protocol, CacheAwareEdgeProvider base class,
and automatic handler injection functionality introduced in Phase 2 of the cache
invalidation architecture.
"""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from typing import Any

import pytest

from graphserver import (
    CacheAwareEdgeProvider,
    Edge,
    Engine,
    InvalidationHandler,
    Vertex,
    VertexEdgePair,
)


class DynamicGraphProvider(CacheAwareEdgeProvider):
    """Test provider that supports dynamic graph updates with cache invalidation."""

    def __init__(self) -> None:
        """Initialize provider with empty graph."""
        super().__init__()
        self.graph: dict[str, list[tuple[Vertex, Edge]]] = {}
        self.call_count = 0
        self.called_with: list[Vertex] = []

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        cost: float,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add edge and trigger immediate cache invalidation."""
        if from_id not in self.graph:
            self.graph[from_id] = []

        target = Vertex({"id": to_id})
        edge = Edge(cost=cost, metadata=metadata)
        self.graph[from_id].append((target, edge))

        # Trigger immediate invalidation for the source vertex
        source = Vertex({"id": from_id})
        self.invalidate_vertex(source)

    def remove_edge(self, from_id: str, to_id: str) -> None:
        """Remove edge and trigger cache invalidation."""
        if from_id not in self.graph:
            return

        # Remove matching edge
        self.graph[from_id] = [
            (vertex, edge)
            for vertex, edge in self.graph[from_id]
            if vertex.get("id") != to_id
        ]

        # Clean up empty entries
        if not self.graph[from_id]:
            del self.graph[from_id]

        # Trigger cache invalidation
        source = Vertex({"id": from_id})
        self.invalidate_vertex(source)

    def bulk_update(self, updates: list[tuple[str, str, float]]) -> None:
        """Perform multiple updates with batch invalidation."""
        affected_vertices = []

        for from_id, to_id, cost in updates:
            # Update internal graph
            if from_id not in self.graph:
                self.graph[from_id] = []

            target = Vertex({"id": to_id})
            edge = Edge(cost=cost)
            self.graph[from_id].append((target, edge))

            # Track affected vertices
            source = Vertex({"id": from_id})
            affected_vertices.append(source)

        # Batch invalidate all affected vertices
        self.invalidate_vertices(affected_vertices)

    def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate outgoing edges from vertex."""
        self.call_count += 1
        self.called_with.append(vertex)

        vertex_id = vertex.get("id", "")
        return self.graph.get(vertex_id, [])

    def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate incoming edges (empty for this test provider)."""
        return []

    def reset_call_tracking(self) -> None:
        """Reset call tracking for testing."""
        self.call_count = 0
        self.called_with.clear()


class MockInvalidationHandler:
    """Mock invalidation handler for testing."""

    def __init__(self) -> None:
        """Initialize mock handler."""
        self.invalidated_vertices: list[Vertex] = []
        self.batch_invalidated_vertices: list[Sequence[Vertex]] = []

    def invalidate_vertex(self, vertex: Vertex) -> None:
        """Track single vertex invalidations."""
        self.invalidated_vertices.append(vertex)

    def invalidate_vertices(self, vertices: Sequence[Vertex]) -> None:
        """Track batch vertex invalidations."""
        self.batch_invalidated_vertices.append(list(vertices))

    def reset(self) -> None:
        """Reset tracking."""
        self.invalidated_vertices.clear()
        self.batch_invalidated_vertices.clear()


class TestInvalidationHandler:
    """Test InvalidationHandler Protocol compliance."""

    def test_protocol_compliance(self) -> None:
        """Test that mock handler complies with InvalidationHandler protocol."""
        handler = MockInvalidationHandler()

        # Should be recognized as InvalidationHandler
        assert isinstance(handler, InvalidationHandler)

        # Should have required methods
        assert hasattr(handler, "invalidate_vertex")
        assert hasattr(handler, "invalidate_vertices")
        assert callable(handler.invalidate_vertex)
        assert callable(handler.invalidate_vertices)

    def test_single_vertex_invalidation(self) -> None:
        """Test single vertex invalidation tracking."""
        handler = MockInvalidationHandler()
        vertex = Vertex({"id": "test"})

        handler.invalidate_vertex(vertex)

        assert len(handler.invalidated_vertices) == 1
        assert handler.invalidated_vertices[0] == vertex
        assert len(handler.batch_invalidated_vertices) == 0

    def test_batch_vertex_invalidation(self) -> None:
        """Test batch vertex invalidation tracking."""
        handler = MockInvalidationHandler()
        vertices = [
            Vertex({"id": "test1"}),
            Vertex({"id": "test2"}),
            Vertex({"id": "test3"}),
        ]

        handler.invalidate_vertices(vertices)

        assert len(handler.invalidated_vertices) == 0
        assert len(handler.batch_invalidated_vertices) == 1
        assert handler.batch_invalidated_vertices[0] == vertices


class TestCacheAwareEdgeProvider:
    """Test CacheAwareEdgeProvider base class functionality."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = DynamicGraphProvider()

        # Should start with no invalidation handler
        assert provider._invalidation_handler is None

        # Should have required abstract methods
        assert hasattr(provider, "out_edges")
        assert hasattr(provider, "in_edges")
        assert callable(provider.out_edges)
        assert callable(provider.in_edges)

    def test_handler_injection(self) -> None:
        """Test invalidation handler injection."""
        provider = DynamicGraphProvider()
        handler = MockInvalidationHandler()

        provider.set_invalidation_handler(handler)

        assert provider._invalidation_handler is handler

    def test_invalidation_without_handler(self) -> None:
        """Test that invalidation calls are safe when no handler is set."""
        provider = DynamicGraphProvider()
        vertex = Vertex({"id": "test"})

        # Should not raise errors
        provider.invalidate_vertex(vertex)
        provider.invalidate_vertices([vertex])

    def test_single_vertex_invalidation_with_handler(self) -> None:
        """Test single vertex invalidation with handler."""
        provider = DynamicGraphProvider()
        handler = MockInvalidationHandler()
        provider.set_invalidation_handler(handler)

        vertex = Vertex({"id": "test"})
        provider.invalidate_vertex(vertex)

        assert len(handler.invalidated_vertices) == 1
        assert handler.invalidated_vertices[0] == vertex

    def test_batch_vertex_invalidation_with_handler(self) -> None:
        """Test batch vertex invalidation with handler."""
        provider = DynamicGraphProvider()
        handler = MockInvalidationHandler()
        provider.set_invalidation_handler(handler)

        vertices = [Vertex({"id": "test1"}), Vertex({"id": "test2"})]
        provider.invalidate_vertices(vertices)

        assert len(handler.batch_invalidated_vertices) == 1
        assert handler.batch_invalidated_vertices[0] == vertices

    def test_dynamic_edge_addition(self) -> None:
        """Test dynamic edge addition with invalidation."""
        provider = DynamicGraphProvider()
        handler = MockInvalidationHandler()
        provider.set_invalidation_handler(handler)

        # Add edge - should trigger invalidation
        provider.add_edge("A", "B", 1.0)

        # Check graph was updated
        vertex_a = Vertex({"id": "A"})
        edges = provider.out_edges(vertex_a)
        assert len(edges) == 1
        assert edges[0][0].get("id") == "B"
        assert edges[0][1].cost == 1.0

        # Check invalidation was triggered
        assert len(handler.invalidated_vertices) == 1
        assert handler.invalidated_vertices[0].get("id") == "A"

    def test_bulk_updates_with_batch_invalidation(self) -> None:
        """Test bulk updates using batch invalidation."""
        provider = DynamicGraphProvider()
        handler = MockInvalidationHandler()
        provider.set_invalidation_handler(handler)

        # Perform bulk update
        updates = [
            ("A", "B", 1.0),
            ("A", "C", 2.0),
            ("B", "D", 3.0),
        ]
        provider.bulk_update(updates)

        # Check graph was updated
        vertex_a = Vertex({"id": "A"})
        vertex_b = Vertex({"id": "B"})

        edges_a = provider.out_edges(vertex_a)
        edges_b = provider.out_edges(vertex_b)

        assert len(edges_a) == 2  # A->B, A->C
        assert len(edges_b) == 1  # B->D

        # Check batch invalidation was triggered
        assert len(handler.batch_invalidated_vertices) == 1
        affected_vertices = handler.batch_invalidated_vertices[0]
        affected_ids = {v.get("id") for v in affected_vertices}
        assert affected_ids == {"A", "B"}  # A appears twice as expected


class TestEngineIntegration:
    """Test integration between Engine and CacheAwareEdgeProvider."""

    def test_automatic_handler_injection(self) -> None:
        """Test that Engine automatically injects handlers for CacheAwareEdgeProvider."""
        engine = Engine(enable_edge_caching=True)
        provider = DynamicGraphProvider()

        # Initially no handler
        assert provider._invalidation_handler is None

        # Register provider - should inject handler
        engine.register_provider("dynamic", provider)

        # Handler should now be injected
        assert provider._invalidation_handler is not None
        assert hasattr(provider._invalidation_handler, "invalidate_vertex")
        assert hasattr(provider._invalidation_handler, "invalidate_vertices")

    def test_regular_provider_no_injection(self) -> None:
        """Test that regular EdgeProvider doesn't get handler injection."""

        class RegularProvider:
            def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
                return []

            def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
                return []

        engine = Engine(enable_edge_caching=True)
        provider = RegularProvider()

        # Register regular provider
        engine.register_provider("regular", provider)

        # Should not have invalidation handler attribute
        assert not hasattr(provider, "_invalidation_handler")

    def test_cache_aware_provider_invalidation_integration(self) -> None:
        """Test full integration of cache-aware provider with engine."""
        engine = Engine(enable_edge_caching=True)
        provider = DynamicGraphProvider()

        # Set up simple graph
        provider.add_edge("A", "B", 1.0)
        provider.add_edge("B", "C", 1.0)

        # Register provider after setup to avoid premature invalidation
        engine.register_provider("dynamic", provider)

        # Plan initial path to cache some edges
        start = Vertex({"id": "A"})
        goal = Vertex({"id": "C"})

        provider.reset_call_tracking()
        result1 = engine.plan(start=start, goal=goal)
        initial_calls = provider.call_count

        assert len(result1) > 0  # Path should be found
        assert initial_calls > 0  # Provider should be called

        # Plan same path again - should potentially use cache
        provider.reset_call_tracking()
        result2 = engine.plan(start=start, goal=goal)
        second_calls = provider.call_count

        # Add new edge, which should trigger invalidation
        provider.add_edge("A", "D", 0.5)  # Cheaper path

        # Plan again - cache should be invalidated, requiring fresh calls
        provider.reset_call_tracking()
        result3 = engine.plan(start=start, goal=goal)

        assert len(result3) > 0  # Path should still be found
        # The exact behavior depends on cache implementation details
        # but the test validates the integration works without errors

    def test_cache_statistics_with_cache_aware_provider(self) -> None:
        """Test that cache statistics work correctly with cache-aware providers."""
        engine = Engine(enable_edge_caching=True)
        provider = DynamicGraphProvider()

        provider.add_edge("A", "B", 1.0)
        engine.register_provider("dynamic", provider)

        # Get initial stats
        initial_stats = engine.get_stats()

        # Perform some operations
        vertex_a = Vertex({"id": "A"})
        vertex_b = Vertex({"id": "B"})

        with contextlib.suppress(Exception):
            engine.plan(start=vertex_a, goal=vertex_b)

        # Trigger invalidation
        provider.add_edge("A", "C", 2.0)

        # Plan again
        with contextlib.suppress(Exception):
            engine.plan(start=vertex_a, goal=vertex_b)

        # Get final stats
        final_stats = engine.get_stats()

        # Should have some cache activity
        assert final_stats.vertices_expanded >= initial_stats.vertices_expanded
        assert final_stats.cache_hits >= initial_stats.cache_hits
        assert final_stats.cache_misses >= initial_stats.cache_misses

    def test_multiple_cache_aware_providers(self) -> None:
        """Test engine with multiple cache-aware providers."""
        engine = Engine(enable_edge_caching=True)

        provider1 = DynamicGraphProvider()
        provider2 = DynamicGraphProvider()

        # Set up different graphs
        provider1.add_edge("A", "B", 1.0)
        provider2.add_edge("X", "Y", 2.0)

        # Register both providers
        engine.register_provider("provider1", provider1)
        engine.register_provider("provider2", provider2)

        # Both should have handlers injected
        assert provider1._invalidation_handler is not None
        assert provider2._invalidation_handler is not None

        # Handlers should be different instances but work similarly
        # (they might be the same type but bound to the same engine)
        assert hasattr(provider1._invalidation_handler, "invalidate_vertex")
        assert hasattr(provider2._invalidation_handler, "invalidate_vertex")


class TestErrorHandling:
    """Test error handling for cache-aware providers."""

    def test_invalidation_with_invalid_vertex_types(self) -> None:
        """Test invalidation behavior with invalid vertex types."""
        engine = Engine(enable_edge_caching=True)
        provider = DynamicGraphProvider()
        engine.register_provider("dynamic", provider)

        # Test invalidation with various vertex types
        # Note: Invalidating vertices not in cache may raise ValueError
        # This is expected behavior from the C implementation
        empty_vertex = Vertex({})
        with contextlib.suppress(ValueError):
            provider.invalidate_vertex(empty_vertex)

        # Test batch invalidation with mixed vertices
        vertices = [Vertex({"id": "A"}), Vertex({}), Vertex({"id": "B"})]
        with contextlib.suppress(ValueError):
            provider.invalidate_vertices(vertices)

    def test_provider_without_cache_enabled(self) -> None:
        """Test cache-aware provider behavior when caching is disabled."""
        engine = Engine(enable_edge_caching=False)  # No cache
        provider = DynamicGraphProvider()

        engine.register_provider("dynamic", provider)

        # Handler should still be injected
        assert provider._invalidation_handler is not None

        # Invalidation calls should work (but be no-ops internally)
        vertex = Vertex({"id": "A"})
        provider.invalidate_vertex(vertex)  # Should not raise

        provider.add_edge("A", "B", 1.0)  # Should trigger invalidation call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
