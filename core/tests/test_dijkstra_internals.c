#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include "../include/graphserver.h"
#include "../include/gs_planner_internal.h"

// Simple test framework
static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void test_##name(void); \
    static void run_test_##name(void) { \
        printf("Running test: %s... ", #name); \
        tests_run++; \
        test_##name(); \
        tests_passed++; \
        printf("PASSED\n"); \
    } \
    static void test_##name(void)

#define ASSERT(condition) \
    do { \
        if (!(condition)) { \
            printf("FAILED\n  Assertion failed: %s (line %d)\n", #condition, __LINE__); \
            exit(1); \
        } \
    } while(0)

#define ASSERT_EQ(expected, actual) \
    do { \
        if ((expected) != (actual)) { \
            printf("FAILED\n  Expected %ld, got %ld (line %d)\n", (long)(expected), (long)(actual), __LINE__); \
            exit(1); \
        } \
    } while(0)

#define ASSERT_DOUBLE_EQ(expected, actual, epsilon) \
    do { \
        if (fabs((expected) - (actual)) > (epsilon)) { \
            printf("FAILED\n  Expected %f, got %f (line %d)\n", (expected), (actual), __LINE__); \
            exit(1); \
        } \
    } while(0)

#define ASSERT_NULL(ptr) \
    do { \
        if ((ptr) != NULL) { \
            printf("FAILED\n  Expected NULL, got %p (line %d)\n", (ptr), __LINE__); \
            exit(1); \
        } \
    } while(0)

#define ASSERT_NOT_NULL(ptr) \
    do { \
        if ((ptr) == NULL) { \
            printf("FAILED\n  Expected non-NULL pointer (line %d)\n", __LINE__); \
            exit(1); \
        } \
    } while(0)

// Helper function to create a test vertex with x,y coordinates
static GraphserverVertex* create_coordinate_vertex(int x, int y) {
    GraphserverKeyPair pairs[] = {
        {"x", gs_value_create_int(x)},
        {"y", gs_value_create_int(y)}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 2, NULL);
    return vertex;
}

// Simple goal predicate for coordinate targets
typedef struct {
    int target_x;
    int target_y;
} CoordinateGoal;

static bool coordinate_goal_predicate(const GraphserverVertex* vertex, void* user_data) {
    CoordinateGoal* goal = (CoordinateGoal*)user_data;
    
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(vertex, "x", &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(vertex, "y", &y_val) != GS_SUCCESS) {
        return false;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    return (x == goal->target_x && y == goal->target_y);
}

// Test Dijkstra state initialization
TEST(dijkstra_state_initialization) {
    GraphserverArena* arena = gs_arena_create(4096);
    ASSERT_NOT_NULL(arena);
    
    DijkstraState state;
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {5, 5};
    
    // Test successful initialization
    GraphserverResult result = dijkstra_init(
        &state, start, coordinate_goal_predicate, &goal, arena, 10.0);
    
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(state.open_set);
    ASSERT_NOT_NULL(state.closed_set);
    ASSERT_NOT_NULL(state.node_map);
    ASSERT_EQ(arena, state.arena);
    ASSERT_EQ(start, state.start_vertex);
    ASSERT_EQ(coordinate_goal_predicate, state.is_goal);
    ASSERT_EQ(&goal, state.goal_user_data);
    ASSERT_DOUBLE_EQ(10.0, state.timeout_seconds, 1e-6);
    
    // Verify initial statistics
    ASSERT_EQ(0, state.vertices_expanded);
    ASSERT_EQ(0, state.edges_examined);
    ASSERT_EQ(0, state.nodes_generated);
    ASSERT(!state.timeout_reached);
    ASSERT(!state.goal_found);
    
    dijkstra_cleanup(&state);
    gs_vertex_destroy(start);
    gs_arena_destroy(arena);
}

// Test Dijkstra state initialization with NULL parameters
TEST(dijkstra_state_null_parameters) {
    GraphserverArena* arena = gs_arena_create(4096);
    DijkstraState state;
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {5, 5};
    
    // Test NULL state
    ASSERT_EQ(GS_ERROR_NULL_POINTER, 
              dijkstra_init(NULL, start, coordinate_goal_predicate, &goal, arena, 10.0));
    
    // Test NULL start vertex
    ASSERT_EQ(GS_ERROR_NULL_POINTER,
              dijkstra_init(&state, NULL, coordinate_goal_predicate, &goal, arena, 10.0));
    
    // Test NULL goal predicate
    ASSERT_EQ(GS_ERROR_NULL_POINTER,
              dijkstra_init(&state, start, NULL, &goal, arena, 10.0));
    
    // Test NULL arena
    ASSERT_EQ(GS_ERROR_NULL_POINTER,
              dijkstra_init(&state, start, coordinate_goal_predicate, &goal, NULL, 10.0));
    
    gs_vertex_destroy(start);
    gs_arena_destroy(arena);
}

// Simple grid provider for testing
static int simple_grid_provider(const GraphserverVertex* current_vertex,
                               GraphserverEdgeList* out_edges,
                               void* user_data) {
    (void)user_data; // Unused
    
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(current_vertex, "x", &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(current_vertex, "y", &y_val) != GS_SUCCESS) {
        return -1;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    // Add edges to 4-connected neighbors
    int dx[] = {-1, 1, 0, 0};
    int dy[] = {0, 0, -1, 1};
    
    for (int i = 0; i < 4; i++) {
        int nx = x + dx[i];
        int ny = y + dy[i];
        
        // Stay within bounds
        if (nx < 0 || nx > 10 || ny < 0 || ny > 10) continue;
        
        GraphserverVertex* neighbor = create_coordinate_vertex(nx, ny);
        if (!neighbor) continue;
        
        double distance = 1.0;
        GraphserverEdge* edge = gs_edge_create(neighbor, &distance, 1);
        if (!edge) {
            gs_vertex_destroy(neighbor);
            continue;
        }
        
        gs_edge_set_owns_target_vertex(edge, true);
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    return 0;
}

// Test basic path reconstruction functionality
TEST(dijkstra_path_reconstruction_basic) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "grid", simple_grid_provider, NULL);
    
    // Create a simple 3-step path: (0,0) -> (1,0) -> (2,0) -> (3,0)
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {3, 0};
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(3, gs_path_get_num_edges(path)); // 3 edges for 4 vertices
    
    // Verify path cost
    const double* total_cost = gs_path_get_total_cost(path);
    ASSERT_NOT_NULL(total_cost);
    ASSERT_DOUBLE_EQ(3.0, total_cost[0], 1e-6);
    
    // Verify path structure - each edge should connect to the next coordinate
    for (size_t i = 0; i < gs_path_get_num_edges(path); i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        ASSERT_NOT_NULL(edge);
        
        const GraphserverVertex* target = gs_edge_get_target_vertex(edge);
        ASSERT_NOT_NULL(target);
        
        GraphserverValue x_val;
        ASSERT_EQ(GS_SUCCESS, gs_vertex_get_value(target, "x", &x_val));
        ASSERT_EQ((int)(i + 1), (int)x_val.as.i_val); // Should be x = i+1
    }
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Zero cost edge provider for testing
static int zero_cost_provider(const GraphserverVertex* current_vertex,
                             GraphserverEdgeList* out_edges,
                             void* user_data) {
    (void)user_data;
    
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(current_vertex, "x", &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(current_vertex, "y", &y_val) != GS_SUCCESS) {
        return -1;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    // Create edges with zero cost to test algorithm behavior
    int dx[] = {1, 0}; // Only right and up
    int dy[] = {0, 1};
    
    for (int i = 0; i < 2; i++) {
        int nx = x + dx[i];
        int ny = y + dy[i];
        
        if (nx > 5 || ny > 5) continue; // Stay in bounds
        
        GraphserverVertex* neighbor = create_coordinate_vertex(nx, ny);
        if (!neighbor) continue;
        
        // Use zero cost for all edges
        double cost = 0.0;
        GraphserverEdge* edge = gs_edge_create(neighbor, &cost, 1);
        if (!edge) {
            gs_vertex_destroy(neighbor);
            continue;
        }
        
        gs_edge_set_owns_target_vertex(edge, true);
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    return 0;
}

// Test zero cost edge behavior
TEST(dijkstra_zero_cost_edges) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "zero_cost", zero_cost_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {3, 3};
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    
    // With zero cost edges, total cost should be 0
    const double* total_cost = gs_path_get_total_cost(path);
    ASSERT_NOT_NULL(total_cost);
    ASSERT_DOUBLE_EQ(0.0, total_cost[0], 1e-6);
    
    // Should still find a valid path
    ASSERT(gs_path_get_num_edges(path) > 0);
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Cycle provider - creates a graph with cycles
static int cycle_provider(const GraphserverVertex* current_vertex,
                         GraphserverEdgeList* out_edges,
                         void* user_data) {
    (void)user_data;
    
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(current_vertex, "x", &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(current_vertex, "y", &y_val) != GS_SUCCESS) {
        return -1;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    // Create a graph with cycles: each vertex connects to neighbors AND back to (0,0)
    // This creates many cycles in the graph
    
    // Normal grid connections
    int dx[] = {-1, 1, 0, 0};
    int dy[] = {0, 0, -1, 1};
    
    for (int i = 0; i < 4; i++) {
        int nx = x + dx[i];
        int ny = y + dy[i];
        
        if (nx < 0 || nx > 5 || ny < 0 || ny > 5) continue;
        
        GraphserverVertex* neighbor = create_coordinate_vertex(nx, ny);
        if (!neighbor) continue;
        
        double cost = 1.0;
        GraphserverEdge* edge = gs_edge_create(neighbor, &cost, 1);
        if (!edge) {
            gs_vertex_destroy(neighbor);
            continue;
        }
        
        gs_edge_set_owns_target_vertex(edge, true);
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    // Add cycle: every non-origin vertex has an edge back to origin
    if (x != 0 || y != 0) {
        GraphserverVertex* origin = create_coordinate_vertex(0, 0);
        if (origin) {
            double cost = 1.0;
            GraphserverEdge* cycle_edge = gs_edge_create(origin, &cost, 1);
            if (cycle_edge) {
                gs_edge_set_owns_target_vertex(cycle_edge, true);
                gs_edge_list_add_edge(out_edges, cycle_edge);
            } else {
                gs_vertex_destroy(origin);
            }
        }
    }
    
    return 0;
}

// Test cycle handling
TEST(dijkstra_graph_with_cycles) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "cycle", cycle_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {3, 3};
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    ASSERT_NOT_NULL(path);
    
    // Should find optimal path despite cycles
    const double* total_cost = gs_path_get_total_cost(path);
    ASSERT_NOT_NULL(total_cost);
    ASSERT_DOUBLE_EQ(6.0, total_cost[0], 1e-6); // Manhattan distance
    
    // Algorithm should terminate (not infinite loop)
    ASSERT(stats.vertices_expanded > 0);
    ASSERT(stats.vertices_expanded < 100); // Reasonable bound
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Error provider - fails after a certain number of calls
static int error_call_count = 0;
static int error_provider(const GraphserverVertex* current_vertex,
                         GraphserverEdgeList* out_edges,
                         void* user_data) {
    (void)out_edges;
    (void)current_vertex;
    (void)user_data;
    
    error_call_count++;
    
    // Fail after 3 calls
    if (error_call_count > 3) {
        return -1; // Provider error
    }
    
    // First few calls succeed but provide no edges (dead ends)
    return 0;
}

// Test provider error handling
TEST(dijkstra_provider_error) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    error_call_count = 0; // Reset counter
    gs_engine_register_provider(engine, "error", error_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {5, 5};
    
    // This should fail due to provider error
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    // Should return NULL due to provider failure
    ASSERT_NULL(path);
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test timeout behavior
TEST(dijkstra_timeout_behavior) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Set very short timeout
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.default_timeout_seconds = 0.001; // 1 millisecond
    gs_engine_set_config(engine, &config);
    
    gs_engine_register_provider(engine, "grid", simple_grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {10, 10}; // Far target requiring many expansions
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    // May or may not find path due to timeout, but should not crash
    // and should have reasonable statistics
    ASSERT(stats.planning_time_seconds >= 0);
    
    if (path) {
        gs_path_destroy(path);
    }
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test statistics tracking
TEST(dijkstra_statistics_tracking) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "grid", simple_grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {2, 2};
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    ASSERT_NOT_NULL(path);
    
    // Verify statistics are reasonable
    ASSERT(stats.vertices_expanded > 0);
    ASSERT(stats.edges_generated >= stats.vertices_expanded);
    ASSERT(stats.planning_time_seconds >= 0);
    ASSERT_EQ(4, stats.path_length); // 4 edges for optimal path
    ASSERT(stats.peak_memory_usage > 0);
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test start vertex is goal case
TEST(dijkstra_start_is_goal) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "grid", simple_grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(5, 5);
    CoordinateGoal goal = {5, 5}; // Same as start
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(0, gs_path_get_num_edges(path)); // Empty path
    
    const double* total_cost = gs_path_get_total_cost(path);
    if (total_cost) {
        ASSERT_DOUBLE_EQ(0.0, total_cost[0], 1e-6);
    }
    
    // Should have minimal statistics since no search needed
    // Note: The start vertex is still expanded to check if it's the goal
    ASSERT(stats.vertices_expanded <= 1);
    ASSERT_EQ(0, stats.path_length);
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test memory cleanup on failure
TEST(dijkstra_cleanup_on_failure) {
    GraphserverArena* arena = gs_arena_create(4096);
    DijkstraState state;
    
    // Initialize state successfully
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {5, 5};
    
    GraphserverResult result = dijkstra_init(
        &state, start, coordinate_goal_predicate, &goal, arena, 10.0);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Cleanup should work without issues
    dijkstra_cleanup(&state);
    
    // Cleanup should be safe to call multiple times
    dijkstra_cleanup(&state);
    dijkstra_cleanup(NULL); // NULL should be safe
    
    gs_vertex_destroy(start);
    gs_arena_destroy(arena);
}

// Main test runner
int main(void) {
    printf("Running Dijkstra Internals Tests\n");
    printf("=================================\n");
    
    run_test_dijkstra_state_initialization();
    run_test_dijkstra_state_null_parameters();
    run_test_dijkstra_path_reconstruction_basic();
    run_test_dijkstra_zero_cost_edges();
    run_test_dijkstra_graph_with_cycles();
    run_test_dijkstra_provider_error();
    run_test_dijkstra_timeout_behavior();
    run_test_dijkstra_statistics_tracking();
    run_test_dijkstra_start_is_goal();
    run_test_dijkstra_cleanup_on_failure();
    
    printf("\n=================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}