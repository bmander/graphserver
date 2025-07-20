#include "../include/gs_cache.h"
#include "../include/gs_memory.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/**
 * @file cache.c
 * @brief Edge cache implementation for vertex expansion acceleration
 * 
 * This module implements an edge cache that stores GraphserverEdgeList objects
 * keyed by vertex hash for fast retrieval during graph expansion operations.
 */

// Hash table entry for the edge cache
typedef struct CacheEntry {
    GraphserverVertex* vertex;     // Key vertex (owned by cache)
    GraphserverEdgeList* edges;    // Cached edge list (owned by cache)
    uint64_t hash;                 // Cached vertex hash
    struct CacheEntry* next;       // For collision chaining
} CacheEntry;

// Edge cache structure
struct EdgeCache {
    CacheEntry** buckets;          // Hash table buckets
    size_t bucket_count;           // Number of buckets (power of 2)
    size_t size;                   // Number of cached entries
    size_t mask;                   // bucket_count - 1 (for fast modulo)
};

// Constants
#define INITIAL_BUCKET_COUNT 32
#define MAX_LOAD_FACTOR 0.75

// Helper function to create a deep copy of an edge list
static GraphserverEdgeList* edge_list_deep_copy(const GraphserverEdgeList* source) {
    if (!source) return NULL;
    
    GraphserverEdgeList* copy = gs_edge_list_create();
    if (!copy) return NULL;
    
    // Set the edge list to own the edges so they get properly destroyed
    gs_edge_list_set_owns_edges(copy, true);
    
    size_t edge_count = gs_edge_list_get_count(source);
    for (size_t i = 0; i < edge_count; i++) {
        GraphserverEdge* edge;
        GraphserverResult result = gs_edge_list_get_edge(source, i, &edge);
        if (result == GS_SUCCESS && edge) {
            // Create a deep copy of the edge
            GraphserverEdge* edge_copy = gs_edge_clone(edge);
            if (edge_copy) {
                gs_edge_list_add_edge(copy, edge_copy);
            }
        }
    }
    
    return copy;
}

// Helper function to destroy a cache entry
static void cache_entry_destroy(CacheEntry* entry) {
    if (!entry) return;
    
    if (entry->vertex) {
        gs_vertex_destroy(entry->vertex);
    }
    if (entry->edges) {
        gs_edge_list_destroy(entry->edges);
    }
    free(entry);
}

// Helper function to resize the hash table
static bool cache_resize(EdgeCache* cache) {
    if (!cache) return false;
    
    size_t old_bucket_count = cache->bucket_count;
    CacheEntry** old_buckets = cache->buckets;
    
    // Double the bucket count
    size_t new_bucket_count = old_bucket_count * 2;
    CacheEntry** new_buckets = calloc(new_bucket_count, sizeof(CacheEntry*));
    if (!new_buckets) return false;
    
    // Update cache structure
    cache->buckets = new_buckets;
    cache->bucket_count = new_bucket_count;
    cache->mask = new_bucket_count - 1;
    cache->size = 0;
    
    // Rehash all entries
    for (size_t i = 0; i < old_bucket_count; i++) {
        CacheEntry* entry = old_buckets[i];
        while (entry) {
            CacheEntry* next = entry->next;
            
            // Insert into new table
            size_t bucket_index = entry->hash & cache->mask;
            entry->next = cache->buckets[bucket_index];
            cache->buckets[bucket_index] = entry;
            cache->size++;
            
            entry = next;
        }
    }
    
    free(old_buckets);
    return true;
}

// Public API implementation

EdgeCache* edge_cache_create(void) {
    EdgeCache* cache = malloc(sizeof(EdgeCache));
    if (!cache) return NULL;
    
    cache->buckets = calloc(INITIAL_BUCKET_COUNT, sizeof(CacheEntry*));
    if (!cache->buckets) {
        free(cache);
        return NULL;
    }
    
    cache->bucket_count = INITIAL_BUCKET_COUNT;
    cache->size = 0;
    cache->mask = INITIAL_BUCKET_COUNT - 1;
    
    return cache;
}

void edge_cache_destroy(EdgeCache* cache) {
    if (!cache) return;
    
    // Clear all entries first
    edge_cache_clear(cache);
    
    // Free the bucket array
    free(cache->buckets);
    free(cache);
}

GraphserverResult edge_cache_get(
    const EdgeCache* cache,
    const GraphserverVertex* vertex,
    GraphserverEdgeList** out_edges) {
    
    if (!cache || !vertex || !out_edges) {
        return GS_ERROR_NULL_POINTER;
    }
    
    uint64_t hash = gs_vertex_hash(vertex);
    size_t bucket_index = hash & cache->mask;
    
    // Search for the vertex in the bucket chain
    CacheEntry* entry = cache->buckets[bucket_index];
    while (entry) {
        if (entry->hash == hash && gs_vertex_equals(entry->vertex, vertex)) {
            // Found! Create a deep copy of the cached edge list
            *out_edges = edge_list_deep_copy(entry->edges);
            return (*out_edges) ? GS_SUCCESS : GS_ERROR_OUT_OF_MEMORY;
        }
        entry = entry->next;
    }
    
    return GS_ERROR_KEY_NOT_FOUND;
}

GraphserverResult edge_cache_put(
    EdgeCache* cache,
    const GraphserverVertex* vertex,
    const GraphserverEdgeList* edges) {
    
    if (!cache || !vertex || !edges) {
        return GS_ERROR_NULL_POINTER;
    }
    
    uint64_t hash = gs_vertex_hash(vertex);
    size_t bucket_index = hash & cache->mask;
    
    // Check if entry already exists
    CacheEntry* existing = cache->buckets[bucket_index];
    while (existing) {
        if (existing->hash == hash && gs_vertex_equals(existing->vertex, vertex)) {
            // Update existing entry
            gs_edge_list_destroy(existing->edges);
            existing->edges = edge_list_deep_copy(edges);
            return existing->edges ? GS_SUCCESS : GS_ERROR_OUT_OF_MEMORY;
        }
        existing = existing->next;
    }
    
    // Check load factor and resize if needed
    double load_factor = (double)(cache->size + 1) / cache->bucket_count;
    if (load_factor > MAX_LOAD_FACTOR) {
        if (!cache_resize(cache)) {
            return GS_ERROR_OUT_OF_MEMORY;
        }
        // Recalculate bucket index after resize
        bucket_index = hash & cache->mask;
    }
    
    // Create new entry
    CacheEntry* entry = malloc(sizeof(CacheEntry));
    if (!entry) return GS_ERROR_OUT_OF_MEMORY;
    
    entry->vertex = gs_vertex_clone(vertex);
    entry->edges = edge_list_deep_copy(edges);
    entry->hash = hash;
    
    if (!entry->vertex || !entry->edges) {
        cache_entry_destroy(entry);
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Insert at head of bucket chain
    entry->next = cache->buckets[bucket_index];
    cache->buckets[bucket_index] = entry;
    cache->size++;
    
    return GS_SUCCESS;
}

void edge_cache_clear(EdgeCache* cache) {
    if (!cache) return;
    
    for (size_t i = 0; i < cache->bucket_count; i++) {
        CacheEntry* entry = cache->buckets[i];
        while (entry) {
            CacheEntry* next = entry->next;
            cache_entry_destroy(entry);
            entry = next;
        }
        cache->buckets[i] = NULL;
    }
    
    cache->size = 0;
}

size_t edge_cache_size(const EdgeCache* cache) {
    return cache ? cache->size : 0;
}

bool edge_cache_contains(const EdgeCache* cache, const GraphserverVertex* vertex) {
    if (!cache || !vertex) return false;
    
    uint64_t hash = gs_vertex_hash(vertex);
    size_t bucket_index = hash & cache->mask;
    
    CacheEntry* entry = cache->buckets[bucket_index];
    while (entry) {
        if (entry->hash == hash && gs_vertex_equals(entry->vertex, vertex)) {
            return true;
        }
        entry = entry->next;
    }
    
    return false;
}