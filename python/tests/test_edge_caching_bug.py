"""Integration test demonstrating cache invalidation with dynamic graph updates.

This test shows how cache invalidation enables proper discovery of new edges when
providers are modified after initial vertex expansion, solving the edge caching bug.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from graphserver import CacheAwareEdgeProvider, Edge, Engine, Vertex


class DynamicMockProvider(CacheAwareEdgeProvider):
    """Mock provider that allows runtime modification of edges."""

    def __init__(self):
        """Initialize with empty edge map."""
        super().__init__()  # Initialize CacheAwareEdgeProvider
        self.edge_map: dict[str, list[tuple[Vertex, Edge]]] = {}
        self.call_count = 0
        self.called_with: list[Vertex] = []

    def add_edges(self, from_vertex_id: str, edges: list[tuple[Vertex, Edge]]) -> None:
        """Add edges from a vertex and invalidate its cache if needed."""
        self.edge_map[from_vertex_id] = edges
        # Invalidate cache for the modified vertex so new edges are discovered
        # Use try/except to handle case where vertex hasn't been cached yet
        try:
            self.invalidate_vertex(Vertex({"id": from_vertex_id}))
        except ValueError:
            # Vertex not in cache yet, no need to invalidate
            pass

    def out_edges(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Return outgoing edges for a vertex."""
        self.call_count += 1
        self.called_with.append(vertex)
        
        vertex_id = vertex.get("id", "")
        return self.edge_map.get(vertex_id, [])

    def in_edges(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Return incoming edges for a vertex."""
        # For simplicity, return empty list for incoming edges
        return []

    def reset_call_tracking(self) -> None:
        """Reset call tracking without modifying edges."""
        self.call_count = 0
        self.called_with.clear()


class TestEdgeCachingBug:
    """Test case demonstrating cache invalidation solving the edge caching problem."""

    def test_cache_invalidation_enables_new_edge_discovery(self):
        """Test that cache invalidation enables discovery of dynamically added edges.
        
        This test demonstrates how cache invalidation solves the edge caching problem:
        1. Route A->B->C is found and B's edges are cached
        2. Provider is modified to add B->D edge with cache invalidation
        3. Route A->D succeeds because cache invalidation allows new edge discovery
        
        This test demonstrates the cache invalidation solution working correctly.
        """
        # Create engine with edge caching enabled
        engine = Engine(enable_edge_caching=True)
        assert engine.cache_enabled
        
        # Create dynamic provider
        provider = DynamicMockProvider()
        engine.register_provider("dynamic", provider)
        
        # Create vertices
        vertex_a = Vertex({"id": "A"})
        vertex_b = Vertex({"id": "B"}) 
        vertex_c = Vertex({"id": "C"})
        vertex_d = Vertex({"id": "D"})
        
        # Set up initial graph: A->B->C
        provider.add_edges("A", [(vertex_b, Edge(cost=1.0))])
        provider.add_edges("B", [(vertex_c, Edge(cost=1.0))])
        provider.add_edges("C", [])  # C has no outgoing edges
        
        # Find route A->B->C (this will cache B's edges)
        result_abc = engine.plan(start=vertex_a, goal=vertex_c)
        assert result_abc is not None
        assert len(result_abc) == 2  # A->B, B->C
        
        # Verify the path is correct
        assert result_abc[0].target["id"] == "B"
        assert result_abc[1].target["id"] == "C"
        
        # Check that provider was called for vertex B
        b_was_called = any(v.get("id") == "B" for v in provider.called_with)
        assert b_was_called, "Provider should have been called for vertex B"
        
        # Reset call tracking to monitor subsequent calls
        provider.reset_call_tracking()
        
        # SOLUTION: Modify provider to add B->D edge with cache invalidation
        # The CacheAwareEdgeProvider will automatically invalidate B's cache
        provider.add_edges("B", [(vertex_c, Edge(cost=1.0)), (vertex_d, Edge(cost=2.0))])
        
        # Try to find route A->D
        # This SHOULD now work because cache invalidation allows new edge discovery
        result_ad = engine.plan(start=vertex_a, goal=vertex_d)
        
        # Verify the route was found successfully
        assert result_ad is not None, "Route A->D should succeed with cache invalidation"
        assert len(result_ad) == 2  # A->B, B->D
        assert result_ad[0].target["id"] == "B"
        assert result_ad[1].target["id"] == "D"
        
        # Check if provider was called for B again (it should be due to invalidation)
        b_called_again = any(v.get("id") == "B" for v in provider.called_with)
        
        # Verify cache invalidation caused provider to be called again
        assert b_called_again, (
            "Provider should be called again for B after cache invalidation. "
            "This ensures the new B->D edge is discovered."
        )
        
        print("SUCCESS: Cache invalidation enabled discovery of new B->D edge")
        print(f"Route A->D found: A->B (cost: {result_ad[0].edge.cost}) -> D (cost: {result_ad[1].edge.cost})")

    def test_cache_invalidation_statistics(self):
        """Verify cache statistics show proper invalidation behavior."""
        engine = Engine(enable_edge_caching=True)
        provider = DynamicMockProvider()
        engine.register_provider("dynamic", provider)
        
        # Set up A->B->C graph
        vertex_a = Vertex({"id": "A"})
        vertex_b = Vertex({"id": "B"})
        vertex_c = Vertex({"id": "C"})
        vertex_d = Vertex({"id": "D"})
        
        provider.add_edges("A", [(vertex_b, Edge(cost=1.0))])
        provider.add_edges("B", [(vertex_c, Edge(cost=1.0))])
        
        # Get initial stats
        initial_stats = engine.get_stats()
        
        # Find A->B->C route 
        engine.plan(start=vertex_a, goal=vertex_c)
        
        # Get stats after first planning
        stats_after_first = engine.get_stats()
        assert stats_after_first.vertices_expanded >= initial_stats.vertices_expanded
        
        # Add B->D edge with cache invalidation
        provider.add_edges("B", [(vertex_c, Edge(cost=1.0)), (vertex_d, Edge(cost=2.0))])
        
        # Try A->D route - should succeed with cache invalidation
        result_ad = engine.plan(start=vertex_a, goal=vertex_d)
        
        # Verify route was found
        assert result_ad is not None, "Route A->D should be found with cache invalidation"
        assert len(result_ad) == 2  # A->B, B->D
        assert result_ad[1].target["id"] == "D"
        
        # Get final stats
        final_stats = engine.get_stats()
        
        # Verify cache statistics show invalidation behavior
        # There should be cache activity and the route should be successfully found
        assert final_stats.vertices_expanded > stats_after_first.vertices_expanded, (
            "Should have expanded more vertices to find the A->D route"
        )
        
        print(f"Cache hits: {stats_after_first.cache_hits} -> {final_stats.cache_hits}")
        print(f"Cache misses: {stats_after_first.cache_misses} -> {final_stats.cache_misses}")
        print("Cache invalidation successfully enabled discovery of A->D route")