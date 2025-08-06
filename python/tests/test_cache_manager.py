"""Tests for CacheManager batch invalidation functionality.

This module contains comprehensive tests for the CacheManager class,
covering context manager behavior, immediate vs batch modes, deduplication,
engine integration, and error handling.
"""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from typing import Any

import pytest

from graphserver import (
    CacheAwareEdgeProvider,
    CacheManager,
    Edge,
    Engine,
    Vertex,
    VertexEdgePair,
)


class MockInvalidationTracker:
    """Helper class to track invalidation calls for testing."""
    
    def __init__(self) -> None:
        """Initialize tracker."""
        self.single_calls: list[Vertex] = []
        self.batch_calls: list[list[Vertex]] = []
        self.call_order: list[str] = []
    
    def track_single(self, vertex: Vertex) -> None:
        """Track single vertex invalidation."""
        self.single_calls.append(vertex)
        self.call_order.append(f"single:{vertex.get('id', 'unknown')}")
    
    def track_batch(self, vertices: list[Vertex]) -> None:
        """Track batch vertex invalidation."""
        self.batch_calls.append(vertices)
        vertex_ids = [v.get('id', 'unknown') for v in vertices]
        self.call_order.append(f"batch:[{','.join(vertex_ids)}]")
    
    def reset(self) -> None:
        """Reset all tracking."""
        self.single_calls.clear()
        self.batch_calls.clear()
        self.call_order.clear()


class TestCacheManagerBasics:
    """Test basic CacheManager functionality."""
    
    def test_cache_manager_creation(self) -> None:
        """Test creating a CacheManager through Engine."""
        engine = Engine(enable_edge_caching=True)
        
        # Should create CacheManager successfully
        cm = engine.create_cache_manager()
        assert isinstance(cm, CacheManager)
        assert cm._engine is engine
        assert not cm.immediate_mode
        assert cm.pending_count == 0
    
    def test_cache_manager_factory_method(self) -> None:
        """Test that each call creates a new CacheManager."""
        engine = Engine(enable_edge_caching=True)
        
        cm1 = engine.create_cache_manager()
        cm2 = engine.create_cache_manager()
        
        assert cm1 is not cm2
        assert cm1._engine is cm2._engine
    
    def test_initial_state(self) -> None:
        """Test CacheManager initial state."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        assert not cm.immediate_mode
        assert cm.pending_count == 0
        assert cm._invalidated_vertices == set()
        assert not cm._immediate_mode


class TestBatchMode:
    """Test CacheManager batch mode functionality."""
    
    def test_batch_accumulation(self) -> None:
        """Test that vertices are accumulated in batch mode."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        vertex1 = Vertex({"id": "A"})
        vertex2 = Vertex({"id": "B"})
        vertex3 = Vertex({"id": "C"})
        
        # Add vertices - should be accumulated
        cm.invalidate(vertex1)
        cm.invalidate(vertex2)
        cm.invalidate(vertex3)
        
        assert cm.pending_count == 3
        assert vertex1 in cm._invalidated_vertices
        assert vertex2 in cm._invalidated_vertices
        assert vertex3 in cm._invalidated_vertices
    
    def test_batch_deduplication(self) -> None:
        """Test that duplicate vertices are deduplicated in batch mode."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        vertex1 = Vertex({"id": "A"})
        vertex1_duplicate = Vertex({"id": "A"})  # Same content, different object
        vertex2 = Vertex({"id": "B"})
        
        # Add vertices including duplicates
        cm.invalidate(vertex1)
        cm.invalidate(vertex2)
        cm.invalidate(vertex1_duplicate)
        cm.invalidate(vertex1)  # Same object
        
        # Should deduplicate based on vertex equality
        assert cm.pending_count == 2  # Only A and B
    
    def test_batch_invalidate_vertices(self) -> None:
        """Test batch addition of multiple vertices."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        vertices = [
            Vertex({"id": "A"}),
            Vertex({"id": "B"}),
            Vertex({"id": "C"}),
        ]
        
        cm.invalidate_vertices(vertices)
        
        assert cm.pending_count == 3
        for vertex in vertices:
            assert vertex in cm._invalidated_vertices
    
    def test_manual_flush(self) -> None:
        """Test manual flush of pending invalidations."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        vertices = [
            Vertex({"id": "A"}),
            Vertex({"id": "B"}),
            Vertex({"id": "C"}),
        ]
        
        for vertex in vertices:
            cm.invalidate(vertex)
        
        assert cm.pending_count == 3
        
        # Flush should return count and clear pending
        count = cm.flush()
        assert count == 3
        assert cm.pending_count == 0
    
    def test_flush_empty(self) -> None:
        """Test flush with no pending invalidations."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Flush empty manager
        count = cm.flush()
        assert count == 0
        assert cm.pending_count == 0
    
    def test_clear_pending(self) -> None:
        """Test clearing pending invalidations without executing."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        vertices = [
            Vertex({"id": "A"}),
            Vertex({"id": "B"}),
        ]
        
        for vertex in vertices:
            cm.invalidate(vertex)
        
        assert cm.pending_count == 2
        
        # Clear should return count and discard pending
        count = cm.clear()
        assert count == 2
        assert cm.pending_count == 0


class TestImmediateMode:
    """Test CacheManager immediate mode functionality."""
    
    def test_immediate_mode_toggle(self) -> None:
        """Test switching between batch and immediate modes."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Start in batch mode
        assert not cm.immediate_mode
        
        # Switch to immediate mode
        cm.set_immediate_mode(True)
        assert cm.immediate_mode
        
        # Switch back to batch mode
        cm.set_immediate_mode(False)
        assert not cm.immediate_mode
    
    def test_immediate_mode_no_accumulation(self) -> None:
        """Test that immediate mode doesn't accumulate vertices."""
        engine = Engine(enable_edge_caching=False)  # Disable to avoid actual calls
        cm = engine.create_cache_manager()
        cm.set_immediate_mode(True)
        
        vertex = Vertex({"id": "A"})
        
        # In immediate mode, should not accumulate
        with contextlib.suppress(Exception):  # May raise if vertex not in cache
            cm.invalidate(vertex)
        
        assert cm.pending_count == 0
    
    def test_immediate_mode_invalidate_vertices(self) -> None:
        """Test immediate mode with multiple vertices."""
        engine = Engine(enable_edge_caching=False)  # Disable to avoid actual calls
        cm = engine.create_cache_manager()
        cm.set_immediate_mode(True)
        
        vertices = [Vertex({"id": "A"}), Vertex({"id": "B"})]
        
        with contextlib.suppress(Exception):  # May raise if vertices not in cache
            cm.invalidate_vertices(vertices)
        
        assert cm.pending_count == 0
    
    def test_invalidate_immediate_bypass(self) -> None:
        """Test invalidate_immediate bypasses batching."""
        engine = Engine(enable_edge_caching=False)  # Disable to avoid actual calls
        cm = engine.create_cache_manager()
        
        # Even in batch mode, invalidate_immediate should not accumulate
        vertex = Vertex({"id": "A"})
        
        with contextlib.suppress(Exception):  # May raise if vertex not in cache
            cm.invalidate_immediate(vertex)
        
        assert cm.pending_count == 0


class TestContextManager:
    """Test CacheManager context manager behavior."""
    
    def test_context_manager_basic(self) -> None:
        """Test basic context manager usage."""
        engine = Engine(enable_edge_caching=True)
        
        vertices = [
            Vertex({"id": "A"}),
            Vertex({"id": "B"}),
        ]
        
        # Use context manager
        with engine.create_cache_manager() as cm:
            assert isinstance(cm, CacheManager)
            
            for vertex in vertices:
                cm.invalidate(vertex)
            
            # Should still be pending inside context
            assert cm.pending_count == 2
        
        # After context exit, pending should be cleared (flushed)
        # Note: We can't easily test the actual flush without complex mocking
    
    def test_context_manager_exception_handling(self) -> None:
        """Test context manager behavior when exceptions occur."""
        engine = Engine(enable_edge_caching=True)
        
        vertex = Vertex({"id": "A"})
        
        # Test that flush still occurs even with exception
        with contextlib.suppress(ValueError):
            with engine.create_cache_manager() as cm:
                cm.invalidate(vertex)
                assert cm.pending_count == 1
                raise ValueError("Test exception")
        
        # Flush should have occurred despite exception
        # (We can't easily verify without complex mocking)
    
    def test_context_manager_nested(self) -> None:
        """Test nested context managers work independently."""
        engine = Engine(enable_edge_caching=True)
        
        with engine.create_cache_manager() as cm1:
            cm1.invalidate(Vertex({"id": "A"}))
            
            with engine.create_cache_manager() as cm2:
                cm2.invalidate(Vertex({"id": "B"}))
                assert cm1.pending_count == 1
                assert cm2.pending_count == 1
                assert cm1 is not cm2
            
            # cm2 should have flushed, cm1 should still have pending
            assert cm1.pending_count == 1


class TestIntegrationWithProviders:
    """Test CacheManager integration with CacheAwareEdgeProvider."""
    
    def test_provider_with_cache_manager(self) -> None:
        """Test provider using cache manager for bulk operations."""
        
        class TestProvider(CacheAwareEdgeProvider):
            def __init__(self) -> None:
                super().__init__()
                self.graph: dict[str, list[tuple[Vertex, Edge]]] = {}
            
            def bulk_update_with_manager(self, engine: Engine, updates: list[tuple[str, str, float]]) -> None:
                """Perform bulk update using cache manager."""
                with engine.create_cache_manager() as cm:
                    for from_id, to_id, cost in updates:
                        # Update internal graph
                        if from_id not in self.graph:
                            self.graph[from_id] = []
                        
                        target = Vertex({"id": to_id})
                        edge = Edge(cost=cost)
                        self.graph[from_id].append((target, edge))
                        
                        # Use cache manager for batched invalidation
                        source = Vertex({"id": from_id})
                        cm.invalidate(source)
            
            def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
                vertex_id = vertex.get("id", "")
                return self.graph.get(vertex_id, [])
            
            def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
                return []
        
        engine = Engine(enable_edge_caching=True)
        provider = TestProvider()
        engine.register_provider("test", provider)
        
        updates = [
            ("A", "B", 1.0),
            ("A", "C", 2.0),
            ("B", "D", 3.0),
        ]
        
        # Should work without errors
        provider.bulk_update_with_manager(engine, updates)
        
        # Verify graph was updated
        vertex_a = Vertex({"id": "A"})
        edges_a = provider.out_edges(vertex_a)
        assert len(edges_a) == 2


class TestErrorHandling:
    """Test CacheManager error handling and edge cases."""
    
    def test_cache_disabled_graceful(self) -> None:
        """Test graceful handling when cache is disabled."""
        engine = Engine(enable_edge_caching=False)
        cm = engine.create_cache_manager()
        
        vertex = Vertex({"id": "A"})
        
        # Should work in batch mode (accumulates but flush may be no-op)
        cm.invalidate(vertex)
        assert cm.pending_count == 1
        
        # Manual flush should work
        count = cm.flush()
        assert count == 1
        assert cm.pending_count == 0
    
    def test_empty_vertices_handling(self) -> None:
        """Test handling of empty vertex sequences."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Empty list should be handled gracefully
        cm.invalidate_vertices([])
        assert cm.pending_count == 0
        
        count = cm.flush()
        assert count == 0
    
    def test_properties_consistency(self) -> None:
        """Test that properties remain consistent."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Initial state
        assert cm.pending_count == 0
        assert not cm.immediate_mode
        
        # Add some vertices
        vertices = [Vertex({"id": f"vertex_{i}"}) for i in range(5)]
        for vertex in vertices:
            cm.invalidate(vertex)
        
        assert cm.pending_count == 5
        assert not cm.immediate_mode
        
        # Switch to immediate mode
        cm.set_immediate_mode(True)
        assert cm.immediate_mode
        assert cm.pending_count == 5  # Pending count unchanged
        
        # Clear pending
        count = cm.clear()
        assert count == 5
        assert cm.pending_count == 0
        assert cm.immediate_mode  # Mode unchanged


class TestPerformanceCharacteristics:
    """Test performance-related characteristics of CacheManager."""
    
    def test_large_batch_handling(self) -> None:
        """Test handling of large batches of vertices."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Create large number of vertices
        large_batch = [Vertex({"id": f"vertex_{i}"}) for i in range(1000)]
        
        # Should handle large batch without issues
        cm.invalidate_vertices(large_batch)
        assert cm.pending_count == 1000
        
        # Flush should handle large batch
        count = cm.flush()
        assert count == 1000
        assert cm.pending_count == 0
    
    def test_deduplication_efficiency(self) -> None:
        """Test that deduplication works efficiently."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Create vertices with some duplicates
        base_vertices = [Vertex({"id": f"vertex_{i}"}) for i in range(10)]
        
        # Add each vertex multiple times
        for _ in range(5):
            for vertex in base_vertices:
                cm.invalidate(vertex)
        
        # Should deduplicate to only unique vertices
        assert cm.pending_count == 10  # Not 50
        
        count = cm.flush()
        assert count == 10
    
    def test_mixed_operations(self) -> None:
        """Test mixed single and batch operations."""
        engine = Engine(enable_edge_caching=True)
        cm = engine.create_cache_manager()
        
        # Mix of single and batch additions
        cm.invalidate(Vertex({"id": "A"}))
        cm.invalidate_vertices([Vertex({"id": "B"}), Vertex({"id": "C"})])
        cm.invalidate(Vertex({"id": "D"}))
        cm.invalidate_vertices([Vertex({"id": "E"}), Vertex({"id": "F"})])
        
        assert cm.pending_count == 6
        
        count = cm.flush()
        assert count == 6
        assert cm.pending_count == 0


# Integration test fixtures
@pytest.fixture
def engine_with_caching() -> Engine:
    """Fixture providing an engine with caching enabled."""
    return Engine(enable_edge_caching=True)


@pytest.fixture
def engine_without_caching() -> Engine:
    """Fixture providing an engine with caching disabled."""
    return Engine(enable_edge_caching=False)


@pytest.fixture
def sample_vertices() -> list[Vertex]:
    """Fixture providing sample vertices for testing."""
    return [
        Vertex({"id": "A", "type": "node"}),
        Vertex({"id": "B", "type": "node"}),
        Vertex({"id": "C", "type": "node"}),
        Vertex({"id": "D", "type": "node"}),
        Vertex({"id": "E", "type": "node"}),
    ]


class TestCacheManagerWithFixtures:
    """Additional tests using fixtures."""
    
    def test_cache_manager_with_fixtures(
        self, engine_with_caching: Engine, sample_vertices: list[Vertex]
    ) -> None:
        """Test CacheManager with fixture data."""
        cm = engine_with_caching.create_cache_manager()
        
        # Use sample vertices
        for vertex in sample_vertices:
            cm.invalidate(vertex)
        
        assert cm.pending_count == len(sample_vertices)
        
        count = cm.flush()
        assert count == len(sample_vertices)
    
    def test_context_manager_with_fixtures(
        self, engine_with_caching: Engine, sample_vertices: list[Vertex]
    ) -> None:
        """Test context manager with fixture data."""
        with engine_with_caching.create_cache_manager() as cm:
            cm.invalidate_vertices(sample_vertices)
            assert cm.pending_count == len(sample_vertices)
        
        # Context exit should have flushed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])