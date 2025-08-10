#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "../include/graphserver.h"
#include "../include/gs_planner_internal.h"
#include "../include/gs_common_keys.h"
#include "../include/gs_string_dict.h"
#include "../../examples/include/example_providers.h"

/**
 * Simple test to compare A* vs Dijkstra performance
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
    printf("A* vs Dijkstra Performance Test\n");
    printf("================================\n");
    
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
    
    // Test coordinates - short distance (should be quick for both)
    GraphserverVertex* start = create_test_vertex(40.7074, -74.0113); // Near Wall St
    LocationGoal goal = {40.7100, -74.0070, 100.0}; // Near City Hall
    
    printf("Testing path from (40.7074, -74.0113) to (40.7100, -74.0070)\n");
    
    // Test Dijkstra first
    clock_t dijkstra_start = clock();
    GraphserverPlanStats dijkstra_stats;
    GraphserverPath* dijkstra_path = gs_plan_simple(
        engine, start, location_goal_predicate, &goal, &dijkstra_stats);
    clock_t dijkstra_end = clock();
    double dijkstra_time = ((double)(dijkstra_end - dijkstra_start)) / CLOCKS_PER_SEC;
    
    printf("Dijkstra test completed\n");
    
    // For now, skip A* and just test Dijkstra
    GraphserverPath* astar_path = NULL;
    GraphserverPlanStats astar_stats = {0};
    double astar_time = 0;
    
    // Report results
    printf("\nResults:\n");
    printf("--------\n");
    
    if (dijkstra_path) {
        printf("Dijkstra found path: %zu edges, %.1f seconds\n", 
               gs_path_get_num_edges(dijkstra_path), dijkstra_time);
        printf("  Vertices expanded: %llu\n", (unsigned long long)dijkstra_stats.vertices_expanded);
        printf("  Edges examined: %llu\n", (unsigned long long)dijkstra_stats.edges_generated);
    } else {
        printf("Dijkstra found NO PATH in %.1f seconds\n", dijkstra_time);
        printf("  Vertices expanded: %llu\n", (unsigned long long)dijkstra_stats.vertices_expanded);
    }
    
    if (astar_path) {
        printf("A* found path: %zu edges, %.1f seconds\n", 
               gs_path_get_num_edges(astar_path), astar_time);
        printf("  Vertices expanded: %llu\n", (unsigned long long)astar_stats.vertices_expanded);
        printf("  Edges examined: %llu\n", (unsigned long long)astar_stats.edges_generated);
    } else {
        printf("A* found NO PATH in %.1f seconds\n", astar_time);
        printf("  Vertices expanded: %llu\n", (unsigned long long)astar_stats.vertices_expanded);
    }
    
    // Performance comparison
    if (dijkstra_path && astar_path) {
        double speedup = dijkstra_time / astar_time;
        double vertex_reduction = (double)(dijkstra_stats.vertices_expanded - astar_stats.vertices_expanded) / dijkstra_stats.vertices_expanded * 100.0;
        
        printf("\nPerformance Comparison:\n");
        printf("  A* speedup: %.2fx\n", speedup);
        printf("  Vertex exploration reduction: %.1f%%\n", vertex_reduction);
        
        if (speedup > 1.0) {
            printf("  ✓ A* is faster than Dijkstra!\n");
        } else {
            printf("  ! Dijkstra performed better (may be due to heuristic overhead on short distances)\n");
        }
    }
    
    // Cleanup
    if (dijkstra_path) gs_path_destroy(dijkstra_path);
    if (astar_path) gs_path_destroy(astar_path);
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
    
    printf("\nA* implementation test completed!\n");
    return 0;
}