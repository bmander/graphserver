#ifndef GS_ENGINE_H
#define GS_ENGINE_H

#include "gs_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file gs_engine.h
 * @brief Engine and Graph Expander for the Graphserver Planning Engine
 * 
 * This module provides the core engine that coordinates edge providers
 * and planning algorithms. The engine manages provider registration,
 * graph expansion, and memory allocation for planning operations.
 */

/**
 * @defgroup engine Engine Management
 * @{
 */

// Forward declarations
typedef struct GraphserverEngine GraphserverEngine;
typedef struct GraphserverPath GraphserverPath;
typedef struct GraphserverPathList GraphserverPathList;
typedef struct EdgeCache EdgeCache;

/**
 * Engine configuration options
 */
typedef struct {
    size_t default_arena_size;      // Default arena size for planning operations
    size_t max_memory_limit;        // Maximum memory limit (0 = no limit)
    double default_timeout_seconds; // Default timeout for planning operations
    bool enable_concurrent_expansion; // Enable concurrent edge provider execution
    uint32_t max_worker_threads;    // Maximum worker threads for concurrent expansion
    bool enable_edge_caching;       // Enable edge caching for vertex expansion
} GraphserverEngineConfig;

/**
 * Provider information structure
 */
typedef struct {
    const char* name;
    gs_generate_edges_fn generator;
    void* user_data;
    bool is_enabled;
} GraphserverProviderInfo;

/**
 * Planning statistics
 */
typedef struct {
    uint64_t vertices_expanded;     // Number of vertices expanded
    uint64_t edges_generated;       // Number of edges generated
    uint64_t providers_called;      // Number of provider calls
    double planning_time_seconds;   // Total planning time
    size_t peak_memory_usage;       // Peak memory usage during planning
    uint32_t path_length;           // Length of found path (0 if no path)
    uint64_t cache_hits;            // Number of successful cache lookups
    uint64_t cache_misses;          // Number of cache misses
    uint64_t cache_puts;            // Number of entries stored in cache
} GraphserverPlanStats;

/**
 * Create a new engine with default configuration
 * @return New engine instance, or NULL on failure
 */
GraphserverEngine* gs_engine_create(void);

/**
 * Create a new engine with custom configuration
 * @param config Engine configuration options
 * @return New engine instance, or NULL on failure
 */
GraphserverEngine* gs_engine_create_with_config(const GraphserverEngineConfig* config);

/**
 * Destroy an engine instance
 * @param engine Engine to destroy
 */
void gs_engine_destroy(GraphserverEngine* engine);

/**
 * Register an edge provider with the engine
 * @param engine Target engine
 * @param provider_name Unique name for the provider
 * @param generator_func Function that generates edges
 * @param user_data Optional user data passed to the generator function
 * @return Result code
 */
GraphserverResult gs_engine_register_provider(
    GraphserverEngine* engine,
    const char* provider_name,
    gs_generate_edges_fn generator_func,
    void* user_data
);

/**
 * Unregister an edge provider from the engine
 * @param engine Target engine
 * @param provider_name Name of the provider to remove
 * @return Result code
 */
GraphserverResult gs_engine_unregister_provider(
    GraphserverEngine* engine,
    const char* provider_name
);

/**
 * Enable or disable a specific provider
 * @param engine Target engine
 * @param provider_name Name of the provider
 * @param enabled Whether the provider should be enabled
 * @return Result code
 */
GraphserverResult gs_engine_set_provider_enabled(
    GraphserverEngine* engine,
    const char* provider_name,
    bool enabled
);

/**
 * List all registered providers
 * @param engine Target engine
 * @param out_provider_info Array of provider information (caller must free)
 * @param out_count Number of providers
 * @return Result code
 */
GraphserverResult gs_engine_list_providers(
    const GraphserverEngine* engine,
    GraphserverProviderInfo** out_provider_info,
    size_t* out_count
);

/**
 * Get the number of registered providers
 * @param engine Target engine
 * @return Number of providers, or 0 if engine is NULL
 */
size_t gs_engine_get_provider_count(const GraphserverEngine* engine);

/**
 * Check if a provider is registered
 * @param engine Target engine
 * @param provider_name Name of the provider
 * @return True if provider is registered, false otherwise
 */
bool gs_engine_has_provider(const GraphserverEngine* engine, const char* provider_name);

/**
 * Expand a vertex to get all outgoing edges
 * This is the core graph expansion operation used by planners
 * @param engine Engine instance
 * @param vertex Vertex to expand
 * @param out_edges List to store generated edges (must be created by caller)
 * @return Result code
 */
GraphserverResult gs_engine_expand_vertex(
    GraphserverEngine* engine,
    const GraphserverVertex* vertex,
    GraphserverEdgeList* out_edges
);

/**
 * Set engine configuration
 * @param engine Target engine
 * @param config New configuration
 * @return Result code
 */
GraphserverResult gs_engine_set_config(
    GraphserverEngine* engine,
    const GraphserverEngineConfig* config
);

/**
 * Get current engine configuration
 * @param engine Target engine
 * @param out_config Configuration structure to fill
 * @return Result code
 */
GraphserverResult gs_engine_get_config(
    const GraphserverEngine* engine,
    GraphserverEngineConfig* out_config
);

/**
 * Get current engine statistics
 * @param engine Target engine
 * @param out_stats Statistics structure to fill
 * @return Result code
 */
GraphserverResult gs_engine_get_stats(
    const GraphserverEngine* engine,
    GraphserverPlanStats* out_stats
);

/**
 * Get the default engine configuration
 * @return Default configuration structure
 */
GraphserverEngineConfig gs_engine_get_default_config(void);

/** @} */

/**
 * @defgroup planning Path Planning
 * @{
 */

/**
 * Find a path from start to goal using the specified planner
 * @param engine Engine instance with registered providers
 * @param options Planning options and parameters
 * @param out_stats Optional statistics output (can be NULL)
 * @return List of paths found, or NULL on failure
 */
GraphserverPathList* gs_plan(
    GraphserverEngine* engine,
    const GraphserverPlanOptions* options,
    GraphserverPlanStats* out_stats
);

/**
 * Find a simple path using default Dijkstra planner
 * @param engine Engine instance
 * @param start_vertex Starting vertex
 * @param is_goal Goal predicate function
 * @param goal_user_data User data for goal predicate
 * @param out_stats Optional statistics output (can be NULL)
 * @return Single path, or NULL if no path found
 */
GraphserverPath* gs_plan_simple(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    GraphserverPlanStats* out_stats
);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GS_ENGINE_H