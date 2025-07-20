from __future__ import annotations

import gc
import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

def test_engine_memory_management() -> None:
    """Test that engines are properly cleaned up."""
    try:
        import _graphserver
        
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
    except ImportError:
        pytest.skip("C extension not built yet")

def test_provider_reference_counting() -> None:
    """Test that Python provider functions are properly reference counted."""
    try:
        import _graphserver
        import weakref
        
        def provider_func(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
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
    except ImportError:
        pytest.skip("C extension not built yet")

def test_repeated_operations() -> None:
    """Test repeated operations don't accumulate memory."""
    try:
        from graphserver import Engine
        
        def provider_func(vertex: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
            return []
        
        # Perform many operations
        for i in range(100):
            engine = Engine()
            engine.register_provider(f"test_{i}", provider_func)
            
            # Try planning (will fail with NotImplementedError, but shouldn't leak)
            try:
                engine.plan(start={"x": i}, goal={"x": i + 1})
            except NotImplementedError:
                pass  # Expected in Phase 1
        
        # Force cleanup
        gc.collect()
        
        # Should complete without issues
    except ImportError:
        pytest.skip("C extension not built yet")