"""Tests for bidirectional provider support.

This module tests the new bidirectional provider functionality,
including out_edges and in_edges method support.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from graphserver import Edge, Engine, Vertex


class BidirectionalProvider:
    """Test provider that supports both incoming and outgoing edges."""

    def __init__(self):
        """Initialize the provider."""
        self.call_count = 0
        self.out_edges_calls = 0
        self.in_edges_calls = 0

    def out_edges(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Generate outgoing edges from a vertex."""
        self.call_count += 1
        self.out_edges_calls += 1

        # Simple test: generate one edge to a target vertex
        x = vertex.get("x", 0)
        y = vertex.get("y", 0)

        # Generate edge to adjacent cell (east)
        target = Vertex({"x": x + 1, "y": y})
        edge = Edge(cost=1.0, metadata={"direction": "east"})

        return [(target, edge)]

    def in_edges(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Generate incoming edges to a vertex."""
        self.call_count += 1
        self.in_edges_calls += 1

        # Simple test: generate one edge from a source vertex
        x = vertex.get("x", 0)
        y = vertex.get("y", 0)

        # Generate edge from adjacent cell (west)
        source = Vertex({"x": x - 1, "y": y})
        edge = Edge(cost=1.0, metadata={"direction": "west"})

        return [(source, edge)]


class OutgoingOnlyProvider:
    """Test provider that only supports outgoing edges."""

    def __init__(self):
        """Initialize the provider."""
        self.call_count = 0

    def out_edges(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Generate outgoing edges from a vertex."""
        self.call_count += 1

        x = vertex.get("x", 0)
        y = vertex.get("y", 0)

        target = Vertex({"x": x + 1, "y": y})
        edge = Edge(cost=2.0)

        return [(target, edge)]

    def in_edges(self, vertex: Vertex) -> Sequence[tuple[Vertex, Edge]]:
        """Raise NotImplementedError for incoming edges."""
        msg = "This provider does not support incoming edges"
        raise NotImplementedError(msg)


class TestBidirectionalProviders:
    """Test bidirectional provider functionality."""

    def test_bidirectional_provider_registration(self):
        """Test that bidirectional providers can be registered."""
        engine = Engine(enable_edge_caching=True)
        provider = BidirectionalProvider()

        # Should register without errors
        engine.register_provider("bidirectional", provider)

        # Verify registration
        assert "bidirectional" in engine.providers
        assert engine.providers["bidirectional"] is provider

    def test_outgoing_only_provider_registration(self):
        """Test that outgoing-only providers can be registered."""
        engine = Engine(enable_edge_caching=True)
        provider = OutgoingOnlyProvider()

        # Should register without errors
        engine.register_provider("outgoing_only", provider)

        # Verify registration
        assert "outgoing_only" in engine.providers
        assert engine.providers["outgoing_only"] is provider

    def test_bidirectional_provider_functionality(self):
        """Test that bidirectional providers work correctly."""
        engine = Engine(enable_edge_caching=False)  # Disable cache for direct testing
        provider = BidirectionalProvider()

        engine.register_provider("bidirectional", provider)

        # Test outgoing edges (this should work through normal planning)
        start = Vertex({"x": 0, "y": 0})
        goal = Vertex({"x": 1, "y": 0})

        # This tests that out_edges is called during planning
        try:
            engine.plan(start=start, goal=goal)
            # Planning might fail (no path), but provider should have been called
            assert provider.out_edges_calls > 0
        except RuntimeError:
            # Expected if no path found, but provider should still have been called
            assert provider.out_edges_calls > 0

    def test_provider_method_validation(self):
        """Test that providers must have required methods."""
        engine = Engine()

        # Provider without out_edges method
        class BadProvider1:
            def in_edges(self, _vertex):
                return []

        with pytest.raises(TypeError, match="must implement out_edges method"):
            engine.register_provider("bad1", BadProvider1())

        # Provider without in_edges method
        class BadProvider2:
            def out_edges(self, _vertex):
                return []

        with pytest.raises(TypeError, match="must implement in_edges method"):
            engine.register_provider("bad2", BadProvider2())

        # Provider with non-callable methods
        class BadProvider3:
            out_edges = "not_callable"
            in_edges = "not_callable"

        with pytest.raises(TypeError, match="must implement out_edges method"):
            engine.register_provider("bad3", BadProvider3())

    def test_provider_notimplemented_handling(self):
        """Test that NotImplementedError is handled correctly."""
        engine = Engine(enable_edge_caching=False)
        provider = OutgoingOnlyProvider()

        engine.register_provider("outgoing_only", provider)

        # This should work with just outgoing edges
        start = Vertex({"x": 0, "y": 0})
        goal = Vertex({"x": 1, "y": 0})

        try:
            engine.plan(start=start, goal=goal)
            # Planning might fail, but should not crash due to NotImplementedError
            assert provider.call_count > 0
        except RuntimeError:
            # Expected if no path found
            assert provider.call_count > 0

    def test_multiple_bidirectional_providers(self):
        """Test multiple bidirectional providers."""
        engine = Engine(enable_edge_caching=True)

        provider1 = BidirectionalProvider()
        provider2 = BidirectionalProvider()

        engine.register_provider("provider1", provider1)
        engine.register_provider("provider2", provider2)

        # Verify both are registered
        assert len(engine.providers) == 2
        assert "provider1" in engine.providers
        assert "provider2" in engine.providers

    def test_bidirectional_provider_with_cache(self):
        """Test bidirectional providers with caching enabled."""
        engine = Engine(enable_edge_caching=True)
        provider = BidirectionalProvider()

        engine.register_provider("cached", provider)

        start = Vertex({"x": 0, "y": 0})
        goal = Vertex({"x": 1, "y": 0})

        # Run planning multiple times to test caching
        from contextlib import suppress

        for _ in range(3):
            with suppress(RuntimeError):
                engine.plan(start=start, goal=goal)

        # Cache should be working - verify that provider was called
        stats = engine.get_stats()
        # The provider should have been called for edge generation
        assert provider.call_count > 0 or stats.vertices_expanded > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
