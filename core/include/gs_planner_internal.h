#ifndef GS_PLANNER_INTERNAL_H
#define GS_PLANNER_INTERNAL_H

/**
 * @file gs_planner_internal.h
 * @brief Internal header for planner implementations
 * 
 * This header contains internal structures and functions used by planner
 * implementations. It is not part of the public API.
 */

#include "gs_types.h"
#include "gs_vertex.h"
#include "gs_edge.h"
#include "gs_memory.h"
#include "gs_engine.h"

#ifdef __cplusplus
extern "C" {
#endif

// Forward declarations
typedef struct PriorityQueue PriorityQueue;
typedef struct HashTable VertexSet;

/**
 * @defgroup priority_queue Priority Queue
 * @brief Binary min-heap for efficient vertex selection
 * @{
 */

/**
 * Create a new priority queue
 * @param arena Optional arena allocator for memory management
 * @return New priority queue instance, or NULL on failure
 */
PriorityQueue* pq_create(GraphserverArena* arena);

/**
 * Insert vertex with cost into priority queue
 * @param pq Priority queue
 * @param vertex Vertex to insert
 * @param cost Cost value for priority ordering
 * @return true on success, false on failure
 */
bool pq_insert(PriorityQueue* pq, GraphserverVertex* vertex, double cost);

/**
 * Extract minimum cost vertex from priority queue
 * @param pq Priority queue
 * @param out_vertex Output vertex pointer
 * @param out_cost Optional output cost value
 * @return true if vertex extracted, false if queue empty
 */
bool pq_extract_min(PriorityQueue* pq, GraphserverVertex** out_vertex, double* out_cost);

/**
 * Decrease cost for vertex if it exists in queue
 * @param pq Priority queue
 * @param vertex Vertex to update
 * @param new_cost New cost value (must be less than current)
 * @return true if key decreased, false if not found or not decreased
 */
bool pq_decrease_key(PriorityQueue* pq, GraphserverVertex* vertex, double new_cost);

/**
 * Check if priority queue is empty
 * @param pq Priority queue
 * @return true if empty, false otherwise
 */
bool pq_is_empty(const PriorityQueue* pq);

/**
 * Get size of priority queue
 * @param pq Priority queue
 * @return Number of entries in queue
 */
size_t pq_size(const PriorityQueue* pq);

/**
 * Check if vertex exists in priority queue
 * @param pq Priority queue
 * @param vertex Vertex to search for
 * @return true if vertex found, false otherwise
 */
bool pq_contains(const PriorityQueue* pq, const GraphserverVertex* vertex);

/**
 * Peek at minimum vertex without extracting
 * @param pq Priority queue
 * @param out_vertex Output vertex pointer
 * @param out_cost Optional output cost value
 * @return true if vertex available, false if queue empty
 */
bool pq_peek_min(const PriorityQueue* pq, GraphserverVertex** out_vertex, double* out_cost);

/**
 * Clear all entries from priority queue
 * @param pq Priority queue
 */
void pq_clear(PriorityQueue* pq);

/**
 * Destroy priority queue and free memory
 * @param pq Priority queue
 */
void pq_destroy(PriorityQueue* pq);

/**
 * Validate heap property (for debugging)
 * @param pq Priority queue
 * @return true if heap property is satisfied
 */
bool pq_validate_heap(const PriorityQueue* pq);

/** @} */

/**
 * @defgroup vertex_set Vertex Set (Closed Set)
 * @brief Hash table for tracking visited vertices
 * @{
 */

/**
 * Create vertex set for closed set tracking
 * @param arena Arena allocator for memory management
 * @return New vertex set instance, or NULL on failure
 */
VertexSet* vertex_set_create(GraphserverArena* arena);

/**
 * Add vertex to closed set
 * @param set Vertex set
 * @param vertex Vertex to add
 * @return true on success, false on failure
 */
bool vertex_set_add(VertexSet* set, GraphserverVertex* vertex);

/**
 * Check if vertex is in closed set
 * @param set Vertex set
 * @param vertex Vertex to check
 * @return true if vertex is in set, false otherwise
 */
bool vertex_set_contains(const VertexSet* set, const GraphserverVertex* vertex);

/**
 * Clear all vertices from set
 * @param set Vertex set
 */
void vertex_set_clear(VertexSet* set);

/**
 * Destroy vertex set
 * @param set Vertex set
 */
void vertex_set_destroy(VertexSet* set);

/** @} */

/**
 * @defgroup path_internal Path Management Functions
 * @brief Internal functions for path management
 * @{
 */

/**
 * Create a new path with specified cost vector size
 * @param cost_vector_size Size of the cost vector
 * @return New path instance, or NULL on failure
 */
GraphserverPath* gs_path_create(size_t cost_vector_size);

/**
 * Destroy a path and free its memory
 * @param path Path to destroy
 */
void gs_path_destroy(GraphserverPath* path);

/** @} */

/**
 * @defgroup dijkstra_internal Dijkstra Internal Structures
 * @brief Internal data structures for Dijkstra implementation
 * @{
 */

// Dijkstra search node
typedef struct DijkstraNode {
    GraphserverVertex* vertex;
    GraphserverVertex* parent;
    double cost;
    struct DijkstraNode* next; // For hash table chaining
} DijkstraNode;

// Dijkstra search state
typedef struct {
    PriorityQueue* open_set;
    VertexSet* closed_set;
    DijkstraNode* nodes;
    size_t node_count;
    size_t node_capacity;
    GraphserverArena* arena;
    
    // Search configuration
    const GraphserverVertex* start_vertex;
    gs_goal_predicate_fn is_goal;
    void* goal_user_data;
    double timeout_seconds;
    
    // Statistics
    size_t vertices_expanded;
    size_t edges_examined;
    size_t nodes_generated;
    double search_time_seconds;
    bool timeout_reached;
    bool goal_found;
} DijkstraState;

/**
 * Initialize Dijkstra search state
 * @param state Dijkstra state structure
 * @param start_vertex Starting vertex for search
 * @param is_goal Goal predicate function
 * @param goal_user_data User data for goal predicate
 * @param arena Arena allocator for memory management
 * @param timeout_seconds Maximum search time
 * @return GS_SUCCESS on success, error code on failure
 */
GraphserverResult dijkstra_init(
    DijkstraState* state,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    GraphserverArena* arena,
    double timeout_seconds
);

/**
 * Run Dijkstra search
 * @param state Initialized Dijkstra state
 * @param engine Engine instance for vertex expansion
 * @param out_path Output path if goal found
 * @return GS_SUCCESS if goal found, GS_ERROR_NO_PATH_FOUND if no path, error code on failure
 */
GraphserverResult dijkstra_search(
    DijkstraState* state,
    GraphserverEngine* engine,
    GraphserverPath** out_path
);

/**
 * Clean up Dijkstra search state
 * @param state Dijkstra state structure
 */
void dijkstra_cleanup(DijkstraState* state);

/**
 * Run Dijkstra planning algorithm
 * @param engine Engine instance for vertex expansion
 * @param start_vertex Starting vertex for search
 * @param is_goal Goal predicate function
 * @param goal_user_data User data for goal predicate
 * @param timeout_seconds Maximum search time (0 for no timeout)
 * @param arena Arena allocator for memory management
 * @param out_path Output path if goal found
 * @param out_stats Optional statistics output
 * @return GS_SUCCESS if goal found, error code otherwise
 */
GraphserverResult gs_plan_dijkstra(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    double timeout_seconds,
    GraphserverArena* arena,
    GraphserverPath** out_path,
    GraphserverPlanStats* out_stats
);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GS_PLANNER_INTERNAL_H