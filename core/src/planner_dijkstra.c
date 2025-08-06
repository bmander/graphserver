#include "../include/gs_planner_internal.h"
#include "../include/gs_engine.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"
#include "../include/gs_memory.h"
#include "../include/gs_hashmap.h"
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <assert.h>
#include <stdio.h>

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

// External vertex hash and equality functions (defined in hashmap.c)
extern size_t vertex_hash(const void* vertex_ptr);
extern bool vertex_equals(const void* a, const void* b);

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

// Find or create Dijkstra node for vertex
static DijkstraNode* get_or_create_dijkstra_node(DijkstraState* state, GraphserverVertex* vertex) {
    // Check if node already exists
    DijkstraNode* existing_node = (DijkstraNode*)hashmap_get(state->node_map, vertex);
    if (existing_node) {
        return existing_node;
    }
    
    // Create new node
    DijkstraNode* node;
    if (state->arena) {
        node = gs_arena_alloc_type(state->arena, DijkstraNode);
    } else {
        node = malloc(sizeof(DijkstraNode));
    }
    
    if (!node) {
        return NULL;
    }
    
    // Initialize node
    node->vertex = vertex;
    node->parent = NULL;
    node->cost = INFINITY;
    node->incoming_edge = NULL;
    node->next = NULL;
    
    // Add to hash map
    if (!hashmap_put(state->node_map, vertex, node)) {
        // Failed to add to map, free node
        if (!state->arena) {
            free(node);
        }
        return NULL;
    }
    
    return node;
}

// Find Dijkstra node for vertex
static DijkstraNode* find_dijkstra_node(DijkstraState* state, const GraphserverVertex* vertex) {
    return (DijkstraNode*)hashmap_get(state->node_map, vertex);
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
    
    // Create closed set (hashmap for vertices)
    state->closed_set = hashmap_create(vertex_hash, vertex_equals, arena);
    if (!state->closed_set) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    // Create node map (vertex -> DijkstraNode*)
    state->node_map = hashmap_create(vertex_hash, vertex_equals, arena);
    if (!state->node_map) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    return GS_SUCCESS;
}

// Helper to count edges in the path by following parent pointers
static GraphserverResult count_path_length(
    DijkstraState* state,
    DijkstraNode* goal_node,
    size_t* out_length) {

    if (!state || !goal_node || !out_length) {
        return GS_ERROR_NULL_POINTER;
    }

    size_t length = 0;
    DijkstraNode* current = goal_node;
    while (current->parent) {
        length++;
        current = find_dijkstra_node(state, current->parent);
        if (!current) {
            return GS_ERROR_NO_PATH_FOUND; // Broken parent chain
        }
    }

    *out_length = length;
    return GS_SUCCESS;
}

// Helper to build path edges and clone vertices
static GraphserverResult build_path_edges(
    DijkstraState* state,
    DijkstraNode* goal_node,
    size_t path_length,
    GraphserverEdge*** out_edges) {

    if (!state || !goal_node || !out_edges) {
        return GS_ERROR_NULL_POINTER;
    }

    GraphserverEdge** edges = malloc(sizeof(GraphserverEdge*) * path_length);
    if (!edges) {
        return GS_ERROR_OUT_OF_MEMORY;
    }

    // Initialize to NULL for safe cleanup on failure
    for (size_t i = 0; i < path_length; i++) {
        edges[i] = NULL;
    }

    DijkstraNode* current = goal_node;
    for (int i = (int)path_length - 1; i >= 0; i--) {
        DijkstraNode* parent_node = find_dijkstra_node(state, current->parent);
        if (!parent_node) {
            // Cleanup any previously created edges
            for (size_t j = 0; j < path_length; j++) {
                if (edges[j]) gs_edge_destroy(edges[j]);
            }
            free(edges);
            return GS_ERROR_NO_PATH_FOUND;
        }

        // Use the original edge if available, otherwise create a simple cost-only edge
        GraphserverEdge* edge;
        if (current->incoming_edge) {
            // Clone the original edge to preserve metadata
            edge = gs_edge_clone(current->incoming_edge);
            if (!edge) {
                for (size_t j = 0; j < path_length; j++) {
                    if (edges[j]) gs_edge_destroy(edges[j]);
                }
                free(edges);
                return GS_ERROR_OUT_OF_MEMORY;
            }
        } else {
            // Fallback: create simple edge with cost only (for start node or missing edges)
            double edge_cost = current->cost - parent_node->cost;
            GraphserverVertex* target_vertex_copy = gs_vertex_clone(current->vertex);
            if (!target_vertex_copy) {
                for (size_t j = 0; j < path_length; j++) {
                    if (edges[j]) gs_edge_destroy(edges[j]);
                }
                free(edges);
                return GS_ERROR_OUT_OF_MEMORY;
            }

            edge = gs_edge_create(target_vertex_copy, &edge_cost, 1);
            if (!edge) {
                gs_vertex_destroy(target_vertex_copy);
                for (size_t j = 0; j < path_length; j++) {
                    if (edges[j]) gs_edge_destroy(edges[j]);
                }
                free(edges);
                return GS_ERROR_OUT_OF_MEMORY;
            }
            gs_edge_set_owns_target_vertex(edge, true);
        }
        edges[i] = edge;
        current = parent_node;
    }

    *out_edges = edges;
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

    size_t path_length = 0;
    GraphserverResult result = count_path_length(state, goal_node, &path_length);
    if (result != GS_SUCCESS) {
        return result;
    }

    GraphserverPath* path = gs_path_create(1);
    if (!path) {
        return GS_ERROR_OUT_OF_MEMORY;
    }

    if (path_length > 0) {
        GraphserverEdge** edges = NULL;
        result = build_path_edges(state, goal_node, path_length, &edges);
        if (result != GS_SUCCESS) {
            gs_path_destroy(path);
            return result;
        }
        path->edges = edges;
    }

    path->num_edges = path_length;
    if (path->total_cost) {
        path->total_cost[0] = goal_node->cost;
    }

    *out_path = path;
    return GS_SUCCESS;
}

// Relax all outgoing edges of the given vertex and update the open set
static GraphserverResult relax_edges(
    DijkstraState* state,
    GraphserverEngine* engine,
    GraphserverVertex* current_vertex,
    double current_cost) {

    GraphserverEdgeList* edges = gs_edge_list_create();
    if (!edges) {
        return GS_ERROR_OUT_OF_MEMORY;
    }

    // Providers create transient edges, so let the list own them
    gs_edge_list_set_owns_edges(edges, true);

    GraphserverResult expand_result =
        gs_engine_expand_vertex(engine, current_vertex, edges);
    if (expand_result != GS_SUCCESS) {
        gs_edge_list_destroy(edges);
        return GS_SUCCESS; // Skip this vertex on failure
    }

    size_t edge_count = gs_edge_list_get_count(edges);
    
    for (size_t i = 0; i < edge_count; i++) {
        GraphserverEdge* edge;
        if (gs_edge_list_get_edge(edges, i, &edge) != GS_SUCCESS || !edge) {
            continue;
        }

        state->edges_examined++;

        const GraphserverVertex* target = gs_edge_get_target_vertex(edge);
        if (!target) {
            continue;
        }

        // Skip if in closed set
        if (hashmap_contains(state->closed_set, target)) {
            continue;
        }

        const double* edge_distance = gs_edge_get_distance_vector(edge);
        if (!edge_distance) {
            continue;
        }

        double new_cost = current_cost + edge_distance[0];

        GraphserverVertex* target_copy = gs_vertex_clone(target);
        if (!target_copy) {
            continue;
        }

        DijkstraNode* target_node =
            get_or_create_dijkstra_node(state, target_copy);
        if (!target_node) {
            gs_vertex_destroy(target_copy);
            continue;
        }

        if (new_cost < target_node->cost) {
            target_node->cost = new_cost;
            target_node->parent = current_vertex;
            
            // Clone the edge to preserve it beyond the edge list's lifetime
            target_node->incoming_edge = gs_edge_clone(edge);
            if (!target_node->incoming_edge) {
                target_node->incoming_edge = NULL;
            }

            if (pq_contains(state->open_set, target_copy)) {
                pq_decrease_key(state->open_set, target_copy, new_cost);
            } else {
                pq_insert(state->open_set, target_copy, new_cost);
                state->nodes_generated++;
            }
        } else {
            gs_vertex_destroy(target_copy);
        }
    }

    gs_edge_list_destroy(edges);
    return GS_SUCCESS;
}

// Process the current vertex: add to closed set, check goal and relax edges
static GraphserverResult process_current_vertex(
    DijkstraState* state,
    GraphserverEngine* engine,
    GraphserverVertex* current_vertex,
    double current_cost,
    GraphserverPath** out_path) {

    hashmap_put(state->closed_set, current_vertex, current_vertex); // Value doesn't matter for set

    if (state->is_goal(current_vertex, state->goal_user_data)) {
        state->goal_found = true;
        return reconstruct_path(state, current_vertex, out_path);
    }

    return relax_edges(state, engine, current_vertex, current_cost);
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

        GraphserverResult proc_result = process_current_vertex(
            state, engine, current_vertex, current_cost, out_path);

        if (state->goal_found || proc_result != GS_SUCCESS) {
            result = proc_result;
            break;
        }
    }
    
    // Record search time
    state->search_time_seconds = get_current_time_seconds() - start_time;
    
    return result;
}

// Clean up Dijkstra search state
void dijkstra_cleanup(DijkstraState* state) {
    if (!state) return;
    
    // Clean up nodes stored in the node map
    if (state->node_map) {
        HashMapIterator iter = hashmap_iterator_create(state->node_map);
        void* key;
        void* value;
        
        while (hashmap_iterator_next(&iter, &key, &value)) {
            GraphserverVertex* vertex = (GraphserverVertex*)key;
            DijkstraNode* node = (DijkstraNode*)value;
            
            if (vertex) {
                gs_vertex_destroy(vertex);
            }
            if (node && node->incoming_edge) {
                gs_edge_destroy(node->incoming_edge);
            }
            // Don't free the node itself if using arena allocation
            if (!state->arena && node) {
                free(node);
            }
        }
    }
    
    // Hash maps and priority queue will be cleaned up with arena
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