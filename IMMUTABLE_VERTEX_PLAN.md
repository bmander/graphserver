# Immutable Vertex Implementation Plan

## Overview
Transform the current mutable vertex implementation into an immutable system where:
- Vertices are created with all key-value pairs at once
- No modification is allowed after creation
- Equality is determined by hash comparison
- An optional hash value can be provided at creation

## API Changes

### Core C API (gs_vertex.h)

#### New Creation Function
```c
// Create immutable vertex with key-value pairs and optional hash
GraphserverVertex* gs_vertex_create(
    const GraphserverKeyPair* pairs, 
    size_t num_pairs,
    uint64_t* optional_hash  // NULL to auto-calculate
);
```

#### Functions to Remove
- `gs_vertex_set_kv()` - No longer needed for immutable vertices
- `gs_vertex_remove_key()` - No longer needed for immutable vertices

#### Functions to Modify
- `gs_vertex_equals()` - Will compare by hash only
- `gs_vertex_hash()` - Will return stored hash or calculate if not provided

#### Functions to Keep As-Is
- `gs_vertex_destroy()`
- `gs_vertex_clone()` 
- `gs_vertex_get_value()`
- `gs_vertex_has_key()`
- `gs_vertex_get_key_count()`
- `gs_vertex_get_key_at_index()`
- `gs_vertex_get_keys()`
- `gs_vertex_to_string()`

### Internal Structure Changes (vertex.c)
```c
struct GraphserverVertex {
    GraphserverKeyPair* pairs;
    size_t num_pairs;
    uint64_t hash;  // Stored hash value
    bool hash_provided;  // Whether hash was provided at creation
};
```

## Implementation Plan

### Phase 1: Update Core C Implementation ✅ COMPLETED

1. ✅ **Modify vertex structure** to include hash field
   - Added `uint64_t hash` and `bool hash_provided` fields to GraphserverVertex struct
2. ✅ **Implement new creation function** `gs_vertex_create(pairs, num_pairs, optional_hash)`
   - Sort pairs by key for consistent ordering using qsort()
   - Calculate hash if not provided using FNV-1a hash algorithm
   - Store all data immutably with proper memory management
3. ✅ **Update `gs_vertex_equals()`** to compare hashes first with fallback for collision detection
4. ✅ **Update `gs_vertex_hash()`** to return stored hash value
5. ✅ **Remove mutation functions** (`gs_vertex_set_kv`, `gs_vertex_remove_key`)
6. ✅ **Update `gs_vertex_clone()`** to preserve hash by passing it to new creation function

**Status**: Core C library compiles successfully. All Phase 1 objectives completed and tested.

### Phase 2: Update C Tests

1. **Rewrite creation tests** to use new API
2. **Remove mutation tests**
3. **Add hash-based equality tests**
4. **Add tests for optional hash parameter**
5. **Verify immutability** (no way to modify after creation)

### Phase 3: Update Python Bindings

1. **Update `_graphserver.c`**:
   - Modify `python_dict_to_vertex()` to create immutable vertex
   - Update `python_vertex_object_to_vertex()` for new API
   - Handle optional hash parameter in conversions

2. **Update Python `Vertex` class** in `core.py`:
   - Make it immutable (remove `__setitem__`)
   - Accept optional hash in `__init__`
   - Update `__hash__()` to use stored hash if available
   - Ensure `__eq__()` uses hash comparison

### Phase 4: Update Python Tests

1. **Update all vertex creation** in tests
2. **Remove mutation tests**
3. **Add immutability tests**
4. **Test hash parameter functionality**
5. **Update provider tests** that create vertices

### Phase 5: Update All Usage Sites

1. **Update example providers** to create immutable vertices
2. **Update OSM providers** to create immutable vertices
3. **Update any code that modifies vertices** to create new ones instead

## Migration Strategy

### Breaking Changes
- `gs_vertex_set_kv()` removed
- `gs_vertex_remove_key()` removed
- `gs_vertex_create()` signature changed
- Python `Vertex` no longer supports item assignment

### Code Pattern Updates

#### Before (Mutable):
```c
GraphserverVertex* v = gs_vertex_create();
gs_vertex_set_kv(v, "x", gs_value_create_int(10));
gs_vertex_set_kv(v, "y", gs_value_create_int(20));
```

#### After (Immutable):
```c
GraphserverKeyPair pairs[] = {
    {"x", gs_value_create_int(10)},
    {"y", gs_value_create_int(20)}
};
GraphserverVertex* v = gs_vertex_create(pairs, 2, NULL);
```

#### Python Before:
```python
v = Vertex()
v["x"] = 10
v["y"] = 20
```

#### Python After:
```python
v = Vertex({"x": 10, "y": 20})
# or with hash:
v = Vertex({"x": 10, "y": 20}, hash_value=12345)
```

## Benefits

1. **Thread Safety**: Immutable vertices are inherently thread-safe
2. **Cache Efficiency**: Hash-based equality enables better caching
3. **Predictability**: No surprising mutations
4. **Performance**: Pre-computed hashes speed up comparisons
5. **Simplicity**: Clearer data flow, easier to reason about

## Risks and Mitigations

1. **Risk**: Breaking existing code
   - **Mitigation**: Clear migration guide, update all tests and examples

2. **Risk**: Performance impact of creating new vertices
   - **Mitigation**: Pre-computed hashes reduce comparison costs

3. **Risk**: Memory usage from more vertex objects
   - **Mitigation**: Vertices are typically short-lived in planning algorithms

## Testing Strategy

1. **Unit Tests**: Comprehensive tests for new immutable API
2. **Integration Tests**: Ensure planning algorithms work with immutable vertices
3. **Performance Tests**: Verify no regression in routing performance
4. **Memory Tests**: Check for leaks with new creation patterns

## Implementation Order

1. Core C implementation (vertex.h, vertex.c)
2. C tests (test_vertex.c)
3. Python bindings (_graphserver.c)
4. Python implementation (core.py)
5. Python tests
6. Update providers and examples
7. Performance validation

## Estimated Timeline

- ✅ Phase 1 (Core C): 2-3 hours **COMPLETED**
- Phase 2 (C Tests): 1-2 hours  
- Phase 3 (Python Bindings): 2-3 hours
- Phase 4 (Python Tests): 1-2 hours
- Phase 5 (Usage Updates): 3-4 hours
- Testing & Validation: 2-3 hours

Total: 11-17 hours of implementation work

## Implementation Status

### ✅ Phase 1 Complete - Core C Implementation
**Completed**: All core C changes implemented and verified working
- New immutable vertex creation API
- Hash-based equality with collision detection
- Automatic key sorting for consistent behavior
- Memory-safe implementation with proper cleanup
- Core library compiles successfully

**Testing**: Custom test program verified all functionality:
- Empty vertex creation ✓
- Multi-key vertex creation ✓  
- Automatic key sorting ✓
- Hash-based equality ✓
- Vertex cloning ✓
- Custom hash values ✓

### 🔄 Next Phase
Phase 2 ready to begin: Update C tests to use new immutable API (test_vertex.c currently fails compilation as expected)