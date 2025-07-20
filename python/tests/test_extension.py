from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence, Mapping
    from typing import Any


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

        def dummy_provider(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
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
        def simple_provider(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
            x = vertex.get("x", 0)
            if x == 0:
                return [{"target": {"x": 1}, "cost": 1.0}]
            return []

        _graphserver.register_provider(engine, "simple", simple_provider)

        # Now planning should work
        result = _graphserver.plan(engine, {"x": 0}, {"x": 1})
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["target"]["x"] == 1
        assert result[0]["cost"] == 1.0
    except ImportError:
        pytest.skip("C extension not built yet")


def test_python_api() -> None:
    """Test Python wrapper layer."""
    try:
        from graphserver import Engine

        engine = Engine()
        assert engine is not None

        # Test provider registration with working provider
        def simple_provider(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
            x = vertex.get("x", 0)
            if x == 0:
                return [{"target": {"x": 1}, "cost": 1.0}]
            return []

        engine.register_provider("simple", simple_provider)
        assert "simple" in engine.providers

        # Test actual planning
        result = engine.plan(start={"x": 0}, goal={"x": 1})
        assert result is not None
        assert len(result) == 1
        assert result[0]["target"]["x"] == 1
        assert result.total_cost == 1.0
    except ImportError:
        pytest.skip("C extension not built yet")


def test_type_checking() -> None:
    """Test that type hints work correctly."""
    from graphserver import Engine, EdgeProvider

    def valid_provider(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
        return [{"target": {"x": 1}, "cost": 1.0}]

    # Should pass type checking
    assert isinstance(valid_provider, EdgeProvider)

    engine = Engine()
    engine.register_provider("valid", valid_provider)


def test_error_handling() -> None:
    """Test error handling in various scenarios."""
    try:
        from graphserver import Engine

        engine = Engine()

        # Test invalid provider
        with pytest.raises(ValueError, match="Provider must be callable"):
            engine.register_provider("bad", "not_callable")  # type: ignore[arg-type]

        # Test invalid start/goal
        def dummy_provider(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
            return []

        engine.register_provider("test", dummy_provider)

        with pytest.raises(ValueError, match="Start must be a mapping"):
            engine.plan(start="not_dict", goal={"x": 1})  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="Goal must be a mapping"):
            engine.plan(start={"x": 0}, goal="not_dict")  # type: ignore[arg-type]
    except ImportError:
        pytest.skip("C extension not built yet")


def test_data_conversion() -> None:
    """Test data conversion between Python and C."""
    try:
        from graphserver import Engine

        engine = Engine()

        # Test complex data types
        def complex_provider(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
            if vertex.get("start", False):
                return [{
                    "target": {
                        "x": 10,
                        "y": 20.5,
                        "name": "destination",
                        "active": True,
                        "path": [1, 2, 3]
                    },
                    "cost": 15.5,
                    "metadata": {
                        "direction": "north",
                        "distance": 100
                    }
                }]
            return []

        engine.register_provider("complex", complex_provider)

        # Test planning with complex data
        result = engine.plan(
            start={"start": True, "location": "origin"},
            goal={"x": 10, "y": 20.5, "name": "destination", "active": True, "path": [1, 2, 3]}
        )
        
        assert len(result) == 1
        edge = result[0]
        assert edge["target"]["x"] == 10
        assert edge["target"]["y"] == 20.5
        assert edge["target"]["name"] == "destination"
        assert edge["target"]["active"] == True
        assert edge["target"]["path"] == [1, 2, 3]
        assert edge["cost"] == 15.5
        assert "metadata" in edge
    except ImportError:
        pytest.skip("C extension not built yet")
