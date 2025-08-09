# Ushort Key Dictionary System Design

## Executive Summary

This document describes the design and implementation of an optimized key-value storage system for the Graphserver engine that replaces string keys with unsigned 16-bit integers (ushorts). This optimization significantly reduces memory usage and improves cache locality.

## Problem Statement

### Current Implementation Issues

1. **Memory Overhead**: Every vertex and edge stores multiple string keys (e.g., "mode", "lat", "lon", "time"). These strings are duplicated across millions of vertices in large graphs.

2. **String Comparison Cost**: Key lookups require `strcmp()` operations, which are slower than integer comparisons.

3. **Cache Inefficiency**: String pointers cause additional memory indirection and poor cache locality.

### Analysis of Key Usage

Based on codebase analysis:
- **Common keys**: ~30-40 frequently reused keys (mode, lat, lon, time, etc.)
- **Domain-specific keys**: Each provider adds 10-20 unique keys
- **Total unique keys**: Typically < 1000 in any single application
- **Available space**: 65,536 possible values with ushort (more than sufficient)

## Proposed Solution

### Core Architecture

```c
// String dictionary structure
typedef struct {
    char** strings;           // Array of interned strings
    uint16_t* hashes;        // Optional: hash values for fast lookup
    size_t count;            // Current number of strings
    size_t capacity;         // Allocated capacity
    pthread_rwlock_t lock;   // Thread-safe access
} GraphserverStringDict;

// Key-value pair using ushort keys
typedef struct {
    uint16_t key;            // Ushort key ID
    GraphserverValue value;
} GraphserverKeyPair;
```

### Key Components

#### 1. Global String Dictionary (gs_string_dict.h/c)

**Purpose**: Central registry mapping ushort IDs to string values. This is a pure, domain-agnostic dictionary service.

```c
// Initialization and cleanup
void gs_string_dict_init(void);
void gs_string_dict_cleanup(void);

// String registration (returns existing ID if already registered)
uint16_t gs_string_dict_register(const char* str);

// String lookup
const char* gs_string_dict_get(uint16_t id);

// Bulk operations for efficiency
void gs_string_dict_register_batch(const char** strings, uint16_t* ids, size_t count);

// Check if string is already registered
bool gs_string_dict_contains(const char* str);

// Get current dictionary size
size_t gs_string_dict_size(void);
```

#### 2. Common Keys Module (gs_common_keys.h/c)

**Purpose**: Define and register commonly used keys across the engine. This is separate from the dictionary itself.

```c
// gs_common_keys.h
extern uint16_t GS_KEY_MODE;
extern uint16_t GS_KEY_LAT;
extern uint16_t GS_KEY_LON;
extern uint16_t GS_KEY_TIME;
extern uint16_t GS_KEY_DISTANCE;
extern uint16_t GS_KEY_COST;
// ... etc

// Initialize common keys (called once at engine startup)
void gs_common_keys_init(void);

// gs_common_keys.c
uint16_t GS_KEY_MODE;
uint16_t GS_KEY_LAT;
uint16_t GS_KEY_LON;
uint16_t GS_KEY_TIME;
uint16_t GS_KEY_DISTANCE;
uint16_t GS_KEY_COST;

void gs_common_keys_init(void) {
    GS_KEY_MODE = gs_string_dict_register("mode");
    GS_KEY_LAT = gs_string_dict_register("lat");
    GS_KEY_LON = gs_string_dict_register("lon");
    GS_KEY_TIME = gs_string_dict_register("time");
    GS_KEY_DISTANCE = gs_string_dict_register("distance");
    GS_KEY_COST = gs_string_dict_register("cost");
    // ... register other common keys
}
```

#### 3. Updated Core Structures

**Vertex Structure**:
```c
struct GraphserverVertex {
    GraphserverKeyPair* pairs;  // Now uses ushort keys directly
    size_t num_pairs;
    uint64_t hash;
    bool hash_provided;
};
```

**Edge Metadata**:
```c
struct GraphserverEdge {
    GraphserverVertex* target_vertex;
    double* distance_vector;
    size_t distance_vector_size;
    GraphserverKeyPair* metadata;  // Now uses ushort keys directly
    size_t metadata_count;
    bool owns_target_vertex;
};
```

#### 4. Updated Public API

The API now directly uses ushort keys:

```c
// Vertex creation with ushort keys
GraphserverVertex* gs_vertex_create(
    const GraphserverKeyPair* pairs,  // Uses ushort keys
    size_t num_pairs,
    const uint64_t* optional_hash
);

// Vertex access functions
GraphserverResult gs_vertex_get_value(const GraphserverVertex* vertex, 
                                      uint16_t key,  // Use ushort key
                                      GraphserverValue* out_value);

GraphserverResult gs_vertex_has_key(const GraphserverVertex* vertex, 
                                    uint16_t key,  // Use ushort key
                                    bool* out_has_key);

// Edge metadata functions
GraphserverResult gs_edge_set_metadata(GraphserverEdge* edge, 
                                       uint16_t key,  // Use ushort key
                                       GraphserverValue value);

GraphserverResult gs_edge_get_metadata(const GraphserverEdge* edge, 
                                       uint16_t key,  // Use ushort key
                                       GraphserverValue* out_value);

// Helper function for debugging/display
const char* gs_key_to_string(uint16_t key);  // Returns string from dictionary
```

### Memory Layout Optimization

#### Before (Current Implementation)
```
Vertex with 4 keys:
[ptr→"lat"] [value] [ptr→"lon"] [value] [ptr→"time"] [value] [ptr→"mode"] [value]
= 4 * (8 bytes ptr + value_size) + external string storage
```

#### After (Optimized Implementation)
```
Vertex with 4 keys:
[ushort:2] [value] [ushort:3] [value] [ushort:4] [value] [ushort:1] [value]
= 4 * (2 bytes + value_size)
```

**Memory Savings Example**:
- 1 million vertices with 4 keys each
- Current: 32 MB (just for key pointers) + string storage
- Optimized: 8 MB (for ushort IDs)
- **Savings: 24+ MB (75% reduction in key storage)**

## Implementation Strategy

### Phase 1: Core Infrastructure
1. Implement `gs_string_dict.h/c` as a pure dictionary service with thread-safe operations
2. Implement `gs_common_keys.h/c` to define and register common keys
3. Add unit tests for dictionary operations

### Phase 2: Core API Update
1. Update `GraphserverKeyPair` to use uint16_t keys
2. Modify vertex/edge structures to use the new key type
3. Update all API functions to accept uint16_t keys
4. Update all tests to use the new API

### Phase 3: Provider Optimization
1. Update example providers to use pre-defined constants
2. Add provider-specific key registration
3. Benchmark memory usage and performance

### Phase 4: Language Bindings
1. Update Python extension to handle key translation
2. Expose key registration API for dynamic providers
3. Add convenience methods for common operations

## Thread Safety

The string dictionary uses read-write locks:
- **Read operations** (gs_string_dict_get): Multiple concurrent readers
- **Write operations** (gs_string_dict_register): Exclusive access
- **Initialization**: Once at program startup
- **Cleanup**: Once at program shutdown

## Performance Considerations

### Benefits
1. **Reduced memory usage**: 75% reduction in key storage overhead
2. **Faster comparisons**: Integer comparison vs string comparison
3. **Better cache locality**: Contiguous memory layout
4. **Reduced allocations**: No string duplication needed

### Trade-offs
1. **Lookup overhead**: One extra indirection for string retrieval
2. **Initialization cost**: Dictionary setup at program start
3. **Limit of 65,536 unique keys**: Sufficient for all practical uses

## Migration Guide

### For Core Developers
```c
// Include common keys header
#include "gs_common_keys.h"

// Direct usage with ushort keys
GraphserverKeyPair pairs[] = {
    {GS_KEY_LAT, gs_value_create_float(47.6097)},
    {GS_KEY_LON, gs_value_create_float(-122.3331)}
};

GraphserverVertex* vertex = gs_vertex_create(pairs, 2, NULL);
```

### For Provider Developers
```c
// Register provider-specific keys at initialization
static uint16_t KEY_ROAD_TYPE;
static uint16_t KEY_SPEED_LIMIT;

void road_provider_init() {
    KEY_ROAD_TYPE = gs_string_dict_register("road_type");
    KEY_SPEED_LIMIT = gs_string_dict_register("speed_limit");
}

// Use registered keys in edge generation
gs_edge_set_metadata(edge, KEY_ROAD_TYPE, value);
```

### For Python Users
```python
# Import common keys
from graphserver.core import Keys, register_keys

# Use pre-defined keys
vertex = Vertex({
    Keys.LAT: 47.6097,
    Keys.LON: -122.3331,
    Keys.TIME: 1234567890
})

# Register custom keys
my_keys = register_keys(["custom_key_1", "custom_key_2"])
vertex = Vertex({
    my_keys["custom_key_1"]: "value1",
    my_keys["custom_key_2"]: "value2"
})
```

## Testing Strategy

1. **Unit tests**: Dictionary operations, thread safety, edge cases
2. **Integration tests**: Vertex/edge creation with both APIs
3. **Performance benchmarks**: Memory usage, lookup speed
4. **Migration tests**: Ensure all code is properly migrated
5. **Stress tests**: Many threads registering keys simultaneously

## Future Enhancements

1. **Persistent dictionary**: Save/load dictionary for faster startup
2. **Key namespacing**: Reserve ranges for different providers
3. **Compression**: Further optimize value storage
4. **Statistics**: Track key usage frequency for optimization

## Conclusion

The ushort key dictionary system provides significant memory savings and performance improvements through a clean, direct implementation. Since we're still pre-release, we can make these changes without backward compatibility concerns.

### Expected Impact
- **Memory reduction**: 50-75% for key storage
- **Performance improvement**: 10-20% faster key lookups
- **Cleaner API**: Direct use of ushort keys throughout
- **Future-proof**: Room for 65,536 unique keys