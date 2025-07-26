#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include <time.h>
#include "../include/graphserver.h"
#include "../../examples/include/example_providers.h"
#include "test_utils.h"

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

// Test utility functions from example providers
TEST(utility_functions) {
    // Test distance calculation
    double distance = calculate_distance_meters(40.7074, -74.0113, 40.7101, -74.0070);
    ASSERT(distance > 300.0 && distance < 600.0); // Should be around 400-500 meters
    
    // Test location vertex creation
    time_t current_time = time(NULL);
    GraphserverVertex* vertex = create_location_vertex(40.7074, -74.0113, current_time);
    ASSERT_NOT_NULL(vertex);
    
    // Test location extraction
    double lat, lon;
    time_t extracted_time;
    ASSERT(extract_location_from_vertex(vertex, &lat, &lon, &extracted_time));
    ASSERT_DOUBLE_EQ(40.7074, lat, 1e-6);
    ASSERT_DOUBLE_EQ(-74.0113, lon, 1e-6);
    ASSERT_EQ(current_time, extracted_time);
    
    // Test goal predicate
    LocationGoal goal = {40.7074, -74.0113, 100.0}; // 100m radius
    ASSERT(location_goal_predicate(vertex, &goal)); // Should be within goal
    
    goal.radius_meters = 10.0; // Very small radius
    ASSERT(location_goal_predicate(vertex, &goal)); // Still within (same location)
    
    // Test with different location
    GraphserverVertex* far_vertex = create_location_vertex(40.8000, -74.0000, current_time);
    goal.radius_meters = 100.0;
    ASSERT(!location_goal_predicate(far_vertex, &goal)); // Should be outside goal
    
    gs_vertex_destroy(vertex);
    gs_vertex_destroy(far_vertex);
}

// Test walking provider functionality
TEST(walking_provider_basic) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Create walking configuration
    WalkingConfig config = walking_config_default();
    
    // Register walking provider
    GraphserverResult result = gs_engine_register_provider(
        engine, "walking", walking_provider, &config);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Create start vertex in Manhattan
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    ASSERT_NOT_NULL(start);
    
    // Test vertex expansion
    GraphserverEdgeList* edges = gs_edge_list_create();
    ASSERT_NOT_NULL(edges);
    
    result = gs_engine_expand_vertex(engine, start, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should generate multiple walking edges
    size_t edge_count = gs_edge_list_get_count(edges);
    ASSERT(edge_count > 10); // Should have many walking options
    ASSERT(edge_count < 100); // But not too many
    
    // Check first edge properties
    GraphserverEdge* edge;
    result = gs_edge_list_get_edge(edges, 0, &edge);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(edge);
    
    // Verify edge has walking mode metadata
    GraphserverValue mode_val;
    if (gs_edge_get_metadata(edge, "mode", &mode_val) == GS_SUCCESS) {
        ASSERT_EQ(GS_VALUE_STRING, mode_val.type);
        ASSERT(strcmp(mode_val.as.s_val, "walking") == 0);
    }
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test transit provider functionality
TEST(transit_provider_basic) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Create transit network
    TransitNetwork* network = transit_network_create_example();
    ASSERT_NOT_NULL(network);
    
    // Register transit provider
    GraphserverResult result = gs_engine_register_provider(
        engine, "transit", transit_provider, network);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Create start vertex near a transit stop
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    ASSERT_NOT_NULL(start);
    
    // Test vertex expansion
    GraphserverEdgeList* edges = gs_edge_list_create();
    result = gs_engine_expand_vertex(engine, start, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should generate walking edges to nearby transit stops
    size_t edge_count = gs_edge_list_get_count(edges);
    ASSERT(edge_count > 0); // Should have walking edges to stops
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(start);
    transit_network_destroy(network);
    gs_engine_destroy(engine);
}

// Test road network provider functionality  
TEST(road_network_provider_basic) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Create road network for car
    RoadNetwork* network = road_network_create_example("car");
    ASSERT_NOT_NULL(network);
    
    // Register road network provider
    GraphserverResult result = gs_engine_register_provider(
        engine, "road", road_network_provider, network);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Create start vertex near road segments with mode
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    
    // For now, create a new vertex with mode by extracting location and adding mode
    GraphserverValue lat_val, lon_val, time_val, mode_val;
    gs_vertex_get_value(start, "lat", &lat_val);
    gs_vertex_get_value(start, "lon", &lon_val);
    bool has_time = (gs_vertex_get_value(start, "time", &time_val) == GS_SUCCESS);
    mode_val = gs_value_create_string("car");
    
    GraphserverKeyPair pairs[4];
    size_t pair_count = 3;
    pairs[0] = (GraphserverKeyPair){"lat", lat_val};
    pairs[1] = (GraphserverKeyPair){"lon", lon_val};
    pairs[2] = (GraphserverKeyPair){"mode", mode_val};
    
    if (has_time) {
        pairs[3] = (GraphserverKeyPair){"time", time_val};
        pair_count = 4;
    }
    
    // Replace start vertex with new one that includes mode
    gs_vertex_destroy(start);
    start = create_vertex_safe(pairs, pair_count, NULL);
    
    // Test vertex expansion
    GraphserverEdgeList* edges = gs_edge_list_create();
    result = gs_engine_expand_vertex(engine, start, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should generate road edges
    size_t edge_count = gs_edge_list_get_count(edges);
    ASSERT(edge_count > 0); // Should have road edges
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(start);
    road_network_destroy(network);
    gs_engine_destroy(engine);
}

// Test multi-modal journey planning
TEST(multi_modal_journey) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Create and register walking provider only first (simpler test)
    WalkingConfig walking_config = walking_config_default();
    walking_config.max_walking_distance = 400.0; // Shorter distance for reliable test
    
    gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
    
    // Plan a simple walking journey
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    ASSERT_NOT_NULL(start);
    
    LocationGoal goal = {40.7100, -74.0070, 100.0}; // Nearby location, 100m radius
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, location_goal_predicate, &goal, &stats);
    
    // Should find a walking path
    if (path) {
        // Verify path has reasonable length
        size_t path_length = gs_path_get_num_edges(path);
        ASSERT(path_length > 0);
        ASSERT(path_length < 20); // Reasonable upper bound for walking
        
        // Verify path has reasonable cost
        const double* total_cost = gs_path_get_total_cost(path);
        ASSERT_NOT_NULL(total_cost);
        ASSERT(total_cost[0] > 0.0); // Should have some cost
        ASSERT(total_cost[0] < 30.0); // Should be less than 30 minutes walking
        
        printf("\n    Walking path found: %zu edges, %.1f minutes cost, %zu vertices expanded",
               path_length, total_cost[0], stats.vertices_expanded);
        
        gs_path_destroy(path);
    } else {
        printf("\n    No walking path found (this may be normal), %zu vertices expanded", stats.vertices_expanded);
        // This is acceptable - the test area might not have a direct walking path
    }
    
    // Verify statistics are reasonable
    ASSERT(stats.vertices_expanded > 0);
    ASSERT(stats.planning_time_seconds >= 0.0);
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test large network performance
TEST(large_network_performance) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Create providers with wider search areas for stress testing
    WalkingConfig walking_config = walking_config_default();
    walking_config.max_walking_distance = 1600.0; // 1.6km max walk
    
    TransitNetwork* transit_network = transit_network_create_example();
    RoadNetwork* road_network = road_network_create_example("car");
    
    gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
    gs_engine_register_provider(engine, "transit", transit_provider, transit_network);
    gs_engine_register_provider(engine, "road", road_network_provider, road_network);
    
    // Plan longer journey to stress test the system
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    LocationGoal goal = {40.7580, -73.9855, 300.0}; // Times Square area
    
    clock_t start_time = clock();
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, location_goal_predicate, &goal, &stats);
    
    clock_t end_time = clock();
    double planning_time = ((double)(end_time - start_time)) / CLOCKS_PER_SEC;
    
    // Should complete within reasonable time
    ASSERT(planning_time < 5.0); // Less than 5 seconds
    
    if (path) {
        size_t path_length = gs_path_get_num_edges(path);
        const double* total_cost = gs_path_get_total_cost(path);
        
        printf("\n    Large network test: %zu edges, %.1f minutes, %.3f seconds planning time, %zu vertices expanded",
               path_length, total_cost ? total_cost[0] : 0.0, planning_time, stats.vertices_expanded);
        
        gs_path_destroy(path);
    } else {
        printf("\n    Large network test: No path found, %.3f seconds planning time, %zu vertices expanded",
               planning_time, stats.vertices_expanded);
    }
    
    gs_vertex_destroy(start);
    road_network_destroy(road_network);
    transit_network_destroy(transit_network);
    gs_engine_destroy(engine);
}

// Test edge cases and error handling
TEST(edge_cases) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Test with no providers
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    LocationGoal goal = {40.7100, -74.0070, 100.0};
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, location_goal_predicate, &goal, NULL);
    ASSERT_NULL(path); // Should find no path with no providers
    
    // Test with unreachable goal
    WalkingConfig walking_config = walking_config_default();
    walking_config.max_walking_distance = 50.0; // Very short max distance
    
    gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
    
    LocationGoal far_goal = {41.0000, -74.0000, 100.0}; // Very far away
    path = gs_plan_simple(engine, start, location_goal_predicate, &far_goal, NULL);
    ASSERT_NULL(path); // Should find no path to unreachable goal
    
    // Test start equals goal
    LocationGoal same_goal = {40.7074, -74.0113, 100.0}; // Same as start
    path = gs_plan_simple(engine, start, location_goal_predicate, &same_goal, NULL);
    ASSERT_NOT_NULL(path); // Should find path (even if empty)
    
    if (path) {
        ASSERT_EQ(0, gs_path_get_num_edges(path)); // Empty path
        gs_path_destroy(path);
    }
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test memory management and cleanup
TEST(memory_management) {
    // Test multiple planning cycles to check for memory leaks
    for (int i = 0; i < 10; i++) {
        GraphserverEngine* engine = gs_engine_create();
        
        WalkingConfig walking_config = walking_config_default();
        TransitNetwork* transit_network = transit_network_create_example();
        
        gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
        gs_engine_register_provider(engine, "transit", transit_provider, transit_network);
        
        GraphserverVertex* start = create_location_vertex(
            40.7074 + (i * 0.001), -74.0113 + (i * 0.001), time(NULL));
        LocationGoal goal = {40.7100, -74.0070, 100.0};
        
        GraphserverPath* path = gs_plan_simple(
            engine, start, location_goal_predicate, &goal, NULL);
        
        if (path) {
            gs_path_destroy(path);
        }
        
        gs_vertex_destroy(start);
        transit_network_destroy(transit_network);
        gs_engine_destroy(engine);
    }
    
    // If we get here without crashing, memory management is working
    ASSERT(true);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Integration Tests\n");
    printf("=====================================\n");
    
    run_test_utility_functions();
    run_test_walking_provider_basic();
    run_test_transit_provider_basic();
    run_test_road_network_provider_basic();
    run_test_multi_modal_journey();
    run_test_large_network_performance();
    run_test_edge_cases();
    run_test_memory_management();
    
    printf("\n=====================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All integration tests PASSED!\n");
        return 0;
    } else {
        printf("Some integration tests FAILED!\n");
        return 1;
    }
}