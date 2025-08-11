#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "../include/graphserver.h"
#include "../include/gs_planner_internal.h"
#include "../include/gs_common_keys.h"
#include "../include/gs_string_dict.h"
#include "../../examples/include/example_providers.h"

/**
 * Simple zero heuristic for A* that should behave like Dijkstra
 */
double zero_heuristic(const GraphserverVertex* vertex, void* goal_data) {
    (void)vertex;
    (void)goal_data;
    return 0.0; // Zero heuristic = Dijkstra behavior
}

// Create a test vertex at given coordinates
GraphserverVertex* create_test_vertex(double lat, double lon) {
    GraphserverKeyPair pairs[2];
    pairs[0].key = GS_KEY_LAT;
    pairs[0].value = gs_value_create_float(lat);
    pairs[1].key = GS_KEY_LON;
    pairs[1].value = gs_value_create_float(lon);
    
    return gs_vertex_create(pairs, 2, NULL);
}

int main() {
    printf("A* with Zero Heuristic Test (should behave like Dijkstra)\n");
    printf("=========================================================\n");
    
    // Initialize graphserver
    if (gs_initialize() != GS_SUCCESS) {
        printf("ERROR: Failed to initialize graphserver\n");
        return 1;
    }
    
    // Initialize string dictionary and common keys
    gs_string_dict_init();
    if (!gs_common_keys_init()) {
        printf("ERROR: Failed to initialize common keys\n");
        return 1;
    }
    
    // Create engine
    GraphserverEngine* engine = gs_engine_create();
    if (!engine) {
        printf("ERROR: Failed to create engine\n");
        return 1;
    }
    
    // Setup walking provider
    WalkingConfig walking_config = walking_config_default();
    gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
    
    // Test coordinates
    GraphserverVertex* start = create_test_vertex(40.7074, -74.0113);
    LocationGoal goal = {40.7100, -74.0070, 100.0};
    
    printf("Testing A* with zero heuristic\n");
    printf("Start: (40.7074, -74.0113), Goal: (40.7100, -74.0070)\n");
    
    // Create arena
    GraphserverArena* arena = gs_arena_create(1024 * 1024);
    if (!arena) {
        printf("ERROR: Failed to create arena\n");
        return 1;
    }
    
    // Test A* with zero heuristic
    printf("Testing...\n");
    fflush(stdout);
    
    clock_t start_time = clock();
    GraphserverPath* path = NULL;
    GraphserverPlanStats stats;
    
    GraphserverResult result = gs_plan_astar(
        engine,
        start,
        location_goal_predicate,
        &goal,
        zero_heuristic,
        &goal,
        5.0,  // 5 second timeout
        arena,
        &path,
        &stats
    );
    
    clock_t end_time = clock();
    double elapsed = ((double)(end_time - start_time)) / CLOCKS_PER_SEC;
    
    printf("A* with zero heuristic completed in %.3f seconds\n", elapsed);
    printf("Result: %d\n", result);
    printf("Vertices expanded: %llu\n", (unsigned long long)stats.vertices_expanded);
    
    if (path) {
        printf("Path found: %zu edges\n", gs_path_get_num_edges(path));
        gs_path_destroy(path);
    }
    
    // Cleanup
    gs_vertex_destroy(start);
    gs_arena_destroy(arena);
    gs_engine_destroy(engine);
    
    return 0;
}