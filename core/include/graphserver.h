#ifndef GRAPHSERVER_H
#define GRAPHSERVER_H

/**
 * @file graphserver.h
 * @brief Main header file for the Graphserver Planning Engine
 * 
 * This is the primary header file that applications should include to use
 * the Graphserver Planning Engine. It provides a high-level C API for
 * graph-based planning and pathfinding.
 * 
 * The Graphserver Planning Engine is a general-purpose, high-performance
 * planning library designed for flexibility and embeddability. It models
 * problems as a graph where a Vertex represents a state and an Edge 
 * represents a valid transition between states.
 * 
 * Key concepts:
 * - Vertex: A state representation using key-value pairs
 * - Edge: A transition between vertices with associated costs
 * - Edge Provider: Pluggable modules that generate edges from vertices
 * - Engine: Coordinates providers and planners to find paths
 * - Planner: Algorithms like Dijkstra and A* that search for optimal paths
 */

#include "gs_types.h"
#include "gs_vertex.h"
#include "gs_edge.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @defgroup version Version Information
 * @{
 */

#define GRAPHSERVER_VERSION_MAJOR 1
#define GRAPHSERVER_VERSION_MINOR 0
#define GRAPHSERVER_VERSION_PATCH 0

/**
 * Get the version string of the Graphserver library
 * @return Version string (e.g., "1.0.0")
 */
const char* gs_get_version(void);

/** @} */

/**
 * @defgroup engine Engine Management
 * @{
 */

/**
 * Create a new Graphserver engine instance
 * @return New engine instance, or NULL on failure
 */
GraphserverEngine* gs_engine_create(void);

/**
 * Destroy a Graphserver engine instance
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
 * List all registered providers
 * @param engine Target engine
 * @param out_provider_names Array of provider names (caller must free)
 * @param out_count Number of providers
 * @return Result code
 */
GraphserverResult gs_engine_list_providers(
    const GraphserverEngine* engine,
    const char*** out_provider_names,
    size_t* out_count
);

/** @} */

/**
 * @defgroup planning Path Planning
 * @{
 */

/**
 * Find a path from start to goal using the specified planner
 * @param engine Engine instance with registered providers
 * @param options Planning options and parameters
 * @return List of paths found, or NULL on failure
 */
GraphserverPathList* gs_plan(
    GraphserverEngine* engine,
    const GraphserverPlanOptions* options
);

/**
 * Find a simple path using default Dijkstra planner
 * @param engine Engine instance
 * @param start_vertex Starting vertex
 * @param is_goal Goal predicate function
 * @param goal_user_data User data for goal predicate
 * @return Single path, or NULL if no path found
 */
GraphserverPath* gs_plan_simple(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data
);

/** @} */

/**
 * @defgroup path Path Management
 * @{
 */

/**
 * Get the number of paths in a path list
 * @param path_list Path list to query
 * @return Number of paths
 */
size_t gs_pathlist_get_count(const GraphserverPathList* path_list);

/**
 * Get a specific path from a path list
 * @param path_list Path list to query
 * @param index Index of the path (0-based)
 * @return Path at the specified index, or NULL if invalid index
 */
GraphserverPath* gs_pathlist_get_path(const GraphserverPathList* path_list, size_t index);

/**
 * Destroy a path list and all contained paths
 * @param path_list Path list to destroy
 */
void gs_pathlist_destroy(GraphserverPathList* path_list);

/**
 * Get the number of edges in a path
 * @param path Path to query
 * @return Number of edges
 */
size_t gs_path_get_num_edges(const GraphserverPath* path);

/**
 * Get a specific edge from a path
 * @param path Path to query
 * @param index Index of the edge (0-based)
 * @return Edge at the specified index, or NULL if invalid index
 */
const GraphserverEdge* gs_path_get_edge(const GraphserverPath* path, size_t index);

/**
 * Get the total cost of a path
 * @param path Path to query
 * @return Cost vector (array of doubles), or NULL if path is empty
 */
const double* gs_path_get_total_cost(const GraphserverPath* path);

/**
 * Get the size of the cost vector for a path
 * @param path Path to query
 * @return Size of the cost vector
 */
size_t gs_path_get_cost_vector_size(const GraphserverPath* path);

/**
 * Destroy a single path
 * @param path Path to destroy
 */
void gs_path_destroy(GraphserverPath* path);

/**
 * Create a string representation of a path (for debugging)
 * @param path Path to convert
 * @return String representation (caller must free), or NULL on failure
 */
char* gs_path_to_string(const GraphserverPath* path);

/** @} */

/**
 * @defgroup utility Utility Functions
 * @{
 */

/**
 * Get a human-readable error message for a result code
 * @param result Result code
 * @return Error message string
 */
const char* gs_get_error_message(GraphserverResult result);

/**
 * Initialize the Graphserver library (call once at startup)
 * @return Result code
 */
GraphserverResult gs_initialize(void);

/**
 * Cleanup the Graphserver library (call once at shutdown)
 */
void gs_cleanup(void);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GRAPHSERVER_H