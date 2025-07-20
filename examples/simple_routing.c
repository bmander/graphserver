#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "include/example_providers.h"
#include "../core/include/graphserver.h"

/**
 * @file simple_routing.c
 * @brief Simple routing example demonstrating Graphserver Planning Engine usage
 * 
 * This example shows how to:
 * 1. Create a planning engine
 * 2. Register multiple providers (walking, transit, road network)
 * 3. Plan a multi-modal journey
 * 4. Analyze the results
 */

static void print_path_details(const GraphserverPath* path) {
    if (!path) {
        printf("No path found.\n");
        return;
    }
    
    size_t num_edges = gs_path_get_num_edges(path);
    const double* total_cost = gs_path_get_total_cost(path);
    
    printf("Path found with %zu edges\n", num_edges);
    if (total_cost) {
        printf("Total cost: %.1f minutes\n", total_cost[0]);
    }
    
    printf("Route details:\n");
    for (size_t i = 0; i < num_edges; i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        if (!edge) continue;
        
        const GraphserverVertex* target = gs_edge_get_target_vertex(edge);
        const double* distance_vector = gs_edge_get_distance_vector(edge);
        
        // Try to get mode from edge metadata
        GraphserverValue mode_val;
        const char* mode = "unknown";
        if (gs_edge_get_metadata(edge, "mode", &mode_val) == GS_SUCCESS && 
            mode_val.type == GS_VALUE_STRING) {
            mode = mode_val.as.s_val;
        }
        
        printf("  Step %zu: %s (%.1f minutes)\n", 
               i + 1, mode, distance_vector ? distance_vector[0] : 0.0);
        
        // Show additional details for different modes
        if (strcmp(mode, "walking") == 0) {
            GraphserverValue distance_val;
            if (gs_edge_get_metadata(edge, "distance_meters", &distance_val) == GS_SUCCESS &&
                distance_val.type == GS_VALUE_FLOAT) {
                printf("    Walk %.0f meters\n", distance_val.as.f_val);
            }
        } else if (strcmp(mode, "subway") == 0 || strcmp(mode, "bus") == 0) {
            GraphserverValue route_val;
            if (gs_edge_get_metadata(edge, "route_name", &route_val) == GS_SUCCESS &&
                route_val.type == GS_VALUE_STRING) {
                printf("    Take %s\n", route_val.as.s_val);
            }
        }
    }
    printf("\n");
}

int main(void) {
    printf("Graphserver Simple Routing Example\n");
    printf("==================================\n\n");
    
    // Initialize the library
    GraphserverResult init_result = gs_initialize();
    if (init_result != GS_SUCCESS) {
        printf("Failed to initialize Graphserver: %s\n", gs_get_error_message(init_result));
        return 1;
    }
    
    // Create the planning engine
    printf("1. Creating planning engine...\n");
    GraphserverEngine* engine = gs_engine_create();
    if (!engine) {
        printf("Failed to create engine\n");
        gs_cleanup();
        return 1;
    }
    
    // Create and register providers
    printf("2. Registering providers...\n");
    
    // Walking provider
    WalkingConfig walking_config = walking_config_default();
    walking_config.max_walking_distance = 800.0; // 800m max walk
    GraphserverResult result = gs_engine_register_provider(
        engine, "walking", walking_provider, &walking_config);
    if (result != GS_SUCCESS) {
        printf("Failed to register walking provider: %s\n", gs_get_error_message(result));
    } else {
        printf("   ✓ Walking provider registered\n");
    }
    
    // Transit provider
    TransitNetwork* transit_network = transit_network_create_example();
    if (transit_network) {
        result = gs_engine_register_provider(
            engine, "transit", transit_provider, transit_network);
        if (result != GS_SUCCESS) {
            printf("Failed to register transit provider: %s\n", gs_get_error_message(result));
        } else {
            printf("   ✓ Transit provider registered\n");
        }
    }
    
    // Road network provider (for cars)
    RoadNetwork* road_network = road_network_create_example("car");
    if (road_network) {
        result = gs_engine_register_provider(
            engine, "road", road_network_provider, road_network);
        if (result != GS_SUCCESS) {
            printf("Failed to register road network provider: %s\n", gs_get_error_message(result));
        } else {
            printf("   ✓ Road network provider registered\n");
        }
    }
    
    // Display registered providers
    GraphserverProviderInfo* provider_info;
    size_t provider_count;
    result = gs_engine_list_providers(engine, &provider_info, &provider_count);
    if (result == GS_SUCCESS) {
        printf("   Total providers registered: %zu\n\n", provider_count);
        free(provider_info);
    }
    
    // Plan a journey
    printf("3. Planning journey...\n");
    printf("   From: Financial District (40.7074, -74.0113)\n");
    printf("   To: Brooklyn Bridge area (40.7061, -73.9969)\n\n");
    
    // Create start vertex
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    if (!start) {
        printf("Failed to create start vertex\n");
        goto cleanup;
    }
    
    // Create goal predicate
    LocationGoal goal = {40.7061, -73.9969, 200.0}; // 200m radius around Brooklyn Bridge
    
    // Run the planner
    GraphserverPlanStats stats;
    clock_t start_time = clock();
    
    GraphserverPath* path = gs_plan_simple(
        engine, start, location_goal_predicate, &goal, &stats);
    
    clock_t end_time = clock();
    double planning_time = ((double)(end_time - start_time)) / CLOCKS_PER_SEC;
    
    // Display results
    printf("4. Planning results:\n");
    printf("   Planning time: %.3f seconds\n", planning_time);
    printf("   Vertices expanded: %zu\n", stats.vertices_expanded);
    printf("   Edges examined: %zu\n", stats.edges_generated);
    printf("   Memory used: %zu bytes\n\n", stats.peak_memory_usage);
    
    if (path) {
        printf("5. Route found:\n");
        print_path_details(path);
        gs_path_destroy(path);
    } else {
        printf("5. No route found.\n");
        printf("   This may be normal - the example network is simplified.\n");
        printf("   Try adjusting the goal location or provider parameters.\n\n");
    }
    
    // Demonstrate error handling
    printf("6. Testing error handling:\n");
    GraphserverPath* invalid_path = gs_plan_simple(NULL, start, location_goal_predicate, &goal, NULL);
    if (!invalid_path) {
        printf("   ✓ Correctly handled NULL engine parameter\n");
    }
    
    // Test with unreachable goal
    LocationGoal unreachable_goal = {50.0, 0.0, 100.0}; // Far away location
    GraphserverPath* no_path = gs_plan_simple(
        engine, start, location_goal_predicate, &unreachable_goal, NULL);
    if (!no_path) {
        printf("   ✓ Correctly handled unreachable destination\n");
    }
    
    printf("\n7. Example completed successfully!\n");
    printf("   This demonstrates basic usage of the Graphserver Planning Engine.\n");
    printf("   For more advanced features, see the integration tests and documentation.\n");

cleanup:
    // Clean up resources
    if (start) gs_vertex_destroy(start);
    if (transit_network) transit_network_destroy(transit_network);
    if (road_network) road_network_destroy(road_network);
    gs_engine_destroy(engine);
    gs_cleanup();
    
    return 0;
}