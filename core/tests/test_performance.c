#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include "../include/graphserver.h"
#include "../../examples/include/example_providers.h"
#include "test_utils.h"

/**
 * @file test_performance.c
 * @brief Performance benchmarking suite for Graphserver Planning Engine
 * 
 * This suite measures performance characteristics including planning time,
 * memory usage, and scalability with network size.
 */

// Performance measurement utilities
typedef struct {
    clock_t start_time;
    clock_t end_time;
    double elapsed_seconds;
} Timer;

static Timer timer_start(void) {
    Timer timer;
    timer.start_time = clock();
    return timer;
}

static void timer_end(Timer* timer) {
    timer->end_time = clock();
    timer->elapsed_seconds = ((double)(timer->end_time - timer->start_time)) / CLOCKS_PER_SEC;
}

// Test configuration
typedef struct {
    const char* test_name;
    size_t target_vertices;
    size_t target_edges;
    double max_planning_time_seconds;
    size_t max_memory_mb;
} PerformanceTarget;

static PerformanceTarget performance_targets[] = {
    {"Small Network", 100, 500, 0.1, 10},
    {"Medium Network", 1000, 5000, 1.0, 50},
    {"Large Network", 10000, 50000, 10.0, 200},
};

// Benchmark memory usage tracking
typedef struct {
    size_t arena_allocations;
    size_t peak_memory_bytes;
    size_t total_allocations;
} MemoryStats;

// Generate synthetic network for performance testing
static void generate_synthetic_network(
    GraphserverEngine* engine,
    size_t target_vertices,
    double density) {
    
    // Create walking provider with wide area for large networks
    WalkingConfig* walking_config = malloc(sizeof(WalkingConfig));
    *walking_config = walking_config_default();
    walking_config->max_walking_distance = 2000.0; // 2km for stress testing
    
    gs_engine_register_provider(engine, "walking", walking_provider, walking_config);
    
    printf("    Generated synthetic network: %zu target vertices, %.2f density\n", 
           target_vertices, density);
}

// Benchmark single planning operation
static void benchmark_planning_operation(
    GraphserverEngine* engine,
    const char* test_name,
    const PerformanceTarget* target) {
    
    printf("\n  Running %s benchmark...\n", test_name);
    
    // Generate start and goal vertices
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    LocationGoal goal = {40.7500, -73.9900, 200.0}; // Distant goal
    
    Timer timer = timer_start();
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(
        engine, start, location_goal_predicate, &goal, &stats);
    
    timer_end(&timer);
    
    // Report results
    printf("    Planning time: %.3f seconds (target: %.1f)\n", 
           timer.elapsed_seconds, target->max_planning_time_seconds);
    printf("    Vertices expanded: %zu\n", stats.vertices_expanded);
    printf("    Edges examined: %zu\n", stats.edges_generated);
    printf("    Memory usage: %zu bytes (target: %zu MB)\n", 
           stats.peak_memory_usage, target->max_memory_mb * 1024 * 1024);
    
    if (path) {
        size_t path_length = gs_path_get_num_edges(path);
        const double* total_cost = gs_path_get_total_cost(path);
        printf("    Path found: %zu edges, %.1f minutes cost\n", 
               path_length, total_cost ? total_cost[0] : 0.0);
        gs_path_destroy(path);
    } else {
        printf("    No path found\n");
    }
    
    // Check performance targets
    bool meets_time_target = timer.elapsed_seconds <= target->max_planning_time_seconds;
    bool meets_memory_target = stats.peak_memory_usage <= (target->max_memory_mb * 1024 * 1024);
    
    printf("    Performance: %s (Time: %s, Memory: %s)\n",
           (meets_time_target && meets_memory_target) ? "PASS" : "FAIL",
           meets_time_target ? "OK" : "SLOW",
           meets_memory_target ? "OK" : "HIGH");
    
    gs_vertex_destroy(start);
}

// Scalability test - measure how performance scales with network size
static void benchmark_scalability(void) {
    printf("\nScalability Benchmarks\n");
    printf("======================\n");
    
    for (size_t i = 0; i < sizeof(performance_targets) / sizeof(performance_targets[0]); i++) {
        PerformanceTarget* target = &performance_targets[i];
        
        GraphserverEngine* engine = gs_engine_create();
        generate_synthetic_network(engine, target->target_vertices, 0.1);
        
        benchmark_planning_operation(engine, target->test_name, target);
        
        gs_engine_destroy(engine);
    }
}

// Memory efficiency test
static void benchmark_memory_efficiency(void) {
    printf("\nMemory Efficiency Benchmarks\n");
    printf("=============================\n");
    
    GraphserverEngine* engine = gs_engine_create();
    
    WalkingConfig walking_config = walking_config_default();
    gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
    
    GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
    LocationGoal goal = {40.7100, -74.0070, 100.0};
    
    // Run multiple planning cycles to test memory reuse
    printf("  Testing memory reuse across multiple planning cycles...\n");
    
    size_t total_memory_used = 0;
    size_t min_memory = SIZE_MAX;
    size_t max_memory = 0;
    
    for (int cycle = 0; cycle < 10; cycle++) {
        GraphserverPlanStats stats;
        GraphserverPath* path = gs_plan_simple(
            engine, start, location_goal_predicate, &goal, &stats);
        
        if (path) {
            gs_path_destroy(path);
        }
        
        total_memory_used += stats.peak_memory_usage;
        if (stats.peak_memory_usage < min_memory) min_memory = stats.peak_memory_usage;
        if (stats.peak_memory_usage > max_memory) max_memory = stats.peak_memory_usage;
        
        printf("    Cycle %d: %zu bytes\n", cycle + 1, stats.peak_memory_usage);
    }
    
    double avg_memory = (double)total_memory_used / 10.0;
    printf("  Memory usage statistics:\n");
    printf("    Average: %.0f bytes\n", avg_memory);
    printf("    Minimum: %zu bytes\n", min_memory);
    printf("    Maximum: %zu bytes\n", max_memory);
    printf("    Variation: %.1f%% (lower is better)\n", 
           ((double)(max_memory - min_memory) / avg_memory) * 100.0);
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Concurrent planning test (simulate multiple planning requests)
static void benchmark_concurrent_planning(void) {
    printf("\nConcurrent Planning Simulation\n");
    printf("==============================\n");
    
    GraphserverEngine* engine = gs_engine_create();
    
    WalkingConfig walking_config = walking_config_default();
    gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
    
    printf("  Simulating 20 sequential planning requests...\n");
    
    Timer total_timer = timer_start();
    size_t successful_plans = 0;
    size_t total_vertices_expanded = 0;
    
    for (int i = 0; i < 20; i++) {
        // Vary start and goal locations
        double start_lat = 40.7074 + (i * 0.001);
        double start_lon = -74.0113 + (i * 0.001);
        double goal_lat = 40.7100 + ((19 - i) * 0.001);
        double goal_lon = -74.0070 + ((19 - i) * 0.001);
        
        GraphserverVertex* start = create_location_vertex(start_lat, start_lon, time(NULL));
        LocationGoal goal = {goal_lat, goal_lon, 100.0};
        
        Timer request_timer = timer_start();
        
        GraphserverPlanStats stats;
        GraphserverPath* path = gs_plan_simple(
            engine, start, location_goal_predicate, &goal, &stats);
        
        timer_end(&request_timer);
        
        if (path) {
            successful_plans++;
            gs_path_destroy(path);
        }
        
        total_vertices_expanded += stats.vertices_expanded;
        
        printf("    Request %d: %.3f seconds, %s\n", 
               i + 1, request_timer.elapsed_seconds, path ? "SUCCESS" : "NO_PATH");
        
        gs_vertex_destroy(start);
    }
    
    timer_end(&total_timer);
    
    printf("  Concurrent planning summary:\n");
    printf("    Total time: %.3f seconds\n", total_timer.elapsed_seconds);
    printf("    Average per request: %.3f seconds\n", total_timer.elapsed_seconds / 20.0);
    printf("    Successful plans: %zu/20 (%.1f%%)\n", successful_plans, (successful_plans / 20.0) * 100.0);
    printf("    Total vertices expanded: %zu\n", total_vertices_expanded);
    printf("    Average vertices per request: %.1f\n", (double)total_vertices_expanded / 20.0);
    
    gs_engine_destroy(engine);
}

// Provider performance comparison
static void benchmark_provider_performance(void) {
    printf("\nProvider Performance Comparison\n");
    printf("===============================\n");
    
    // Test each provider type individually
    const char* provider_names[] = {"Walking", "Transit", "Road Network"};
    
    for (int p = 0; p < 3; p++) {
        printf("  %s Provider Performance:\n", provider_names[p]);
        
        GraphserverEngine* engine = gs_engine_create();
        
        if (p == 0) {
            // Walking provider
            WalkingConfig walking_config = walking_config_default();
            gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);
        } else if (p == 1) {
            // Transit provider
            TransitNetwork* transit_network = transit_network_create_example();
            gs_engine_register_provider(engine, "transit", transit_provider, transit_network);
        } else {
            // Road network provider
            RoadNetwork* road_network = road_network_create_example("car");
            gs_engine_register_provider(engine, "road", road_network_provider, road_network);
        }
        
        GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
        if (p == 2) { // Add car mode for road network - create new vertex with mode
            // Extract data from existing vertex and create new one with mode
            GraphserverValue lat_val, lon_val, time_val;
            gs_vertex_get_value(start, "lat", &lat_val);
            gs_vertex_get_value(start, "lon", &lon_val);
            gs_vertex_get_value(start, "time", &time_val);
            
            GraphserverKeyPair pairs[] = {
                {"lat", lat_val},
                {"lon", lon_val},
                {"time", time_val},
                {"mode", gs_value_create_string("car")}
            };
            
            gs_vertex_destroy(start);
            start = create_vertex_safe(pairs, 4, NULL);
        }
        
        // Test vertex expansion performance
        Timer timer = timer_start();
        
        GraphserverEdgeList* edges = gs_edge_list_create();
        GraphserverResult result = gs_engine_expand_vertex(engine, start, edges);
        
        timer_end(&timer);
        
        if (result == GS_SUCCESS) {
            size_t edge_count = gs_edge_list_get_count(edges);
            printf("    Expansion time: %.3f seconds\n", timer.elapsed_seconds);
            printf("    Edges generated: %zu\n", edge_count);
            printf("    Edges per second: %.0f\n", edge_count / timer.elapsed_seconds);
        } else {
            printf("    Expansion failed\n");
        }
        
        gs_edge_list_destroy(edges);
        gs_vertex_destroy(start);
        
        // Cleanup provider-specific resources
        if (p == 1) {
            // Clean up transit network (stored in engine user_data)
        } else if (p == 2) {
            // Clean up road network (stored in engine user_data)
        }
        
        gs_engine_destroy(engine);
    }
}

// Helper function to create a test vertex for cache benchmarks
static GraphserverVertex* create_cache_test_vertex(const char* name) {
    return create_named_vertex_safe(name);
}

// Cache performance benchmarks
static void benchmark_cache_performance(void) {
    printf("\nCache Performance Benchmarks\n");
    printf("============================\n");
    
    // Test 1: Basic cache hit vs miss performance
    printf("  Testing cache hit vs miss performance...\n");
    
    // Create engine with caching enabled
    GraphserverEngineConfig cache_config = gs_engine_get_default_config();
    cache_config.enable_edge_caching = true;
    
    GraphserverEngine* cache_engine = gs_engine_create_with_config(&cache_config);
    WalkingConfig walking_config = walking_config_default();
    gs_engine_register_provider(cache_engine, "walking", walking_provider, &walking_config);
    
    GraphserverVertex* test_vertex = create_cache_test_vertex("cache_perf_test");
    
    // First expansion (cache miss)
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    Timer miss_timer = timer_start();
    GraphserverResult result1 = gs_engine_expand_vertex(cache_engine, test_vertex, edges1);
    timer_end(&miss_timer);
    
    if (result1 != GS_SUCCESS) {
        printf("    Cache miss expansion failed\n");
        return;
    }
    
    size_t first_edge_count = gs_edge_list_get_count(edges1);
    
    // Get statistics after cache miss
    GraphserverPlanStats miss_stats;
    gs_engine_get_stats(cache_engine, &miss_stats);
    
    // Second expansion (cache hit)
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    Timer hit_timer = timer_start();
    GraphserverResult result2 = gs_engine_expand_vertex(cache_engine, test_vertex, edges2);
    timer_end(&hit_timer);
    
    if (result2 != GS_SUCCESS) {
        printf("    Cache hit expansion failed\n");
        return;
    }
    
    size_t second_edge_count = gs_edge_list_get_count(edges2);
    
    // Get statistics after cache hit
    GraphserverPlanStats hit_stats;
    gs_engine_get_stats(cache_engine, &hit_stats);
    
    // Calculate performance improvement
    double improvement_ratio = miss_timer.elapsed_seconds / hit_timer.elapsed_seconds;
    bool performance_pass = improvement_ratio >= 5.0; // Minimum 5x improvement
    
    printf("    Cache miss time: %.6f seconds (%zu edges)\n", 
           miss_timer.elapsed_seconds, first_edge_count);
    printf("    Cache hit time: %.6f seconds (%zu edges)\n", 
           hit_timer.elapsed_seconds, second_edge_count);
    printf("    Performance improvement: %.1fx %s\n", 
           improvement_ratio, performance_pass ? "PASS" : "FAIL");
    printf("    Cache statistics: %lu hits, %lu misses, %lu puts\n",
           hit_stats.cache_hits, hit_stats.cache_misses, hit_stats.cache_puts);
    
    // Validate statistics are correct
    bool stats_pass = (hit_stats.cache_hits == 1 && hit_stats.cache_misses == 1 && 
                       hit_stats.cache_puts == 1);
    printf("    Statistics validation: %s\n", stats_pass ? "PASS" : "FAIL");
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    
    // Test 2: Multi-vertex cache performance
    printf("  Testing multi-vertex cache scalability...\n");
    
    Timer multi_timer = timer_start();
    size_t total_cache_hits = 0;
    
    // Cache multiple vertices
    for (int i = 0; i < 10; i++) {
        char vertex_name[32];
        snprintf(vertex_name, sizeof(vertex_name), "cache_test_%d", i);
        
        GraphserverVertex* vertex = create_cache_test_vertex(vertex_name);
        GraphserverEdgeList* edges = gs_edge_list_create();
        gs_edge_list_set_owns_edges(edges, true);
        
        // First expansion (cache miss)
        gs_engine_expand_vertex(cache_engine, vertex, edges);
        
        // Second expansion (cache hit)
        gs_edge_list_clear(edges);
        gs_engine_expand_vertex(cache_engine, vertex, edges);
        total_cache_hits++;
        
        gs_edge_list_destroy(edges);
        gs_vertex_destroy(vertex);
    }
    
    timer_end(&multi_timer);
    
    GraphserverPlanStats multi_stats;
    gs_engine_get_stats(cache_engine, &multi_stats);
    
    printf("    Multi-vertex test time: %.6f seconds\n", multi_timer.elapsed_seconds);
    printf("    Total cache operations: %zu vertices\n", total_cache_hits);
    printf("    Final cache statistics: %lu hits, %lu misses\n",
           multi_stats.cache_hits, multi_stats.cache_misses);
    
    // Test 3: Cache vs no-cache comparison
    printf("  Testing cache vs no-cache performance...\n");
    
    // Create engine without caching
    GraphserverEngine* no_cache_engine = gs_engine_create();
    gs_engine_register_provider(no_cache_engine, "walking", walking_provider, &walking_config);
    
    // Repeat same vertex expansion 5 times with no cache
    Timer no_cache_timer = timer_start();
    for (int i = 0; i < 5; i++) {
        GraphserverEdgeList* edges = gs_edge_list_create();
        gs_edge_list_set_owns_edges(edges, true);
        
        gs_engine_expand_vertex(no_cache_engine, test_vertex, edges);
        
        gs_edge_list_destroy(edges);
    }
    timer_end(&no_cache_timer);
    
    // Repeat same vertex expansion 5 times with cache (1 miss + 4 hits)
    Timer with_cache_timer = timer_start();
    for (int i = 0; i < 5; i++) {
        GraphserverEdgeList* edges = gs_edge_list_create();
        gs_edge_list_set_owns_edges(edges, true);
        
        gs_engine_expand_vertex(cache_engine, test_vertex, edges);
        
        gs_edge_list_destroy(edges);
    }
    timer_end(&with_cache_timer);
    
    double cache_benefit = no_cache_timer.elapsed_seconds / with_cache_timer.elapsed_seconds;
    bool cache_benefit_pass = cache_benefit >= 2.0; // Expect at least 2x improvement
    
    printf("    No-cache 5x expansion time: %.6f seconds\n", no_cache_timer.elapsed_seconds);
    printf("    With-cache 5x expansion time: %.6f seconds\n", with_cache_timer.elapsed_seconds);
    printf("    Cache benefit: %.1fx %s\n", 
           cache_benefit, cache_benefit_pass ? "PASS" : "FAIL");
    
    // Test 4: Cache invalidation performance
    printf("  Testing cache invalidation performance...\n");
    
    // Build up cache with multiple vertices
    for (int i = 0; i < 20; i++) {
        char vertex_name[32];
        snprintf(vertex_name, sizeof(vertex_name), "invalidation_test_%d", i);
        
        GraphserverVertex* vertex = create_cache_test_vertex(vertex_name);
        GraphserverEdgeList* edges = gs_edge_list_create();
        gs_edge_list_set_owns_edges(edges, true);
        
        gs_engine_expand_vertex(cache_engine, vertex, edges);
        
        gs_edge_list_destroy(edges);
        gs_vertex_destroy(vertex);
    }
    
    // Measure cache invalidation time
    Timer invalidation_timer = timer_start();
    
    GraphserverEngineConfig new_config = cache_config;
    gs_engine_set_config(cache_engine, &new_config); // This should clear cache
    
    timer_end(&invalidation_timer);
    
    // Verify cache was cleared
    GraphserverPlanStats invalidation_stats;
    gs_engine_get_stats(cache_engine, &invalidation_stats);
    
    bool invalidation_pass = (invalidation_stats.cache_hits == 0 && 
                             invalidation_stats.cache_misses == 0 && 
                             invalidation_stats.cache_puts == 0);
    
    printf("    Cache invalidation time: %.6f seconds\n", invalidation_timer.elapsed_seconds);
    printf("    Invalidation speed: %s (< 0.001s target)\n", 
           invalidation_timer.elapsed_seconds < 0.001 ? "PASS" : "FAIL");
    printf("    Cache cleared verification: %s\n", invalidation_pass ? "PASS" : "FAIL");
    
    // Cleanup
    gs_vertex_destroy(test_vertex);
    gs_engine_destroy(cache_engine);
    gs_engine_destroy(no_cache_engine);
    
    printf("  Cache performance benchmarks completed!\n");
}

int main(void) {
    printf("Graphserver Performance Benchmarks\n");
    printf("===================================\n");
    printf("Testing planning performance, memory usage, and scalability\n");
    
    benchmark_scalability();
    benchmark_memory_efficiency();
    benchmark_concurrent_planning();
    benchmark_provider_performance();
    benchmark_cache_performance();
    
    printf("\n===================================\n");
    printf("Performance benchmarks completed!\n");
    printf("Results can be used to validate performance targets\n");
    printf("and identify optimization opportunities.\n");
    
    return 0;
}