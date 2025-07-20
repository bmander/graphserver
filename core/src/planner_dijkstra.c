#include "../include/gs_planner_internal.h"
#include "../include/gs_engine.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"
#include "../include/gs_memory.h"
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <assert.h>

// Forward declare the internal path structure
struct GraphserverPath {
    GraphserverEdge** edges;
    size_t num_edges;
    double* total_cost;
    size_t cost_vector_size;
};

/**
 * @file planner_dijkstra.c
 * @brief Dijkstra's algorithm implementation for single-objective pathfinding
 * 
 * This implementation provides a complete Dijkstra planner that integrates
 * with the Graphserver engine infrastructure. It uses arena allocation for
 * efficiency and supports early termination when a goal is found.
 */

// Constants
#define INITIAL_NODE_CAPACITY 256
#define NODE_HASH_SIZE 1024

// Helper function to get current time in seconds
static double get_current_time_seconds(void) {
    #ifdef _POSIX_C_SOURCE
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
    #else
    return (double)clock() / CLOCKS_PER_SEC;
    #endif
}

// Hash function for vertex pointer (simple pointer hash)
static size_t hash_vertex_pointer(const GraphserverVertex* vertex) {
    uintptr_t addr = (uintptr_t)vertex;
    return (addr >> 3) % NODE_HASH_SIZE; // Simple hash
}

// Find Dijkstra node for vertex
static DijkstraNode* find_dijkstra_node(DijkstraState* state, const GraphserverVertex* vertex) {
    size_t hash = hash_vertex_pointer(vertex);
    
    // Linear probing for collision resolution
    for (size_t i = 0; i < state->node_capacity; i++) {
        size_t index = (hash + i) % state->node_capacity;
        DijkstraNode* current = &state->nodes[index];
        
        if (!current->vertex) {
            return NULL; // Not found, empty slot
        }
        
        if (gs_vertex_equals(current->vertex, vertex)) {
            return current; // Found
        }
    }
    
    return NULL; // Table full or not found
}

// Create or update Dijkstra node
static DijkstraNode* get_or_create_dijkstra_node(DijkstraState* state, GraphserverVertex* vertex) {
    size_t hash = hash_vertex_pointer(vertex);
    
    // Linear probing for insertion
    for (size_t i = 0; i < state->node_capacity; i++) {
        size_t index = (hash + i) % state->node_capacity;
        DijkstraNode* node = &state->nodes[index];
        
        if (!node->vertex) {
            // Empty slot, create new node
            node->vertex = vertex;
            node->parent = NULL;
            node->cost = INFINITY;
            node->next = NULL;
            state->node_count++;
            return node;
        }
        
        if (gs_vertex_equals(node->vertex, vertex)) {
            return node; // Found existing
        }
    }
    
    return NULL; // Table full
}

// Initialize Dijkstra search state
GraphserverResult dijkstra_init(
    DijkstraState* state,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    GraphserverArena* arena,
    double timeout_seconds) {
    
    if (!state || !start_vertex || !is_goal || !arena) {
        return GS_ERROR_NULL_POINTER;
    }
    
    // Initialize state
    memset(state, 0, sizeof(DijkstraState));
    state->arena = arena;
    state->start_vertex = start_vertex;
    state->is_goal = is_goal;
    state->goal_user_data = goal_user_data;
    state->timeout_seconds = timeout_seconds;
    
    // Create priority queue
    state->open_set = pq_create(arena);
    if (!state->open_set) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Create closed set
    state->closed_set = vertex_set_create(arena);
    if (!state->closed_set) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Allocate node table
    state->node_capacity = NODE_HASH_SIZE;
    state->nodes = gs_arena_calloc_array(arena, DijkstraNode, state->node_capacity);
    if (!state->nodes) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    return GS_SUCCESS;
}

// Reconstruct path from goal to start
static GraphserverResult reconstruct_path(
    DijkstraState* state,
    const GraphserverVertex* goal_vertex,
    GraphserverPath** out_path) {
    
    if (!state || !goal_vertex || !out_path) {
        return GS_ERROR_NULL_POINTER;
    }
    
    // Find goal node
    DijkstraNode* goal_node = find_dijkstra_node(state, goal_vertex);
    if (!goal_node) {
        return GS_ERROR_NO_PATH_FOUND;
    }
    
    // Count path length by following parent chain
    size_t path_length = 0;
    DijkstraNode* current = goal_node;
    while (current->parent) {
        path_length++;
        current = find_dijkstra_node(state, current->parent);
        if (!current) {
            return GS_ERROR_NO_PATH_FOUND; // Broken parent chain
        }
    }
    
    if (path_length == 0) {
        // Start is goal, create empty path
        GraphserverPath* path = gs_path_create(1);
        if (!path) return GS_ERROR_OUT_OF_MEMORY;
        *out_path = path;
        return GS_SUCCESS;
    }
    
    // Create path with correct size
    GraphserverPath* path = gs_path_create(1);
    if (!path) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Allocate edges array
    path->edges = malloc(sizeof(GraphserverEdge*) * path_length);
    if (!path->edges) {
        gs_path_destroy(path);
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Build path by following parent chain backwards
    current = goal_node;
    for (int i = path_length - 1; i >= 0; i--) {
        DijkstraNode* parent_node = find_dijkstra_node(state, current->parent);
        if (!parent_node) {
            gs_path_destroy(path);
            return GS_ERROR_NO_PATH_FOUND;
        }
        
        // Create edge from parent to current
        double edge_cost = current->cost - parent_node->cost;
        
        // Clone the vertex to ensure data persistence after cleanup
        GraphserverVertex* target_vertex_copy = gs_vertex_clone(current->vertex);
        if (!target_vertex_copy) {
            gs_path_destroy(path);
            return GS_ERROR_OUT_OF_MEMORY;
        }
        
        GraphserverEdge* edge = gs_edge_create(target_vertex_copy, &edge_cost, 1);
        if (!edge) {
            gs_vertex_destroy(target_vertex_copy);
            gs_path_destroy(path);
            return GS_ERROR_OUT_OF_MEMORY;
        }
        
        // Set the edge to own the cloned vertex so it persists after path creation
        gs_edge_set_owns_target_vertex(edge, true);
        
        path->edges[i] = edge;
        current = parent_node;
    }
    
    path->num_edges = path_length;
    
    // Set total cost
    if (path->total_cost) {
        path->total_cost[0] = goal_node->cost;
    }
    
    *out_path = path;
    return GS_SUCCESS;
}

// Run Dijkstra search
GraphserverResult dijkstra_search(
    DijkstraState* state,
    GraphserverEngine* engine,
    GraphserverPath** out_path) {
    
    if (!state || !engine || !out_path) {
        return GS_ERROR_NULL_POINTER;
    }
    
    double start_time = get_current_time_seconds();
    *out_path = NULL;
    
    // Create start vertex copy for internal use
    GraphserverVertex* start_copy = gs_vertex_clone(state->start_vertex);
    if (!start_copy) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Initialize start node
    DijkstraNode* start_node = get_or_create_dijkstra_node(state, start_copy);
    if (!start_node) {
        gs_vertex_destroy(start_copy);
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    start_node->cost = 0.0;
    start_node->parent = NULL;
    
    // Add start to open set
    if (!pq_insert(state->open_set, start_copy, 0.0)) {
        gs_vertex_destroy(start_copy);
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    GraphserverResult result = GS_ERROR_NO_PATH_FOUND;
    
    // Main search loop
    while (!pq_is_empty(state->open_set)) {
        // Check timeout
        double current_time = get_current_time_seconds();
        if (state->timeout_seconds > 0 && 
            (current_time - start_time) > state->timeout_seconds) {
            state->timeout_reached = true;
            result = GS_ERROR_TIMEOUT;
            break;
        }
        
        // Extract minimum cost vertex
        GraphserverVertex* current_vertex;
        double current_cost;
        if (!pq_extract_min(state->open_set, &current_vertex, &current_cost)) {
            break; // Should not happen
        }
        
        state->vertices_expanded++;
        
        // Add to closed set
        vertex_set_add(state->closed_set, current_vertex);
        
        // Check if goal
        if (state->is_goal(current_vertex, state->goal_user_data)) {
            state->goal_found = true;
            result = reconstruct_path(state, current_vertex, out_path);
            break;
        }
        
        // Expand current vertex
        GraphserverEdgeList* edges = gs_edge_list_create();
        if (!edges) {
            result = GS_ERROR_OUT_OF_MEMORY;
            break;
        }
        
        // Set edge list to own its edges since providers create transient edges
        gs_edge_list_set_owns_edges(edges, true);
        
        GraphserverResult expand_result = gs_engine_expand_vertex(engine, current_vertex, edges);
        if (expand_result != GS_SUCCESS) {
            gs_edge_list_destroy(edges);
            continue; // Skip this vertex
        }
        
        // Process each edge
        size_t edge_count = gs_edge_list_get_count(edges);
        for (size_t i = 0; i < edge_count; i++) {
            GraphserverEdge* edge;
            if (gs_edge_list_get_edge(edges, i, &edge) != GS_SUCCESS || !edge) {
                continue;
            }
            
            state->edges_examined++;
            
            const GraphserverVertex* target = gs_edge_get_target_vertex(edge);
            if (!target) continue;
            
            // Skip if in closed set
            if (vertex_set_contains(state->closed_set, target)) {
                continue;
            }
            
            // Calculate new cost
            const double* edge_distance = gs_edge_get_distance_vector(edge);
            if (!edge_distance) continue;
            
            double new_cost = current_cost + edge_distance[0];
            
            // Create target copy for our node table
            GraphserverVertex* target_copy = gs_vertex_clone(target);
            if (!target_copy) continue;
            
            // Get or create target node
            DijkstraNode* target_node = get_or_create_dijkstra_node(state, target_copy);
            if (!target_node) {
                gs_vertex_destroy(target_copy);
                continue;
            }
            
            // Update if better path found
            if (new_cost < target_node->cost) {
                target_node->cost = new_cost;
                target_node->parent = current_vertex;
                
                // Update priority queue
                if (pq_contains(state->open_set, target_copy)) {
                    pq_decrease_key(state->open_set, target_copy, new_cost);
                } else {
                    pq_insert(state->open_set, target_copy, new_cost);
                    state->nodes_generated++;
                }
            } else {
                // Destroy copy if not used
                gs_vertex_destroy(target_copy);
            }
        }
        
        gs_edge_list_destroy(edges);
    }
    
    // Record search time
    state->search_time_seconds = get_current_time_seconds() - start_time;
    
    return result;
}

// Clean up Dijkstra search state
void dijkstra_cleanup(DijkstraState* state) {
    if (!state) return;
    
    // Clean up cloned vertices in the node table
    if (state->nodes) {
        for (size_t i = 0; i < state->node_capacity; i++) {
            DijkstraNode* node = &state->nodes[i];
            if (node->vertex) {
                gs_vertex_destroy(node->vertex);
            }
        }
    }
    
    // Priority queue and vertex set will be cleaned up with arena
    // No explicit cleanup needed for arena-allocated memory
    
    // Clear state
    memset(state, 0, sizeof(DijkstraState));
}

// Public function to run Dijkstra planning
GraphserverResult gs_plan_dijkstra(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    double timeout_seconds,
    GraphserverArena* arena,
    GraphserverPath** out_path,
    GraphserverPlanStats* out_stats) {
    
    if (!engine || !start_vertex || !is_goal || !arena || !out_path) {
        return GS_ERROR_NULL_POINTER;
    }
    
    DijkstraState state;
    GraphserverResult init_result = dijkstra_init(
        &state, start_vertex, is_goal, goal_user_data, arena, timeout_seconds);
    
    if (init_result != GS_SUCCESS) {
        return init_result;
    }
    
    GraphserverResult search_result = dijkstra_search(&state, engine, out_path);
    
    // Populate statistics
    if (out_stats) {
        memset(out_stats, 0, sizeof(GraphserverPlanStats));
        out_stats->vertices_expanded = state.vertices_expanded;
        out_stats->edges_generated = state.edges_examined;
        out_stats->planning_time_seconds = state.search_time_seconds;
        out_stats->peak_memory_usage = gs_arena_get_usage(arena);
        out_stats->path_length = (*out_path) ? (*out_path)->num_edges : 0;
    }
    
    dijkstra_cleanup(&state);
    
    return search_result;
}