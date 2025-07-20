#ifndef GS_CACHE_H
#define GS_CACHE_H

#include "gs_types.h"
#include "gs_vertex.h"
#include "gs_edge.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file gs_cache.h
 * @brief Edge caching system for the Graphserver Planning Engine
 * 
 * This module provides caching functionality to store and retrieve
 * edge lists for vertices to accelerate subsequent graph expansions.
 */

/**
 * @defgroup cache Edge Cache
 * @{
 */

// Forward declaration of EdgeCache structure
typedef struct EdgeCache EdgeCache;

/**
 * Create a new edge cache
 * @return New cache instance, or NULL on failure
 */
EdgeCache* edge_cache_create(void);

/**
 * Destroy an edge cache and free all memory
 * @param cache Cache to destroy (can be NULL)
 */
void edge_cache_destroy(EdgeCache* cache);

/**
 * Retrieve cached edge list for a vertex
 * @param cache Edge cache
 * @param vertex Vertex to look up
 * @param out_edges Output edge list (caller must destroy)
 * @return GS_SUCCESS if found, GS_ERROR_KEY_NOT_FOUND if not cached, other error codes on failure
 */
GraphserverResult edge_cache_get(
    const EdgeCache* cache,
    const GraphserverVertex* vertex,
    GraphserverEdgeList** out_edges
);

/**
 * Store a copy of an edge list in the cache for a vertex
 * @param cache Edge cache
 * @param vertex Vertex to cache edges for
 * @param edges Edge list to cache (will be deep copied)
 * @return GS_SUCCESS on success, error code on failure
 */
GraphserverResult edge_cache_put(
    EdgeCache* cache,
    const GraphserverVertex* vertex,
    const GraphserverEdgeList* edges
);

/**
 * Clear all entries from the cache
 * @param cache Edge cache
 */
void edge_cache_clear(EdgeCache* cache);

/**
 * Get the number of cached entries
 * @param cache Edge cache
 * @return Number of cached vertices, or 0 if cache is NULL
 */
size_t edge_cache_size(const EdgeCache* cache);

/**
 * Check if a vertex has cached edges
 * @param cache Edge cache
 * @param vertex Vertex to check
 * @return true if vertex is cached, false otherwise
 */
bool edge_cache_contains(const EdgeCache* cache, const GraphserverVertex* vertex);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GS_CACHE_H