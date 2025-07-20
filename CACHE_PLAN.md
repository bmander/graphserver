# Edge Cache Implementation Plan

This document outlines the plan to implement an edge caching feature in the Graphserver engine. The goal is to cache adjacent edges fetched from edge providers to accelerate subsequent fetches for the same vertex.

## 1. Analysis

-   **Core Logic:** The primary point for edge fetching is the `gs_engine_expand_vertex` function in `core/src/engine.c`. This function iterates through registered providers to generate edges for a given vertex.
-   **Data Structures:** The `GraphserverEngine` struct defined in `core/include/gs_engine.h` is the central object for the engine's state.
-   **Vertex Identity:** The `gs_vertex.h` header provides `gs_vertex_hash` and `gs_vertex_equals` functions, which are essential for using `GraphserverVertex` objects as keys in a hash table-based cache.

## 2. Implementation Steps

### Step 2.1: Introduce Cache Data Structures

-   **Modify `core/include/gs_engine.h`:**
    -   Add a forward declaration for a new `EdgeCache` struct: `typedef struct EdgeCache EdgeCache;`
    -   Add a new field to the `GraphserverEngineConfig` struct: `bool enable_edge_caching;` to allow enabling/disabling the cache.
    -   Add a new member to the `GraphserverEngine` struct (defined in `core/src/engine.c`): `EdgeCache* edge_cache;`.

-   **Create `core/src/cache.c` and `core/include/gs_cache.h` (or similar):**
    -   Define the `EdgeCache` struct. It will wrap a hash table (`HashTable*`). The hash table will map a vertex hash (`uint64_t`) to a cached `GraphserverEdgeList*`.
    -   Implement the following functions:
        -   `edge_cache_create()`: Initializes the cache and its hash table.
        -   `edge_cache_destroy()`: Frees the cache and all its contents (including the cached edge lists).
        -   `edge_cache_get()`: Retrieves an edge list from the cache for a given vertex.
        -   `edge_cache_put()`: Stores a copy of an edge list in the cache for a given vertex.
        -   `edge_cache_clear()`: Clears all entries from the cache.

### Step 2.2: Integrate Cache into Engine Lifecycle

-   **Modify `core/src/engine.c`:**
    -   In `gs_engine_create_with_config`:
        -   Initialize the `edge_cache` by calling `edge_cache_create()` if `config.enable_edge_caching` is true.
        -   Set the default value for `enable_edge_caching` in `gs_engine_get_default_config`.
    -   In `gs_engine_destroy`:
        -   Call `edge_cache_destroy()` to clean up the cache.

### Step 2.3: Implement Caching Logic

-   **Modify `gs_engine_expand_vertex` in `core/src/engine.c`:**
    -   At the beginning of the function, check if caching is enabled (`engine->config.enable_edge_caching`).
    -   If enabled, attempt to retrieve the edge list from `engine->edge_cache` using the vertex.
    -   **Cache Hit:** If an entry is found, copy the cached `GraphserverEdgeList` into the `out_edges` list and return immediately. This bypasses the provider calls.
    -   **Cache Miss:** If no entry is found, proceed with the existing logic of calling the providers.
    -   After successfully gathering all edges from the providers into `out_edges`, if caching is enabled, `put` a copy of the `out_edges` list into the `engine->edge_cache` using the current vertex as the key.

### Step 2.4: Handle Cache Invalidation

-   **Modify `core/src/engine.c`:**
    -   Create a new internal function `gs_engine_clear_cache(GraphserverEngine* engine)` that calls `edge_cache_clear()`.
    -   Call this new `gs_engine_clear_cache` function from within:
        -   `gs_engine_register_provider()`
        -   `gs_engine_unregister_provider()`
        -   `gs_engine_set_provider_enabled()`
        -   `gs_engine_set_config()` (if the caching configuration changes)
    This ensures that any change to the graph generation logic invalidates the cache.

### Step 2.5: Update Testing

-   **Modify `core/tests/test_performance.c`:**
    -   Add a new test case specifically for the edge cache.
    -   In this test:
        1.  Create an engine with caching enabled.
        2.  Expand a specific vertex for the first time and record the execution time.
        3.  Expand the *same* vertex a second time and record the execution time.
        4.  Assert that the second expansion is significantly faster than the first.
        5.  Optionally, check that the `providers_called` statistic is incremented on the first call but not the second.
-   **Modify `core/tests/test_engine.c`:**
    -   Add tests to verify that the cache is correctly invalidated when providers are added, removed, or disabled.

This plan provides a clear path to implementing the edge caching feature, including the necessary data structures, logic integration, and verification through testing.
