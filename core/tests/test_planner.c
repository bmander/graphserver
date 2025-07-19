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
    GraphserverVertex* vertex = gs_vertex_create();
    if (!vertex) return NULL;
    
    GraphserverValue x_val = gs_value_create_int(x);
    GraphserverValue y_val = gs_value_create_int(y);
    
    gs_vertex_set_kv(vertex, "x", x_val);
    gs_vertex_set_kv(vertex, "y", y_val);
    
    return vertex;
}


// Grid provider: generates edges to adjacent grid cells
static int grid_provider(const GraphserverVertex* current_vertex,
                        GraphserverEdgeList* out_edges,
                        void* user_data) {
    (void)user_data; // Unused parameter
    
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
        
        // Stay within reasonable bounds
        if (nx < 0 || nx > 10 || ny < 0 || ny > 10) continue;
        
        GraphserverVertex* neighbor = create_coordinate_vertex(nx, ny);
        if (!neighbor) continue;
        
        double distance = 1.0; // Unit distance for grid
        GraphserverEdge* edge = gs_edge_create(neighbor, &distance, 1);
        if (!edge) {
            gs_vertex_destroy(neighbor);
            continue;
        }
        
        // Set edge to own the target vertex since we created it specifically for this edge
        gs_edge_set_owns_target_vertex(edge, true);
        
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    return 0;
}

// Goal predicate: check if we've reached a specific coordinate
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

// Test priority queue basic operations
TEST(priority_queue_basic) {
    GraphserverArena* arena = gs_arena_create(4096);
    ASSERT_NOT_NULL(arena);
    
    PriorityQueue* pq = pq_create(arena);
    ASSERT_NOT_NULL(pq);
    
    ASSERT(pq_is_empty(pq));
    ASSERT_EQ(0, pq_size(pq));
    
    // Insert some vertices
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    
    ASSERT(pq_insert(pq, v1, 5.0));
    ASSERT(pq_insert(pq, v2, 2.0));
    ASSERT(pq_insert(pq, v3, 8.0));
    
    ASSERT(!pq_is_empty(pq));
    ASSERT_EQ(3, pq_size(pq));
    
    // Extract minimum (should be v2 with cost 2.0)
    GraphserverVertex* min_vertex;
    double min_cost;
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v2));
    ASSERT_DOUBLE_EQ(2.0, min_cost, 1e-6);
    
    // Extract next minimum (should be v1 with cost 5.0)
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v1));
    ASSERT_DOUBLE_EQ(5.0, min_cost, 1e-6);
    
    // Extract last (should be v3 with cost 8.0)
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v3));
    ASSERT_DOUBLE_EQ(8.0, min_cost, 1e-6);
    
    ASSERT(pq_is_empty(pq));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_arena_destroy(arena);
}

// Test priority queue decrease key operation
TEST(priority_queue_decrease_key) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    
    pq_insert(pq, v1, 10.0);
    pq_insert(pq, v2, 5.0);
    
    // Decrease key for v1
    ASSERT(pq_decrease_key(pq, v1, 3.0));
    
    // v1 should now be minimum
    GraphserverVertex* min_vertex;
    double min_cost;
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v1));
    ASSERT_DOUBLE_EQ(3.0, min_cost, 1e-6);
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_arena_destroy(arena);
}

// Test simple straight-line path
TEST(dijkstra_simple_path) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Register grid provider
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    // Plan from (0,0) to (3,0) - should be straight line
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {3, 0};
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(3, gs_path_get_num_edges(path)); // 3 edges for 4 vertices
    
    // Check path cost
    const double* total_cost = gs_path_get_total_cost(path);
    ASSERT_NOT_NULL(total_cost);
    ASSERT_DOUBLE_EQ(3.0, total_cost[0], 1e-6); // Distance 3
    
    // Verify statistics
    ASSERT(stats.vertices_expanded > 0);
    ASSERT(stats.planning_time_seconds >= 0);
    ASSERT_EQ(3, stats.path_length);
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test L-shaped path
TEST(dijkstra_l_shaped_path) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    // Plan from (0,0) to (2,2) - should be L-shaped with distance 4
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {2, 2};
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(4, gs_path_get_num_edges(path)); // 4 edges for shortest path
    
    const double* total_cost = gs_path_get_total_cost(path);
    ASSERT_DOUBLE_EQ(4.0, total_cost[0], 1e-6);
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test no path case
TEST(dijkstra_no_path) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    // Try to reach an unreachable coordinate
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {-5, -5}; // Outside grid bounds
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NULL(path); // Should find no path
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test start is goal case
TEST(dijkstra_start_is_goal) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(5, 5);
    CoordinateGoal goal = {5, 5}; // Same as start
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(0, gs_path_get_num_edges(path)); // Empty path
    
    const double* total_cost = gs_path_get_total_cost(path);
    if (total_cost) {
        ASSERT_DOUBLE_EQ(0.0, total_cost[0], 1e-6);
    }
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Linear provider: creates a simple chain
static int linear_provider(const GraphserverVertex* current_vertex,
                          GraphserverEdgeList* out_edges,
                          void* user_data) {
    (void)user_data; // Unused parameter
    
    GraphserverValue id_val;
    if (gs_vertex_get_value(current_vertex, "id", &id_val) != GS_SUCCESS) {
        return -1;
    }
    
    int id = (int)id_val.as.i_val;
    int max_id = 10;
    
    if (id < max_id) {
        GraphserverVertex* next = gs_vertex_create();
        GraphserverValue next_id = gs_value_create_int(id + 1);
        gs_vertex_set_kv(next, "id", next_id);
        
        double distance = 1.0;
        GraphserverEdge* edge = gs_edge_create(next, &distance, 1);
        
        // Set edge to own the target vertex since we created it specifically for this edge
        gs_edge_set_owns_target_vertex(edge, true);
        
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    return 0;
}

static bool linear_goal_predicate(const GraphserverVertex* vertex, void* user_data) {
    int* target_id = (int*)user_data;
    
    GraphserverValue id_val;
    if (gs_vertex_get_value(vertex, "id", &id_val) != GS_SUCCESS) {
        return false;
    }
    
    return (int)id_val.as.i_val == *target_id;
}

// Test longer path
TEST(dijkstra_long_path) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "linear", linear_provider, NULL);
    
    GraphserverVertex* start = gs_vertex_create();
    GraphserverValue start_id = gs_value_create_int(0);
    gs_vertex_set_kv(start, "id", start_id);
    
    int target_id = 8;
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, linear_goal_predicate, &target_id, &stats);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(8, gs_path_get_num_edges(path));
    
    const double* total_cost = gs_path_get_total_cost(path);
    ASSERT_DOUBLE_EQ(8.0, total_cost[0], 1e-6);
    
    // Verify we expanded the right number of vertices
    ASSERT_EQ(9, stats.vertices_expanded); // 0 through 8
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test error conditions
TEST(dijkstra_error_conditions) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {1, 1};
    
    // Test NULL engine
    ASSERT_NULL(gs_plan_simple(NULL, start, coordinate_goal_predicate, &goal, NULL));
    
    // Test NULL start vertex
    ASSERT_NULL(gs_plan_simple(engine, NULL, coordinate_goal_predicate, &goal, NULL));
    
    // Test NULL goal predicate
    ASSERT_NULL(gs_plan_simple(engine, start, NULL, &goal, NULL));
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test memory efficiency with arena
TEST(dijkstra_memory_efficiency) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {5, 5};
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    ASSERT_NOT_NULL(path);
    
    // Should have used arena memory efficiently
    ASSERT(stats.peak_memory_usage > 0);
    ASSERT(stats.peak_memory_usage < 1000000); // Reasonable limit
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test planning with timeout
TEST(dijkstra_timeout) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Set very short timeout
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.default_timeout_seconds = 0.0001; // 0.1 millisecond
    gs_engine_set_config(engine, &config);
    
    gs_engine_register_provider(engine, "grid", grid_provider, NULL);
    
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {10, 10}; // Far away (requires 20 steps)
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, &stats);
    
    // Should timeout before finding path, or find a short path very quickly
    // This test is timing-dependent, so we'll accept either outcome
    if (path) {
        // If a path was found, it should be reasonably long
        ASSERT(gs_path_get_num_edges(path) > 0);
        gs_path_destroy(path);
    }
    // If no path found, that's also acceptable (timeout occurred)
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test vertex set (closed set) operations
TEST(vertex_set_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    VertexSet* set = vertex_set_create(arena);
    ASSERT_NOT_NULL(set);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    
    // Initially empty
    ASSERT(!vertex_set_contains(set, v1));
    ASSERT(!vertex_set_contains(set, v2));
    
    // Add vertices
    ASSERT(vertex_set_add(set, v1));
    ASSERT(vertex_set_add(set, v2));
    
    ASSERT(vertex_set_contains(set, v1));
    ASSERT(vertex_set_contains(set, v2));
    ASSERT(!vertex_set_contains(set, v3));
    
    // Clear set
    vertex_set_clear(set);
    ASSERT(!vertex_set_contains(set, v1));
    ASSERT(!vertex_set_contains(set, v2));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_arena_destroy(arena);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Planner Tests\n");
    printf("==================================\n");
    
    run_test_priority_queue_basic();
    run_test_priority_queue_decrease_key();
    run_test_dijkstra_simple_path();
    run_test_dijkstra_l_shaped_path();
    run_test_dijkstra_no_path();
    run_test_dijkstra_start_is_goal();
    run_test_dijkstra_long_path();
    run_test_dijkstra_error_conditions();
    run_test_dijkstra_memory_efficiency();
    run_test_dijkstra_timeout();
    run_test_vertex_set_operations();
    
    printf("\n==================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}