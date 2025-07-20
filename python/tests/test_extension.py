from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence

    from graphserver import Vertex, VertexEdgePair


def test_module_import() -> None:
    """Test that the C extension module can be imported."""
    try:
        import _graphserver

        assert _graphserver is not None
        assert hasattr(_graphserver, "__version__")
        assert _graphserver.__version__ == "2.0.0"
    except ImportError:
        pytest.skip("C extension not built yet")


def test_engine_creation() -> None:
    """Test engine creation and destruction."""
    try:
        import _graphserver

        engine = _graphserver.create_engine()
        assert engine is not None
        # Destruction handled by PyCapsule destructor automatically
    except ImportError:
        pytest.skip("C extension not built yet")


def test_provider_registration() -> None:
    """Test provider registration functionality."""
    try:
        import _graphserver

        def dummy_provider(vertex: Vertex) -> Sequence[VertexEdgePair]:
            return []

        engine = _graphserver.create_engine()

        # Should not raise exception
        _graphserver.register_provider(engine, "test", dummy_provider)

        # Test error cases
        with pytest.raises(TypeError):
            _graphserver.register_provider(engine, "bad", "not_callable")
    except ImportError:
        pytest.skip("C extension not built yet")


def test_plan_with_provider() -> None:
    """Test plan function with actual provider."""
    try:
        import _graphserver

        engine = _graphserver.create_engine()

        # Register a simple provider that creates a path from x=0 to x=1
        def simple_provider(vertex: Vertex) -> Sequence[VertexEdgePair]:
            from graphserver import Edge, Vertex

            x = vertex.get("x", 0)
            if x == 0:
                target = Vertex({"x": 1})
                edge = Edge(cost=1.0)
                return [(target, edge)]
            return []

        _graphserver.register_provider(engine, "simple", simple_provider)

        # Now planning should work
        result = _graphserver.plan(engine, {"x": 0}, {"x": 1})
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        # Target vertex data should now be accessible (raw dict format from C extension)
        assert result[0]["target"]["x"] == 1
        cost = 1.0
        assert result[0]["cost"] == cost
    except ImportError:
        pytest.skip("C extension not built yet")


def test_python_api() -> None:
    """Test Python wrapper layer."""
    try:
        from graphserver import Edge, Engine, Vertex

        engine = Engine()
        assert engine is not None

        # Test provider registration with working provider
        def simple_provider(vertex: Vertex) -> Sequence[VertexEdgePair]:
            from graphserver import Vertex

            x = vertex.get("x", 0)
            if x == 0:
                target = Vertex({"x": 1})
                edge = Edge(cost=1.0)
                return [(target, edge)]
            return []

        engine.register_provider("simple", simple_provider)
        assert "simple" in engine.providers

        # Test actual planning
        result = engine.plan(start=Vertex({"x": 0}), goal=Vertex({"x": 1}))
        assert result is not None
        assert len(result) == 1
        # Target vertex data should now be accessible
        assert result[0].target["x"] == 1
        expected_cost = 1.0
        assert result.total_cost == expected_cost
    except ImportError:
        pytest.skip("C extension not built yet")


def test_type_checking() -> None:
    """Test that type hints work correctly."""
    from graphserver import Edge, EdgeProvider, Engine, Vertex

    def valid_provider(vertex: Vertex) -> Sequence[VertexEdgePair]:
        target = Vertex({"x": 1})
        edge = Edge(cost=1.0)
        return [(target, edge)]

    # Should pass type checking
    assert isinstance(valid_provider, EdgeProvider)

    engine = Engine()
    engine.register_provider("valid", valid_provider)


def test_error_handling() -> None:
    """Test error handling in various scenarios."""
    try:
        from graphserver import Engine, Vertex

        engine = Engine()

        # Test invalid provider
        with pytest.raises(TypeError, match="Provider must be callable"):
            engine.register_provider("bad", "not_callable")  # type: ignore[arg-type]

        # Test invalid start/goal
        def dummy_provider(vertex: Vertex) -> Sequence[VertexEdgePair]:
            return []

        engine.register_provider("test", dummy_provider)

        with pytest.raises(TypeError, match="Start must be a Vertex"):
            engine.plan(start="not_vertex", goal=Vertex({"x": 1}))  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="Goal must be a Vertex"):
            engine.plan(start=Vertex({"x": 0}), goal="not_vertex")  # type: ignore[arg-type]
    except ImportError:
        pytest.skip("C extension not built yet")


def test_data_conversion() -> None:
    """Test data conversion between Python and C."""
    try:
        from graphserver import Edge, Engine, Vertex

        engine = Engine()

        # Test complex data types
        def complex_provider(vertex: Vertex) -> Sequence[VertexEdgePair]:
            from graphserver import Vertex

            if vertex.get("start", False):
                target = Vertex(
                    {
                        "x": 10,
                        "y": 20.5,
                        "name": "destination",
                        "active": True,
                        "path": [1, 2, 3],
                    }
                )
                edge = Edge(cost=15.5, metadata={"direction": "north", "distance": 100})
                return [(target, edge)]
            return []

        engine.register_provider("complex", complex_provider)

        # Test planning with complex data
        result = engine.plan(
            start=Vertex({"start": True, "location": "origin"}),
            goal=Vertex(
                {
                    "x": 10,
                    "y": 20.5,
                    "name": "destination",
                    "active": True,
                    "path": [1, 2, 3],
                }
            ),
        )

        assert len(result) == 1
        path_edge = result[0]
        # Target vertex data should now be accessible
        assert path_edge.target["x"] == 10
        assert path_edge.target["y"] == 20.5
        assert path_edge.target["name"] == "destination"
        assert (
            path_edge.target["active"] == 1
        )  # Booleans converted to int in C conversion
        assert (
            path_edge.target["path"] == "[1, 2, 3]"
        )  # Arrays converted to string in C conversion
        expected_cost = 15.5
        assert path_edge.edge.cost == expected_cost
        # Metadata handling working in edge processing during provider execution
        # Note: Metadata is not preserved in path results due to C library limitations
        # This validates that the provider and edge conversion are working correctly
    except ImportError:
        pytest.skip("C extension not built yet")
