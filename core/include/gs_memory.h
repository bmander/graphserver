#ifndef GS_MEMORY_H
#define GS_MEMORY_H

#include "gs_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file gs_memory.h
 * @brief Memory management for the Graphserver Planning Engine
 * 
 * This module provides efficient memory allocation strategies optimized for
 * planning operations. The primary component is an arena allocator that
 * reduces allocation overhead during graph expansion and pathfinding.
 * 
 * Key features:
 * - Arena allocation for bulk memory management
 * - Proper alignment for all data types
 * - Fast reset for reusing memory pools
 * - Memory tracking and statistics
 */

/**
 * @defgroup memory Memory Management
 * @{
 */

// Forward declaration
typedef struct GraphserverArena GraphserverArena;

// Memory alignment (typically 8 bytes for 64-bit systems)
#define GS_MEMORY_ALIGNMENT 8

// Default arena size (1MB)
#define GS_DEFAULT_ARENA_SIZE (1024 * 1024)

// Minimum arena size (4KB)
#define GS_MIN_ARENA_SIZE (4 * 1024)

/**
 * Memory statistics for monitoring usage
 */
typedef struct {
    size_t total_allocated;     // Total bytes allocated from arena
    size_t total_requested;     // Total bytes requested by users
    size_t peak_usage;          // Peak memory usage
    size_t num_allocations;     // Number of allocation calls
    size_t num_resets;          // Number of arena resets
    size_t num_blocks;          // Number of memory blocks in arena
} GraphserverMemoryStats;

/**
 * Create a new arena allocator
 * @param initial_size Initial size of the arena in bytes
 * @return New arena instance, or NULL on failure
 */
GraphserverArena* gs_arena_create(size_t initial_size);

/**
 * Allocate memory from the arena
 * @param arena Arena to allocate from
 * @param size Number of bytes to allocate
 * @return Pointer to allocated memory, or NULL on failure
 */
void* gs_arena_alloc(GraphserverArena* arena, size_t size);

/**
 * Allocate aligned memory from the arena
 * @param arena Arena to allocate from
 * @param size Number of bytes to allocate
 * @param alignment Alignment requirement (must be power of 2)
 * @return Pointer to aligned allocated memory, or NULL on failure
 */
void* gs_arena_alloc_aligned(GraphserverArena* arena, size_t size, size_t alignment);

/**
 * Allocate zeroed memory from the arena
 * @param arena Arena to allocate from
 * @param count Number of elements
 * @param size Size of each element
 * @return Pointer to zeroed allocated memory, or NULL on failure
 */
void* gs_arena_calloc(GraphserverArena* arena, size_t count, size_t size);

/**
 * Reset the arena, making all allocated memory available for reuse
 * This is much faster than destroying and recreating the arena
 * @param arena Arena to reset
 */
void gs_arena_reset(GraphserverArena* arena);

/**
 * Get memory statistics for the arena
 * @param arena Arena to query
 * @param out_stats Pointer to statistics structure to fill
 * @return Result code
 */
GraphserverResult gs_arena_get_stats(const GraphserverArena* arena, GraphserverMemoryStats* out_stats);

/**
 * Get the current memory usage of the arena
 * @param arena Arena to query
 * @return Number of bytes currently allocated
 */
size_t gs_arena_get_usage(const GraphserverArena* arena);

/**
 * Check if the arena can allocate a given amount of memory
 * @param arena Arena to query
 * @param size Number of bytes to check
 * @return True if allocation would succeed, false otherwise
 */
bool gs_arena_can_alloc(const GraphserverArena* arena, size_t size);

/**
 * Destroy the arena and free all associated memory
 * @param arena Arena to destroy
 */
void gs_arena_destroy(GraphserverArena* arena);

/**
 * Helper macros for typed allocation
 */
#define gs_arena_alloc_type(arena, type) \
    ((type*)gs_arena_alloc_aligned((arena), sizeof(type), _Alignof(type)))

#define gs_arena_alloc_array(arena, type, count) \
    ((type*)gs_arena_alloc_aligned((arena), sizeof(type) * (count), _Alignof(type)))

#define gs_arena_calloc_type(arena, type) \
    ((type*)gs_arena_calloc((arena), 1, sizeof(type)))

#define gs_arena_calloc_array(arena, type, count) \
    ((type*)gs_arena_calloc((arena), (count), sizeof(type)))

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GS_MEMORY_H