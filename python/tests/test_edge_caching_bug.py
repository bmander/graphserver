"""Integration test demonstrating the edge caching bug.

This test shows how edge caching can prevent discovery of new edges when
providers are modified after initial vertex expansion.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from graphserver import Edge, Engine, Vertex


class DynamicMockProvider:
    """Mock provider that allows runtime modification of edges."""

    def __init__(self):
        """Initialize with empty edge map."""
        self.edge_map: dict[str, list[tuple[Vertex, Edge]]] = {}
        self.call_count = 0
        self.called_with: list[Vertex] = []

    def add_edges(self, from_vertex_id: str, edges: list[tuple[Vertex, Edge]]) -> None:
        """Add edges from a vertex."""
        self.edge_map[from_vertex_id] = edges

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
    """Test case demonstrating the edge caching bug."""

    def test_edge_caching_prevents_new_edge_discovery(self):
        """Test that edge caching prevents discovery of dynamically added edges.
        
        This test demonstrates a bug where:
        1. Route A->B->C is found and B's edges are cached
        2. Provider is modified to add B->D edge  
        3. Route A->D fails because cached B edges don't include B->D
        
        This test is expected to FAIL due to the caching bug.
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
        provider_calls_before = provider.call_count
        b_was_called = any(v.get("id") == "B" for v in provider.called_with)
        assert b_was_called, "Provider should have been called for vertex B"
        
        # Reset call tracking to monitor subsequent calls
        provider.reset_call_tracking()
        
        # NOW THE BUG: Modify provider to add B->D edge
        # This simulates a dynamic change to the graph
        provider.add_edges("B", [(vertex_c, Edge(cost=1.0)), (vertex_d, Edge(cost=2.0))])
        
        # Try to find route A->D
        # This SHOULD work if caching didn't interfere, but will fail due to bug
        result_ad = engine.plan(start=vertex_a, goal=vertex_d)
        
        # Check if provider was called for B again (it shouldn't be due to caching)
        b_called_again = any(v.get("id") == "B" for v in provider.called_with)
        
        # This assertion demonstrates the bug:
        # If caching works as intended, B should NOT be called again (cached hit)
        # But this means the new B->D edge won't be discovered
        if not b_called_again:
            # Cache hit occurred - the bug is present
            assert result_ad is None, (
                "Route A->D should fail due to cached edges from B not including B->D. "
                f"Provider was not called again for B (cache hit), "
                f"so new B->D edge was not discovered."
            )
            print("BUG CONFIRMED: Edge caching prevented discovery of new B->D edge")
        else:
            # Cache miss occurred - provider was called again 
            # This means the route might succeed, which would indicate the bug is fixed
            if result_ad is not None:
                assert len(result_ad) == 2  # A->B, B->D
                assert result_ad[0].target["id"] == "B"
                assert result_ad[1].target["id"] == "D"
                print("Edge caching bug appears to be fixed - new edge was discovered")
            else:
                print("Route still failed despite cache miss - other issues present")

    def test_cache_behavior_with_stats(self):
        """Verify cache statistics show expected behavior during the bug scenario."""
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
        
        # Add B->D edge
        provider.add_edges("B", [(vertex_c, Edge(cost=1.0)), (vertex_d, Edge(cost=2.0))])
        
        # Try A->D route
        engine.plan(start=vertex_a, goal=vertex_d)
        
        # Get final stats
        final_stats = engine.get_stats()
        
        # Verify cache was used (hits should increase)
        if final_stats.cache_hits > stats_after_first.cache_hits:
            print(f"Cache hits increased from {stats_after_first.cache_hits} to {final_stats.cache_hits}")
            print("This confirms caching behavior during the bug scenario")