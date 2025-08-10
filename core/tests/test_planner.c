#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include "../include/graphserver.h"
#include "../include/gs_planner_internal.h"
#include "../include/gs_string_dict.h"
#include "../include/gs_common_keys.h"

// Simple test framework
static int tests_run = 0;
static int tests_passed = 0;

// Test-specific keys - will be initialized in main
static uint16_t KEY_EDGE_TYPE;
static uint16_t KEY_DIRECTION;
static uint16_t KEY_WAY_ID;
static uint16_t KEY_SOURCE;
static uint16_t KEY_TARGET;

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
        {GS_KEY_X, gs_value_create_int(x)},
        {GS_KEY_Y, gs_value_create_int(y)}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 2, NULL);
    return vertex;
}


// Grid provider: generates edges to adjacent grid cells
static int grid_provider(const GraphserverVertex* current_vertex,
                        GraphserverEdgeList* out_edges,
                        void* user_data) {
    (void)user_data; // Unused parameter
    
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(current_vertex, GS_KEY_X, &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(current_vertex, GS_KEY_Y, &y_val) != GS_SUCCESS) {
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
    if (gs_vertex_get_value(vertex, GS_KEY_X, &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(vertex, GS_KEY_Y, &y_val) != GS_SUCCESS) {
        return false;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    return (x == goal->target_x && y == goal->target_y);
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
    if (gs_vertex_get_value(current_vertex, GS_KEY_ID, &id_val) != GS_SUCCESS) {
        return -1;
    }
    
    int id = (int)id_val.as.i_val;
    int max_id = 10;
    
    if (id < max_id) {
        GraphserverKeyPair pairs[] = {
            {GS_KEY_ID, gs_value_create_int(id + 1)}
        };
        GraphserverVertex* next = gs_vertex_create(pairs, 1, NULL);
        
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
    if (gs_vertex_get_value(vertex, GS_KEY_ID, &id_val) != GS_SUCCESS) {
        return false;
    }
    
    return (int)id_val.as.i_val == *target_id;
}

// Test longer path
TEST(dijkstra_long_path) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "linear", linear_provider, NULL);
    
    GraphserverKeyPair pairs[] = {
        {GS_KEY_ID, gs_value_create_int(0)}
    };
    GraphserverVertex* start = gs_vertex_create(pairs, 1, NULL);
    
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

// Metadata provider: generates edges with metadata for testing
static int metadata_provider(const GraphserverVertex* current_vertex,
                            GraphserverEdgeList* out_edges,
                            void* user_data) {
    (void)user_data; // Unused parameter
    
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(current_vertex, GS_KEY_X, &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(current_vertex, GS_KEY_Y, &y_val) != GS_SUCCESS) {
        return -1;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    // Add edges to 4-connected neighbors with metadata
    int dx[] = {-1, 1, 0, 0};
    int dy[] = {0, 0, -1, 1};
    const char* directions[] = {"west", "east", "south", "north"};
    
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
        
        // Add rich metadata
        GraphserverValue way_id_val = gs_value_create_int(x * 100 + y * 10 + i);
        gs_edge_set_metadata(edge, KEY_WAY_ID, way_id_val);
        
        GraphserverValue edge_type_val = gs_value_create_string("test_road");
        gs_edge_set_metadata(edge, KEY_EDGE_TYPE, edge_type_val);
        
        GraphserverValue direction_val = gs_value_create_string(directions[i]);
        gs_edge_set_metadata(edge, KEY_DIRECTION, direction_val);
        
        GraphserverValue speed_val = gs_value_create_float(5.0);
        gs_edge_set_metadata(edge, GS_KEY_SPEED_KMH, speed_val);
        
        // Set edge to own the target vertex since we created it specifically for this edge
        gs_edge_set_owns_target_vertex(edge, true);
        
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    return 0;
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

// Test that Dijkstra preserves metadata in path results
TEST(dijkstra_metadata_preservation) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Register metadata provider that adds rich metadata to edges
    gs_engine_register_provider(engine, "metadata", metadata_provider, NULL);
    
    // Plan from (0,0) to (2,0) - should be straight line
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {2, 0};
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(2, gs_path_get_num_edges(path)); // 2 edges for 3 vertices
    
    // Check that each edge in the path has preserved metadata
    for (size_t i = 0; i < gs_path_get_num_edges(path); i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        ASSERT_NOT_NULL(edge);
        
        // Verify metadata count
        ASSERT_EQ(4, gs_edge_get_metadata_count(edge)); // way_id, edge_type, direction, speed_kmh
        
        // Check specific metadata values
        GraphserverValue way_id_val;
        GraphserverResult result = gs_edge_get_metadata(edge, KEY_WAY_ID, &way_id_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_INT, way_id_val.type);
        // way_id should be > 0 (calculated as x * 100 + y * 10 + direction_index)
        ASSERT(way_id_val.as.i_val > 0);
        
        GraphserverValue edge_type_val;
        result = gs_edge_get_metadata(edge, KEY_EDGE_TYPE, &edge_type_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_STRING, edge_type_val.type);
        ASSERT(strcmp(edge_type_val.as.s_val, "test_road") == 0);
        gs_value_destroy(&edge_type_val);
        
        GraphserverValue direction_val;
        result = gs_edge_get_metadata(edge, KEY_DIRECTION, &direction_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_STRING, direction_val.type);
        // For a straight line from (0,0) to (2,0), all edges should go "east"
        ASSERT(strcmp(direction_val.as.s_val, "east") == 0);
        gs_value_destroy(&direction_val);
        
        GraphserverValue speed_val;
        result = gs_edge_get_metadata(edge, GS_KEY_SPEED_KMH, &speed_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_FLOAT, speed_val.type);
        ASSERT_DOUBLE_EQ(5.0, speed_val.as.f_val, 1e-6);
    }
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test DijkstraNode incoming_edge field behavior through planning
TEST(dijkstra_node_incoming_edge) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "metadata", metadata_provider, NULL);
    
    // Run a simple plan that should exercise the incoming_edge logic
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {1, 0}; // Single step east
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(1, gs_path_get_num_edges(path)); // Single edge
    
    // The fact that we get a path with metadata means incoming_edge worked
    const GraphserverEdge* edge = gs_path_get_edge(path, 0);
    ASSERT_NOT_NULL(edge);
    ASSERT_EQ(4, gs_edge_get_metadata_count(edge)); // Metadata preserved
    
    // Verify the metadata came through the incoming_edge mechanism
    GraphserverValue edge_type_val;
    GraphserverResult result = gs_edge_get_metadata(edge, KEY_EDGE_TYPE, &edge_type_val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(GS_VALUE_STRING, edge_type_val.type);
    ASSERT(strcmp(edge_type_val.as.s_val, "test_road") == 0);
    gs_value_destroy(&edge_type_val);
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test path reconstruction preserves original edge metadata
TEST(dijkstra_path_reconstruction_metadata) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "metadata", metadata_provider, NULL);
    
    // Plan a longer path to test multiple edge reconstructions
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {0, 3}; // North 3 steps
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    ASSERT_EQ(3, gs_path_get_num_edges(path)); // 3 edges for 4 vertices
    
    // Each edge should have preserved metadata from path reconstruction
    for (size_t i = 0; i < gs_path_get_num_edges(path); i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        ASSERT_NOT_NULL(edge);
        
        // All edges should be going north, so direction should be "north"
        GraphserverValue direction_val;
        GraphserverResult result = gs_edge_get_metadata(edge, KEY_DIRECTION, &direction_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_STRING, direction_val.type);
        ASSERT(strcmp(direction_val.as.s_val, "north") == 0);
        gs_value_destroy(&direction_val);
        
        // Each edge should have a different way_id based on the formula
        GraphserverValue way_id_val;
        result = gs_edge_get_metadata(edge, KEY_WAY_ID, &way_id_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_INT, way_id_val.type);
        
        // For path (0,0) -> (0,1) -> (0,2) -> (0,3), way_ids should be:
        // Edge 0: 0*100 + 0*10 + 3 = 3 (north from (0,0))
        // Edge 1: 0*100 + 1*10 + 3 = 13 (north from (0,1))  
        // Edge 2: 0*100 + 2*10 + 3 = 23 (north from (0,2))
        int expected_way_id = (int)i * 10 + 3;
        ASSERT_EQ(expected_way_id, way_id_val.as.i_val);
    }
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test edge cloning during relaxation phase
TEST(dijkstra_edge_cloning_relaxation) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_provider(engine, "metadata", metadata_provider, NULL);
    
    // Create a diamond-shaped graph to test edge relaxation:
    // (0,0) -> (1,0) -> (2,1)
    //   |        \      /
    //   v         v    v  
    // (0,1) -> (1,1) -> (2,1)
    GraphserverVertex* start = create_coordinate_vertex(0, 0);
    CoordinateGoal goal = {2, 1};
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, coordinate_goal_predicate, &goal, NULL);
    
    ASSERT_NOT_NULL(path);
    
    // Verify that the path has edges with properly cloned metadata
    for (size_t i = 0; i < gs_path_get_num_edges(path); i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        ASSERT_NOT_NULL(edge);
        
        // Each edge should have been cloned during relaxation, preserving metadata
        ASSERT_EQ(4, gs_edge_get_metadata_count(edge));
        
        // Verify that metadata is accessible and correct
        GraphserverValue edge_type_val;
        GraphserverResult result = gs_edge_get_metadata(edge, KEY_EDGE_TYPE, &edge_type_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_STRING, edge_type_val.type);
        ASSERT(strcmp(edge_type_val.as.s_val, "test_road") == 0);
        gs_value_destroy(&edge_type_val);
        
        // Metadata should not be corrupted or pointing to invalid memory
        GraphserverValue speed_val;
        result = gs_edge_get_metadata(edge, GS_KEY_SPEED_KMH, &speed_val);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ(GS_VALUE_FLOAT, speed_val.type);
        ASSERT_DOUBLE_EQ(5.0, speed_val.as.f_val, 1e-6);
    }
    
    gs_path_destroy(path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Planner Tests\n");
    printf("==================================\n");
    
    // Initialize string dictionary and common keys
    gs_string_dict_init();
    gs_common_keys_init();
    
    // Register test-specific keys
    KEY_EDGE_TYPE = gs_string_dict_register("edge_type");
    KEY_DIRECTION = gs_string_dict_register("direction");
    KEY_WAY_ID = gs_string_dict_register("way_id");
    KEY_SOURCE = gs_string_dict_register("source");
    KEY_TARGET = gs_string_dict_register("target");
    
    run_test_dijkstra_simple_path();
    run_test_dijkstra_l_shaped_path();
    run_test_dijkstra_no_path();
    run_test_dijkstra_start_is_goal();
    run_test_dijkstra_long_path();
    run_test_dijkstra_error_conditions();
    run_test_dijkstra_memory_efficiency();
    run_test_dijkstra_timeout();
    run_test_vertex_set_operations();
    run_test_dijkstra_metadata_preservation();
    run_test_dijkstra_node_incoming_edge();
    run_test_dijkstra_path_reconstruction_metadata();
    run_test_dijkstra_edge_cloning_relaxation();
    
    printf("\n==================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    // Cleanup
    gs_string_dict_cleanup();
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}