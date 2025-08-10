#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "../include/graphserver.h"
#include "../include/gs_planner_internal.h"
#include "../include/gs_common_keys.h"
#include "../include/gs_string_dict.h"
#include "../../examples/include/example_providers.h"

/**
 * Direct test of A* implementation
 */

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
    printf("Direct A* Implementation Test\n");
    printf("============================\n");
    
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
    GraphserverVertex* start = create_test_vertex(40.7074, -74.0113); // Near Wall St
    LocationGoal goal = {40.7100, -74.0070, 100.0}; // Near City Hall
    
    printf("Testing A* directly with geographic heuristic\n");
    printf("Start: (40.7074, -74.0113), Goal: (40.7100, -74.0070)\n");
    
    // Test A* directly
    GraphserverArena* arena = gs_arena_create(1024 * 1024);
    if (!arena) {
        printf("ERROR: Failed to create arena\n");
        return 1;
    }
    
    clock_t astar_start = clock();
    GraphserverPath* astar_path = NULL;
    GraphserverPlanStats astar_stats;
    
    GraphserverResult result = gs_plan_astar(
        engine,
        start,
        location_goal_predicate,
        &goal,
        geographic_distance_heuristic,
        &goal, // Use same goal data for heuristic
        10.0,  // 10 second timeout
        arena,
        &astar_path,
        &astar_stats
    );
    
    clock_t astar_end = clock();
    double astar_time = ((double)(astar_end - astar_start)) / CLOCKS_PER_SEC;
    
    // Report results
    printf("\nDirect A* Results:\n");
    printf("------------------\n");
    printf("Result code: %d ", result);
    
    switch (result) {
        case GS_SUCCESS:
            printf("(SUCCESS)\n");
            break;
        case GS_ERROR_NO_PATH_FOUND:
            printf("(NO_PATH_FOUND)\n");
            break;
        case GS_ERROR_TIMEOUT:
            printf("(TIMEOUT)\n");
            break;
        case GS_ERROR_OUT_OF_MEMORY:
            printf("(OUT_OF_MEMORY)\n");
            break;
        case GS_ERROR_NULL_POINTER:
            printf("(NULL_POINTER)\n");
            break;
        default:
            printf("(UNKNOWN_ERROR)\n");
            break;
    }
    
    printf("Time: %.3f seconds\n", astar_time);
    printf("Vertices expanded: %llu\n", (unsigned long long)astar_stats.vertices_expanded);
    printf("Edges examined: %llu\n", (unsigned long long)astar_stats.edges_generated);
    
    if (astar_path) {
        printf("Path found: %zu edges\n", gs_path_get_num_edges(astar_path));
        gs_path_destroy(astar_path);
    } else {
        printf("No path found\n");
    }
    
    // Cleanup
    gs_vertex_destroy(start);
    gs_arena_destroy(arena);
    gs_engine_destroy(engine);
    
    printf("\nDirect A* test completed!\n");
    return 0;
}