#include "../include/gs_planner_internal.h"
#include "../include/gs_engine.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"
#include "../include/gs_memory.h"
#include "../include/gs_hashmap.h"
#include "../include/gs_common_keys.h"
#include "../../examples/include/example_providers.h"
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <assert.h>
#include <stdio.h>

/**
 * @file planner_astar.c
 * @brief A* algorithm implementation for informed pathfinding
 * 
 * This implementation provides A* search with geographic distance heuristics
 * for significantly improved performance over Dijkstra's algorithm for
 * long-distance routing scenarios.
 */

// Forward declare the internal path structure
struct GraphserverPath {
    GraphserverEdge** edges;
    size_t num_edges;
    double* total_cost;
    size_t cost_vector_size;
};

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

// Find or create A* node for vertex
static AStarNode* get_or_create_astar_node(AStarState* state, GraphserverVertex* vertex, bool* created_new_node) {
    // Check if node already exists
    AStarNode* existing_node = (AStarNode*)hashmap_get(state->node_map, vertex);
    if (existing_node) {
        if (created_new_node) *created_new_node = false;
        return existing_node;
    }
    
    // Create new node
    AStarNode* node;
    if (state->arena) {
        node = gs_arena_alloc_type(state->arena, AStarNode);
    } else {
        node = malloc(sizeof(AStarNode));
    }
    
    if (!node) {
        return NULL;
    }
    
    // Initialize node
    node->vertex = vertex;
    node->parent = NULL;
    node->g_cost = INFINITY;
    node->f_cost = INFINITY;
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
    
    if (created_new_node) *created_new_node = true;
    return node;
}

// Find A* node for vertex
static AStarNode* find_astar_node(AStarState* state, const GraphserverVertex* vertex) {
    return (AStarNode*)hashmap_get(state->node_map, vertex);
}

// Initialize A* search state
GraphserverResult astar_init(
    AStarState* state,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    gs_astar_heuristic_fn heuristic,
    void* heuristic_data,
    GraphserverArena* arena,
    double timeout_seconds) {
    
    if (!state || !start_vertex || !is_goal || !heuristic || !arena) {
        return GS_ERROR_NULL_POINTER;
    }
    
    // Initialize state
    memset(state, 0, sizeof(AStarState));
    state->arena = arena;
    state->start_vertex = start_vertex;
    state->is_goal = is_goal;
    state->goal_user_data = goal_user_data;
    state->heuristic = heuristic;
    state->heuristic_data = heuristic_data;
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
    
    // Create node map (vertex -> AStarNode*)
    state->node_map = hashmap_create(vertex_hash, vertex_equals, arena);
    if (!state->node_map) {
        return GS_ERROR_OUT_OF_MEMORY;
    }
    
    return GS_SUCCESS;
}

// Helper to count edges in the path by following parent pointers
static GraphserverResult count_path_length(
    AStarState* state,
    AStarNode* goal_node,
    size_t* out_length) {

    if (!state || !goal_node || !out_length) {
        return GS_ERROR_NULL_POINTER;
    }

    size_t length = 0;
    AStarNode* current = goal_node;
    while (current->parent) {
        length++;
        current = find_astar_node(state, current->parent);
        if (!current) {
            return GS_ERROR_NO_PATH_FOUND; // Broken parent chain
        }
    }

    *out_length = length;
    return GS_SUCCESS;
}

// Helper to build path edges and clone vertices
static GraphserverResult build_path_edges(
    AStarState* state,
    AStarNode* goal_node,
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

    AStarNode* current = goal_node;
    for (int i = (int)path_length - 1; i >= 0; i--) {
        AStarNode* parent_node = find_astar_node(state, current->parent);
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
            double edge_cost = current->g_cost - parent_node->g_cost;
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
    AStarState* state,
    const GraphserverVertex* goal_vertex,
    GraphserverPath** out_path) {

    if (!state || !goal_vertex || !out_path) {
        return GS_ERROR_NULL_POINTER;
    }

    // Find goal node
    AStarNode* goal_node = find_astar_node(state, goal_vertex);
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
        path->total_cost[0] = goal_node->g_cost;
    }

    *out_path = path;
    return GS_SUCCESS;
}

// Relax all outgoing edges of the given vertex and update the open set
static GraphserverResult relax_edges(
    AStarState* state,
    GraphserverEngine* engine,
    GraphserverVertex* current_vertex,
    double current_g_cost) {

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
        return expand_result;
    }

    state->edges_examined += gs_edge_list_get_count(edges);

    size_t edge_count = gs_edge_list_get_count(edges);
    
    // Process each outgoing edge
    for (size_t i = 0; i < edge_count; i++) {
        GraphserverEdge* edge;
        if (gs_edge_list_get_edge(edges, i, &edge) != GS_SUCCESS || !edge) {
            continue;
        }
        
        const GraphserverVertex* target = gs_edge_get_target_vertex(edge);
        if (!target) {
            continue;
        }
        
        // Calculate tentative g cost
        const double* edge_distance = gs_edge_get_distance_vector(edge);
        if (!edge_distance) {
            continue;
        }
        double tentative_g_cost = current_g_cost + edge_distance[0];
        
        // Skip if we've already processed this vertex optimally
        if (hashmap_contains(state->closed_set, target)) {
            continue;
        }
        
        // Clone the target vertex since we need a mutable copy
        GraphserverVertex* neighbor_vertex = gs_vertex_clone(target);
        if (!neighbor_vertex) {
            gs_edge_list_destroy(edges);
            return GS_ERROR_OUT_OF_MEMORY;
        }
        
        // Find or create neighbor node
        bool created_new_node = false;
        AStarNode* neighbor_node = get_or_create_astar_node(state, neighbor_vertex, &created_new_node);
        if (!neighbor_node) {
            gs_edge_list_destroy(edges);
            return GS_ERROR_OUT_OF_MEMORY;
        }
        
        if (created_new_node) {
            state->nodes_generated++;
        }
        
        // Update if we found a better path
        if (tentative_g_cost < neighbor_node->g_cost) {
            neighbor_node->parent = current_vertex;
            neighbor_node->g_cost = tentative_g_cost;
            neighbor_node->incoming_edge = edge;
            
            // Calculate f_cost using heuristic
            double h_cost = state->heuristic(neighbor_vertex, state->heuristic_data);
            neighbor_node->f_cost = tentative_g_cost + h_cost;
            
            // Add to open set or update priority
            if (!pq_contains(state->open_set, neighbor_vertex)) {
                if (!pq_insert(state->open_set, neighbor_vertex, neighbor_node->f_cost)) {
                    gs_edge_list_destroy(edges);
                    return GS_ERROR_OUT_OF_MEMORY;
                }
            } else {
                // Update priority in open set
                pq_decrease_key(state->open_set, neighbor_vertex, neighbor_node->f_cost);
            }
        }
    }

    gs_edge_list_destroy(edges);
    return GS_SUCCESS;
}

// Run A* search
GraphserverResult astar_search(
    AStarState* state,
    GraphserverEngine* engine,
    GraphserverPath** out_path) {

    if (!state || !engine || !out_path) {
        return GS_ERROR_NULL_POINTER;
    }

    // Record search start time
    double search_start_time = get_current_time_seconds();

    // Initialize start node
    GraphserverVertex* start_vertex_copy = gs_vertex_clone(state->start_vertex);
    if (!start_vertex_copy) {
        return GS_ERROR_OUT_OF_MEMORY;
    }

    bool created_new_node = false;
    AStarNode* start_node = get_or_create_astar_node(state, start_vertex_copy, &created_new_node);
    if (!start_node) {
        gs_vertex_destroy(start_vertex_copy);
        return GS_ERROR_OUT_OF_MEMORY;
    }

    if (created_new_node) {
        state->nodes_generated++;
    }

    start_node->g_cost = 0.0;
    start_node->f_cost = state->heuristic(start_vertex_copy, state->heuristic_data);

    // Add start vertex to open set
    if (!pq_insert(state->open_set, start_vertex_copy, start_node->f_cost)) {
        return GS_ERROR_OUT_OF_MEMORY;
    }

    // Main search loop
    while (!pq_is_empty(state->open_set)) {
        // Check timeout
        if (state->timeout_seconds > 0) {
            double elapsed = get_current_time_seconds() - search_start_time;
            if (elapsed > state->timeout_seconds) {
                state->timeout_reached = true;
                state->search_time_seconds = elapsed;
                return GS_ERROR_TIMEOUT;
            }
        }

        // Extract minimum f-cost vertex
        GraphserverVertex* current_vertex;
        double current_f_cost;
        if (!pq_extract_min(state->open_set, &current_vertex, &current_f_cost)) {
            break; // Open set is empty
        }

        // Add to closed set
        hashmap_put(state->closed_set, current_vertex, (void*)1);
        state->vertices_expanded++;

        // Check if goal is reached
        if (state->is_goal(current_vertex, state->goal_user_data)) {
            state->goal_found = true;
            state->search_time_seconds = get_current_time_seconds() - search_start_time;
            return reconstruct_path(state, current_vertex, out_path);
        }

        // Get current node's g_cost
        AStarNode* current_node = find_astar_node(state, current_vertex);
        if (!current_node) {
            continue; // Should not happen
        }

        // Expand current vertex
        GraphserverResult relax_result = relax_edges(
            state, engine, current_vertex, current_node->g_cost);
        if (relax_result != GS_SUCCESS) {
            return relax_result;
        }
    }

    // No path found
    state->search_time_seconds = get_current_time_seconds() - search_start_time;
    return GS_ERROR_NO_PATH_FOUND;
}

// Clean up A* search state
void astar_cleanup(AStarState* state) {
    if (!state) return;
    
    // Priority queue, hashmaps, and arena memory will be freed by arena
    // or have their own cleanup methods if not using arena
    memset(state, 0, sizeof(AStarState));
}

// Geographic distance heuristic for routing with lat/lng coordinates
double geographic_distance_heuristic(const GraphserverVertex* vertex, void* goal_data) {
    if (!vertex || !goal_data) {
        return 0.0;
    }
    
    LocationGoal* goal = (LocationGoal*)goal_data;
    
    // Get vertex coordinates using proper key lookups
    GraphserverValue lat_value, lng_value;
    GraphserverResult lat_result = gs_vertex_get_value(vertex, GS_KEY_LAT, &lat_value);
    GraphserverResult lng_result = gs_vertex_get_value(vertex, GS_KEY_LON, &lng_value);
    
    if (lat_result != GS_SUCCESS || lng_result != GS_SUCCESS) {
        return 0.0; // No coordinates available
    }
    
    if (lat_value.type != GS_VALUE_FLOAT || lng_value.type != GS_VALUE_FLOAT) {
        return 0.0; // Wrong value types
    }
    
    double vertex_lat = lat_value.as.f_val;
    double vertex_lng = lng_value.as.f_val;
    
    // Calculate haversine distance
    double lat_diff = (goal->target_lat - vertex_lat) * M_PI / 180.0;
    double lng_diff = (goal->target_lon - vertex_lng) * M_PI / 180.0;
    double vertex_lat_rad = vertex_lat * M_PI / 180.0;
    double goal_lat_rad = goal->target_lat * M_PI / 180.0;
    
    double a = sin(lat_diff / 2) * sin(lat_diff / 2) +
               cos(vertex_lat_rad) * cos(goal_lat_rad) *
               sin(lng_diff / 2) * sin(lng_diff / 2);
    double c = 2 * atan2(sqrt(a), sqrt(1 - a));
    double distance_km = 6371.0 * c; // Earth's radius
    
    // Convert to travel time estimate in minutes
    // Assume average speed of 4 km/h for walking, 15 km/h for mixed transport
    double speed_kmh = 5.0; // Conservative estimate for admissible heuristic
    return (distance_km / speed_kmh) * 60.0; // Convert hours to minutes
}

// Run A* planning algorithm
GraphserverResult gs_plan_astar(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    gs_astar_heuristic_fn heuristic,
    void* heuristic_data,
    double timeout_seconds,
    GraphserverArena* arena,
    GraphserverPath** out_path,
    GraphserverPlanStats* out_stats) {

    if (!engine || !start_vertex || !is_goal || !heuristic || !out_path) {
        return GS_ERROR_NULL_POINTER;
    }

    // Create local arena if none provided
    GraphserverArena* local_arena = arena;
    if (!local_arena) {
        local_arena = gs_arena_create(1024 * 1024); // 1MB arena
        if (!local_arena) {
            return GS_ERROR_OUT_OF_MEMORY;
        }
    }

    AStarState state;
    GraphserverResult init_result = astar_init(
        &state, start_vertex, is_goal, goal_user_data,
        heuristic, heuristic_data, local_arena, timeout_seconds);
    
    if (init_result != GS_SUCCESS) {
        if (!arena) gs_arena_destroy(local_arena);
        return init_result;
    }

    GraphserverResult search_result = astar_search(&state, engine, out_path);

    // Populate statistics if requested
    if (out_stats) {
        out_stats->vertices_expanded = state.vertices_expanded;
        out_stats->edges_generated = state.edges_examined;
        out_stats->planning_time_seconds = state.search_time_seconds;
        out_stats->peak_memory_usage = local_arena ? gs_arena_get_usage(local_arena) : 0;
    }

    astar_cleanup(&state);

    // Clean up local arena if we created it
    if (!arena) {
        gs_arena_destroy(local_arena);
    }

    return search_result;
}