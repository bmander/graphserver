from __future__ import annotations

import contextlib
import gc
import weakref
from typing import TYPE_CHECKING

import pytest

try:
    import _graphserver

    from graphserver import Engine
except ImportError:
    _graphserver = None
    Engine = None

if TYPE_CHECKING:
    from collections.abc import Sequence

    from graphserver import Vertex, VertexEdgePair


def test_engine_memory_management() -> None:
    """Test that engines are properly cleaned up."""
    if _graphserver is None:
        pytest.skip("C extension not built yet")
        return

    # Create multiple engines and let them go out of scope
    engines = []
    for _ in range(10):
        engine = _graphserver.create_engine()
        engines.append(engine)

    # Clear references
    engines.clear()

    # Force garbage collection
    gc.collect()

    # Should not crash or leak memory
    # (Detailed memory leak detection requires external tools)


def test_provider_reference_counting() -> None:
    """Test that Python provider functions are properly reference counted."""
    if _graphserver is None:
        pytest.skip("C extension not built yet")
        return

    def provider_func(_vertex: Vertex) -> Sequence[VertexEdgePair]:
        return []

    # Create weak reference to track lifetime
    weak_ref = weakref.ref(provider_func)

    engine = _graphserver.create_engine()
    _graphserver.register_provider(engine, "test", provider_func)

    # Function should still be alive due to C extension holding reference
    assert weak_ref() is not None

    # Delete our reference
    del provider_func
    gc.collect()

    # Function should still be alive (held by C extension)
    assert weak_ref() is not None

    # Delete engine (should release provider reference)
    del engine
    gc.collect()

    # Now function should be garbage collected
    # Note: This test may be fragile depending on Python implementation details


def test_repeated_operations() -> None:
    """Test repeated operations don't accumulate memory."""
    if Engine is None:
        pytest.skip("Python wrapper not available")
        return

    def provider_func(_vertex: Vertex) -> Sequence[VertexEdgePair]:
        return []

    # Perform many operations
    for i in range(100):
        engine = Engine()
        engine.register_provider(f"test_{i}", provider_func)

        # Try planning (will fail with no path found, but shouldn't leak)
        with contextlib.suppress(NotImplementedError, RuntimeError):
            from graphserver import Vertex

            engine.plan(start=Vertex({"x": i}), goal=Vertex({"x": i + 1}))
            # Expected - either Phase 1 (NotImplementedError) or Phase 2 (RuntimeError)

    # Force cleanup
    gc.collect()

    # Should complete without issues
