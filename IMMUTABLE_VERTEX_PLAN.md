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

### Phase 2: Update C Tests ✅ COMPLETED

1. ✅ **Rewrite creation tests** to use new API - Updated all vertex creation calls
2. ✅ **Remove mutation tests** - Removed all gs_vertex_set_kv/remove_key tests
3. ✅ **Add hash-based equality tests** - Updated vertex_equality_and_hashing test
4. ✅ **Add tests for optional hash parameter** - Added vertex_custom_hash test
5. ✅ **Verify immutability** - Added vertex_immutability test

**Additional New Tests Added:**
- `test_vertex_custom_hash` - Tests custom hash parameter functionality
- `test_vertex_hash_consistency` - Verifies same data produces same hash
- `test_vertex_empty_vertex_hash` - Tests hash behavior for empty vertices
- `test_vertex_immutability` - Verifies no mutation capabilities exist

**Status**: All C tests updated and passing (14/14 tests passed)  
**Memory Safety**: ✅ Valgrind clean - no memory leaks detected

### Phase 3: Update Python Bindings ✅ COMPLETED

1. ✅ **Update `_graphserver.c`**:
   - Modified `python_dict_to_vertex()` to create immutable vertex using new API
   - Updated `python_vertex_object_to_vertex()` for new API with hash support
   - Added optional hash parameter handling in conversions via "_hash" key
   - Updated `vertex_to_python_dict()` to include hash value in output

2. ✅ **Update Python `Vertex` class** in `core.py`:
   - Made it immutable (removed mutation capability from `__setitem__`)
   - Added optional hash parameter to `__init__`
   - Updated `__hash__()` to use stored hash if available
   - Updated `to_dict()` to include hash value when present
   - Maintains data-based equality in `__eq__()`

**Key Changes Made:**
- `python_dict_to_vertex()`: Now collects all key-value pairs and creates vertex with `gs_vertex_create(pairs, num_pairs, hash_ptr)`
- Hash parameter handling: "_hash" key in dictionaries is extracted and used as optional hash parameter
- `Vertex` class: Now accepts `hash_value` parameter and stores it as `_custom_hash`
- Full memory safety: Proper cleanup of GraphserverKeyPair arrays and values
- Backward compatibility: Existing code continues to work, hash support is optional

**Status**: All Python bindings updated and working with immutable vertex API  
**Testing**: ✅ All tests passing (C tests: 14/14, Python extension tests: 8/8, custom immutable tests: all passing)

### Phase 4: Update Python Tests ✅ COMPLETED

1. ✅ **Created comprehensive vertex test suite** (`tests/test_vertex.py`):
   - 31 test cases covering all immutable vertex functionality
   - Tests for creation, immutability, hash functionality, equality, and edge cases
   - Full coverage of dictionary-like interface and string representation

2. ✅ **Fixed minor code issue** in `core.py`:
   - Simplified `Vertex(target_data) if target_data else Vertex()` to `Vertex(target_data or {})`

3. ✅ **Added integration tests** to `test_extension.py`:
   - `test_vertex_immutability_integration()` - Verifies vertices from planning are immutable
   - `test_hash_preservation_through_planning()` - Tests hash preservation through C extension

4. ✅ **Verified existing tests** remain compatible:
   - All existing 72 test cases continue to pass
   - No changes needed to provider tests (already use immutable patterns)
   - OSM provider tests, cache tests, and others work without modification

**Key Achievements:**
- **Comprehensive test coverage**: 31 new tests specifically for immutable vertex functionality
- **Integration testing**: Ensures C extension properly handles immutable vertices and hash values  
- **Backward compatibility**: All existing tests (103 total) continue to pass
- **Code quality**: All tests pass linting with ruff and follow project style guidelines

**Status**: All Python tests updated and passing (103/103 tests passed)  
**Testing**: ✅ Full test suite validates immutable vertex implementation at all levels

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
- ✅ Phase 2 (C Tests): 1-2 hours **COMPLETED** 
- ✅ Phase 3 (Python Bindings): 2-3 hours **COMPLETED**
- ✅ Phase 4 (Python Tests): 1-2 hours **COMPLETED**
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

### ✅ Phase 2 Complete - C Tests Updated
**Completed**: All C tests updated for immutable vertex API
- Updated existing tests to use new gs_vertex_create() API
- Removed all mutation-based tests (set_kv, remove_key)
- Added comprehensive tests for immutable features
- All 14 tests passing successfully

**Tests Updated:**
- `test_vertex_lifecycle` - Uses new empty vertex creation
- `test_vertex_immutable_access` - Replaces old key-value ops test
- `test_vertex_key_ordering` - Tests automatic key sorting
- `test_vertex_equality_and_hashing` - Tests hash-based equality
- `test_vertex_cloning` - Tests hash preservation in clones
- `test_vertex_string_representation` - Updated for new API
- `test_vertex_error_conditions` - Removed mutation error tests

**New Tests Added:**
- `test_vertex_custom_hash` - Custom hash parameter functionality
- `test_vertex_hash_consistency` - Hash consistency verification
- `test_vertex_empty_vertex_hash` - Empty vertex hash behavior
- `test_vertex_immutability` - Immutability verification

### 🔄 Next Phase  
Phase 5 ready to begin: Update all usage sites for immutable vertex API