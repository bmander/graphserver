#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <time.h>

#include "../include/gs_engine.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"
#include "../include/gs_cache.h"

// Test provider for grid graph
typedef struct {
    int width;
    int height;
} GridData;

// Simple grid provider that generates edges to adjacent cells
static int grid_provider_generate_edges(
    const GraphserverVertex* vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    GridData* grid = (GridData*)user_data;
    if (!vertex || !out_edges || !grid) return -1;
    
    // Get vertex coordinates from vertex
    GraphserverValue x_val, y_val;
    if (gs_vertex_get_value(vertex, "x", &x_val) != GS_SUCCESS ||
        gs_vertex_get_value(vertex, "y", &y_val) != GS_SUCCESS) {
        return -1;
    }
    
    if (x_val.type != GS_VALUE_INT || y_val.type != GS_VALUE_INT) {
        return -1;
    }
    
    int x = (int)x_val.as.i_val;
    int y = (int)y_val.as.i_val;
    
    // Generate edges to adjacent cells (north, south, east, west)
    int dx[] = {0, 0, 1, -1};
    int dy[] = {1, -1, 0, 0};
    
    for (int i = 0; i < 4; i++) {
        int new_x = x + dx[i];
        int new_y = y + dy[i];
        
        // Check bounds
        if (new_x >= 0 && new_x < grid->width && new_y >= 0 && new_y < grid->height) {
            // Create target vertex
            GraphserverVertex* target = gs_vertex_create();
            if (!target) continue;
            
            gs_vertex_set_kv(target, "x", gs_value_create_int(new_x));
            gs_vertex_set_kv(target, "y", gs_value_create_int(new_y));
            
            // Create edge with cost 1.0
            double cost[] = {1.0};
            GraphserverEdge* edge = gs_edge_create(target, cost, 1);
            if (edge) {
                // Edge should own the target vertex since we created it for this edge
                gs_edge_set_owns_target_vertex(edge, true);
                gs_edge_list_add_edge(out_edges, edge);
            } else {
                gs_vertex_destroy(target);
            }
        }
    }
    
    return 0; // Success
}

// Helper function to create a grid vertex
static GraphserverVertex* create_grid_vertex(int x, int y) {
    GraphserverVertex* vertex = gs_vertex_create();
    if (!vertex) return NULL;
    
    gs_vertex_set_kv(vertex, "x", gs_value_create_int(x));
    gs_vertex_set_kv(vertex, "y", gs_value_create_int(y));
    
    return vertex;
}

// Test basic precaching functionality
static void test_basic_precaching(void) {
    printf("Testing basic precaching functionality...\n");
    
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    assert(engine != NULL);
    
    // Create grid provider (5x5 grid)
    GridData grid_data = {5, 5};
    GraphserverResult result = gs_engine_register_provider(
        engine, "grid", grid_provider_generate_edges, &grid_data);
    assert(result == GS_SUCCESS);
    
    // Create seed vertex at (0,0)
    GraphserverVertex* seed = create_grid_vertex(0, 0);
    assert(seed != NULL);
    
    GraphserverVertex* seeds[] = {seed};
    
    // Test precaching with depth limit
    result = gs_engine_precache_subgraph(engine, "grid", seeds, 1, 2, 0);
    assert(result == GS_SUCCESS);
    
    // Cleanup
    gs_vertex_destroy(seed);
    gs_engine_destroy(engine);
    
    printf("Basic precaching test passed!\n");
}

// Test precaching with multiple seeds
static void test_multiple_seeds(void) {
    printf("Testing precaching with multiple seeds...\n");
    
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    assert(engine != NULL);
    
    // Create grid provider (10x10 grid)
    GridData grid_data = {10, 10};
    GraphserverResult result = gs_engine_register_provider(
        engine, "grid", grid_provider_generate_edges, &grid_data);
    assert(result == GS_SUCCESS);
    
    // Create multiple seed vertices
    GraphserverVertex* seed1 = create_grid_vertex(0, 0);
    GraphserverVertex* seed2 = create_grid_vertex(9, 9);
    GraphserverVertex* seed3 = create_grid_vertex(5, 5);
    assert(seed1 != NULL && seed2 != NULL && seed3 != NULL);
    
    GraphserverVertex* seeds[] = {seed1, seed2, seed3};
    
    // Test precaching with multiple seeds
    result = gs_engine_precache_subgraph(engine, "grid", seeds, 3, 3, 0);
    assert(result == GS_SUCCESS);
    
    // Cleanup
    gs_vertex_destroy(seed1);
    gs_vertex_destroy(seed2);
    gs_vertex_destroy(seed3);
    gs_engine_destroy(engine);
    
    printf("Multiple seeds test passed!\n");
}

// Test precaching with vertex limit
static void test_vertex_limit(void) {
    printf("Testing precaching with vertex limit...\n");
    
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    assert(engine != NULL);
    
    // Create grid provider (10x10 grid)
    GridData grid_data = {10, 10};
    GraphserverResult result = gs_engine_register_provider(
        engine, "grid", grid_provider_generate_edges, &grid_data);
    assert(result == GS_SUCCESS);
    
    // Create seed vertex at center
    GraphserverVertex* seed = create_grid_vertex(5, 5);
    assert(seed != NULL);
    
    GraphserverVertex* seeds[] = {seed};
    
    // Test precaching with vertex limit of 10
    result = gs_engine_precache_subgraph(engine, "grid", seeds, 1, 0, 10);
    assert(result == GS_SUCCESS);
    
    // Cleanup
    gs_vertex_destroy(seed);
    gs_engine_destroy(engine);
    
    printf("Vertex limit test passed!\n");
}

// Test error conditions
static void test_error_conditions(void) {
    printf("Testing error conditions...\n");
    
    // Create engine with caching disabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = false;
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    assert(engine != NULL);
    
    // Test with caching disabled
    GraphserverVertex* seed = create_grid_vertex(0, 0);
    GraphserverVertex* seeds[] = {seed};
    
    GraphserverResult result = gs_engine_precache_subgraph(engine, "nonexistent", seeds, 1, 2, 0);
    assert(result != GS_SUCCESS); // Should fail - caching disabled
    
    gs_vertex_destroy(seed);
    gs_engine_destroy(engine);
    
    // Test with NULL parameters
    result = gs_engine_precache_subgraph(NULL, "test", NULL, 0, 0, 0);
    assert(result == GS_ERROR_NULL_POINTER);
    
    printf("Error conditions test passed!\n");
}

// Test performance comparison (basic)
static void test_performance_comparison(void) {
    printf("Testing basic performance comparison...\n");
    
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    assert(engine != NULL);
    
    // Create grid provider (20x20 grid)
    GridData grid_data = {20, 20};
    GraphserverResult result = gs_engine_register_provider(
        engine, "grid", grid_provider_generate_edges, &grid_data);
    assert(result == GS_SUCCESS);
    
    // Create seed vertex
    GraphserverVertex* seed = create_grid_vertex(10, 10);
    assert(seed != NULL);
    
    GraphserverVertex* seeds[] = {seed};
    
    // Measure precaching time
    clock_t start = clock();
    result = gs_engine_precache_subgraph(engine, "grid", seeds, 1, 5, 0);
    clock_t end = clock();
    
    assert(result == GS_SUCCESS);
    
    double precache_time = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Precaching took: %f seconds\n", precache_time);
    
    // Test vertex expansion (should use cached edges)
    GraphserverEdgeList* edges = gs_edge_list_create();
    assert(edges != NULL);
    
    // Set edge list to own edges so they get properly cleaned up
    gs_edge_list_set_owns_edges(edges, true);
    
    start = clock();
    result = gs_engine_expand_vertex(engine, seed, edges);
    end = clock();
    
    assert(result == GS_SUCCESS);
    
    double expand_time = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("Vertex expansion took: %f seconds\n", expand_time);
    
    size_t edge_count = gs_edge_list_get_count(edges);
    printf("Generated %zu edges\n", edge_count);
    
    // Cleanup
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(seed);
    gs_engine_destroy(engine);
    
    printf("Performance comparison test passed!\n");
}

int main(void) {
    printf("Running precaching tests...\n");
    
    test_basic_precaching();
    test_multiple_seeds();
    test_vertex_limit();
    test_error_conditions();
    test_performance_comparison();
    
    printf("All precaching tests passed!\n");
    return 0;
}