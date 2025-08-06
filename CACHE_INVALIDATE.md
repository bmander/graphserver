# Unified Cache Invalidation Architecture for GraphServer

## Problem Analysis

### The Read/Write Path Disconnect
As Gemini clearly identified, the core issue is a fundamental disconnect between:
- **Read Path**: `Engine → Cache → Provider` (on cache miss)
- **Write Path**: `External Event → Provider's Internal State` (invisible to engine)

The cache serves as a performance-enhancing replica that becomes stale when the source of truth (provider) changes without notification.

## Architectural Solution: Hybrid Invalidation System

### Design Pattern: Observer/Callback with Batch Management

We'll implement an **Observer pattern** where providers can notify the engine of changes, combined with a **batch invalidation manager** for performance optimization.

## Implementation Design

### 1. C Core API Extensions

```c
// In gs_cache.h - Basic invalidation operations
GraphserverResult edge_cache_invalidate(
    EdgeCache* cache,
    const GraphserverVertex* vertex
);

GraphserverResult edge_cache_invalidate_batch(
    EdgeCache* cache,
    const GraphserverVertex** vertices,
    size_t count
);

void edge_cache_invalidate_all(EdgeCache* cache);

// In gs_engine.h - Engine-level API
GraphserverResult gs_engine_invalidate_vertex_cache(
    GraphserverEngine* engine,
    const GraphserverVertex* vertex
);

GraphserverResult gs_engine_invalidate_vertices_cache(
    GraphserverEngine* engine,
    const GraphserverVertex** vertices,
    size_t count
);

// Callback type for C/Python interop
typedef void (*gs_invalidation_callback_fn)(
    void* callback_data,
    const char* vertex_id
);

// Register Python callback
GraphserverResult gs_engine_set_invalidation_callback(
    GraphserverEngine* engine,
    gs_invalidation_callback_fn callback,
    void* callback_data
);
```

### 2. Python API Design

#### Basic Provider Interface with Invalidation Support

```python
from typing import Protocol, Callable, Optional
from abc import ABC, abstractmethod

class InvalidationHandler(Protocol):
    """Protocol for cache invalidation handlers."""
    def invalidate_vertex(self, vertex: Vertex) -> None: ...
    def invalidate_vertices(self, vertices: list[Vertex]) -> None: ...

class CacheAwareEdgeProvider(EdgeProvider):
    """Base class for providers that need cache invalidation."""
    
    def __init__(self):
        self._invalidation_handler: Optional[InvalidationHandler] = None
    
    def set_invalidation_handler(self, handler: InvalidationHandler) -> None:
        """Called by engine during provider registration."""
        self._invalidation_handler = handler
    
    def invalidate_vertex(self, vertex: Vertex) -> None:
        """Notify engine that vertex cache is stale."""
        if self._invalidation_handler:
            self._invalidation_handler.invalidate_vertex(vertex)
    
    @abstractmethod
    def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]: ...
    
    @abstractmethod
    def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]: ...
```

#### Advanced Batch Management

```python
class CacheManager:
    """Context manager for efficient batch cache invalidation."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self._invalidated_vertices: set[Vertex] = set()
        self._immediate_mode = False
    
    def invalidate(self, vertex: Vertex) -> None:
        """Mark vertex for invalidation."""
        if self._immediate_mode:
            self.engine.invalidate_vertex_cache(vertex)
        else:
            self._invalidated_vertices.add(vertex)
    
    def invalidate_immediate(self, vertex: Vertex) -> None:
        """Immediately invalidate without batching."""
        self.engine.invalidate_vertex_cache(vertex)
    
    def set_immediate_mode(self, immediate: bool) -> None:
        """Toggle between batch and immediate invalidation."""
        self._immediate_mode = immediate
    
    def __enter__(self) -> 'CacheManager':
        return self
    
    def __exit__(self, *args) -> None:
        # Batch invalidate all marked vertices
        if self._invalidated_vertices:
            self.engine.invalidate_vertices_cache(list(self._invalidated_vertices))
            self._invalidated_vertices.clear()
```

#### Engine Extensions

```python
class Engine:
    def __init__(self, *, enable_edge_caching: bool = False, **kwargs):
        # ... existing init ...
        self._invalidation_handler = self._create_invalidation_handler()
    
    def register_provider(self, name: str, provider: EdgeProvider) -> None:
        """Register provider with automatic invalidation support."""
        # Existing validation...
        
        # If provider supports invalidation, inject handler
        if isinstance(provider, CacheAwareEdgeProvider):
            provider.set_invalidation_handler(self._invalidation_handler)
        
        # Register with C extension
        _graphserver.register_provider(self._engine, name, provider)
        self._providers[name] = provider
    
    def _create_invalidation_handler(self) -> InvalidationHandler:
        """Create handler that bridges Python to C invalidation."""
        class EngineInvalidationHandler:
            def __init__(self, engine):
                self.engine = engine
            
            def invalidate_vertex(self, vertex: Vertex) -> None:
                _graphserver.invalidate_vertex_cache(self.engine._engine, vertex)
            
            def invalidate_vertices(self, vertices: list[Vertex]) -> None:
                _graphserver.invalidate_vertices_cache(
                    self.engine._engine, vertices
                )
        
        return EngineInvalidationHandler(self)
    
    def create_cache_manager(self) -> CacheManager:
        """Create a cache manager for this engine."""
        return CacheManager(self)
    
    # Direct invalidation methods
    def invalidate_vertex_cache(self, vertex: Vertex) -> None:
        """Directly invalidate cache for a vertex."""
        if not self.cache_enabled:
            return
        _graphserver.invalidate_vertex_cache(self._engine, vertex)
    
    def invalidate_vertices_cache(self, vertices: Sequence[Vertex]) -> None:
        """Batch invalidate cache for multiple vertices."""
        if not self.cache_enabled:
            return
        _graphserver.invalidate_vertices_cache(self._engine, list(vertices))
    
    def clear_cache(self) -> None:
        """Clear entire edge cache."""
        if not self.cache_enabled:
            return
        _graphserver.clear_cache(self._engine)
```

### 3. C Implementation Details

```c
// In cache.c - Remove entry implementation
static void cache_entry_remove(EdgeCache* cache, const GraphserverVertex* vertex) {
    if (!cache || !vertex) return;
    
    uint64_t hash = gs_vertex_hash(vertex);
    size_t bucket_index = hash & cache->mask;
    
    CacheEntry* prev = NULL;
    CacheEntry* current = cache->buckets[bucket_index];
    
    while (current) {
        if (current->hash == hash && gs_vertex_equals(current->vertex, vertex)) {
            // Found - remove from chain
            if (prev) {
                prev->next = current->next;
            } else {
                cache->buckets[bucket_index] = current->next;
            }
            
            cache_entry_destroy(current);
            cache->size--;
            return;
        }
        prev = current;
        current = current->next;
    }
}

// Public invalidation functions
GraphserverResult edge_cache_invalidate(
    EdgeCache* cache,
    const GraphserverVertex* vertex) {
    
    if (!cache || !vertex) return GS_ERROR_NULL_POINTER;
    
    // Thread safety: acquire lock here if multi-threaded
    cache_entry_remove(cache, vertex);
    
    return GS_SUCCESS;
}

GraphserverResult edge_cache_invalidate_batch(
    EdgeCache* cache,
    const GraphserverVertex** vertices,
    size_t count) {
    
    if (!cache || !vertices) return GS_ERROR_NULL_POINTER;
    
    // Single lock acquisition for entire batch
    for (size_t i = 0; i < count; i++) {
        if (vertices[i]) {
            cache_entry_remove(cache, vertices[i]);
        }
    }
    
    return GS_SUCCESS;
}
```

### 4. Usage Examples

#### Simple Provider with Direct Invalidation

```python
class DynamicGraphProvider(CacheAwareEdgeProvider):
    def __init__(self):
        super().__init__()
        self.graph = {}  # vertex_id -> [(target, edge)]
    
    def add_edge(self, from_id: str, to_id: str, cost: float):
        """Add edge and invalidate cache."""
        if from_id not in self.graph:
            self.graph[from_id] = []
        
        target = Vertex({"id": to_id})
        edge = Edge(cost=cost)
        self.graph[from_id].append((target, edge))
        
        # Immediate invalidation
        source = Vertex({"id": from_id})
        self.invalidate_vertex(source)
    
    def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        return self.graph.get(vertex["id"], [])
    
    def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        return []  # Not implemented for this example
```

#### Batch Updates with Cache Manager

```python
class BulkUpdateProvider(CacheAwareEdgeProvider):
    def __init__(self):
        super().__init__()
        self.graph = {}
        self.engine = None
    
    def bulk_update(self, updates: list[tuple[str, str, float]]):
        """Perform multiple updates with batch invalidation."""
        if not self.engine:
            # Fallback to immediate invalidation
            for from_id, to_id, cost in updates:
                self._add_edge_internal(from_id, to_id, cost)
                self.invalidate_vertex(Vertex({"id": from_id}))
        else:
            # Use cache manager for batch invalidation
            with self.engine.create_cache_manager() as cm:
                for from_id, to_id, cost in updates:
                    self._add_edge_internal(from_id, to_id, cost)
                    cm.invalidate(Vertex({"id": from_id}))
                # All invalidations happen here atomically
    
    def _add_edge_internal(self, from_id: str, to_id: str, cost: float):
        if from_id not in self.graph:
            self.graph[from_id] = []
        self.graph[from_id].append((Vertex({"id": to_id}), Edge(cost=cost)))
```

## Key Design Decisions

### 1. **Dual API Approach**
- Simple callback injection for basic use cases (Gemini's approach)
- Advanced CacheManager for complex scenarios (my approach)
- Providers can choose the appropriate level of sophistication

### 2. **Batch Optimization**
- Single C function call for multiple invalidations
- Reduces FFI overhead and improves performance
- Optional immediate mode for time-critical invalidations

### 3. **Thread Safety**
- Cache operations designed to be mutex-protected
- Batch operations hold single lock for consistency
- Invalidation callbacks are synchronous to avoid race conditions

### 4. **Backward Compatibility**
- Existing providers continue to work without modification
- Cache-aware providers opt-in to invalidation support
- Engine automatically detects and configures cache-aware providers

## Tradeoff Analysis

| Aspect | Our Hybrid Solution |
|--------|-------------------|
| **Correctness** | High - Immediate invalidation ensures no stale data after provider updates |
| **Complexity** | Medium - Simple API for basic use, advanced features available when needed |
| **Performance** | High - Batch invalidation minimizes overhead, direct C calls for efficiency |
| **API Ergonomics** | High - Intuitive callback pattern with optional advanced features |
| **Flexibility** | Very High - Supports immediate, batch, and context-managed invalidation |
| **Migration Path** | Excellent - Existing code works unchanged, gradual adoption possible |

## Implementation Priority

1. **Phase 1**: Basic invalidation API (C functions + simple Python wrapper) ✅ **COMPLETED**
2. **Phase 2**: Provider callback injection and CacheAwareEdgeProvider ✅ **COMPLETED** 
3. **Phase 3**: CacheManager and batch operations 🔄 **TODO**
4. **Phase 4**: Thread safety and performance optimization 🔄 **TODO**

This unified approach combines Gemini's clear architectural vision with practical implementation details, providing both simplicity for common cases and power for advanced scenarios.

## Implementation Status

### ✅ Phase 1 Complete - Basic Invalidation API

**Implemented Components:**
- ✅ C core invalidation functions in `gs_cache.h` and `cache.c`
  - `edge_cache_invalidate()` - Single vertex invalidation
  - `edge_cache_invalidate_batch()` - Batch vertex invalidation  
  - `edge_cache_invalidate_all()` - Full cache clear
- ✅ Engine-level API in `gs_engine.h` and `engine.c`
  - `gs_engine_invalidate_vertex_cache()`
  - `gs_engine_invalidate_vertices_cache()`
  - `gs_engine_clear_cache()`
- ✅ Python bindings in `extension/cache.c`
  - `py_invalidate_vertex_cache()`
  - `py_invalidate_vertices_cache()`
  - `py_clear_cache()`
- ✅ Python API methods in `Engine` class
  - `invalidate_vertex_cache(vertex)`
  - `invalidate_vertices_cache(vertices)`
  - `clear_cache()`
- ✅ Comprehensive test coverage (22/22 C tests + 6/6 Python tests passing)

**Key Achievement:** Direct invalidation API available for immediate use.

### ✅ Phase 2 Complete - Provider Callback Injection

**Implemented Components:**
- ✅ `InvalidationHandler` Protocol - Type-safe interface for cache invalidation handlers
- ✅ `CacheAwareEdgeProvider` Abstract Base Class - Providers can inherit to get invalidation capabilities
- ✅ `_EngineInvalidationHandler` Bridge Class - Seamless Python-to-C invalidation calls
- ✅ Automatic Handler Injection - `Engine.register_provider()` detects cache-aware providers
- ✅ Full backward compatibility - Regular `EdgeProvider` implementations unchanged
- ✅ Comprehensive test coverage (17/17 tests passing)

**Key Achievement:** Providers can now proactively invalidate cache when their state changes.

**Example Usage:**
```python
from graphserver import CacheAwareEdgeProvider, Vertex, Edge

class DynamicGraphProvider(CacheAwareEdgeProvider):
    def __init__(self):
        super().__init__()
        self.graph = {}
    
    def add_edge(self, from_id: str, to_id: str, cost: float):
        # Update internal graph
        self.graph[from_id] = [(Vertex({"id": to_id}), Edge(cost=cost))]
        
        # Trigger automatic cache invalidation
        self.invalidate_vertex(Vertex({"id": from_id}))
    
    def out_edges(self, vertex): 
        return self.graph.get(vertex.get("id"), [])
```

### 🔄 Phase 3 TODO - CacheManager and Batch Operations

**Planned Components:**
- `CacheManager` context manager for efficient batch invalidation
- Immediate vs. batched invalidation modes
- Advanced performance optimizations for bulk operations

### 🔄 Phase 4 TODO - Thread Safety and Performance

**Planned Components:**
- Thread-safe cache invalidation operations
- Performance optimizations for high-frequency invalidation
- Advanced memory management for large-scale operations