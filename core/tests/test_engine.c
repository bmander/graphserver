#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/graphserver.h"
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

#define ASSERT_STR_EQ(expected, actual) \
    do { \
        if (strcmp((expected), (actual)) != 0) { \
            printf("FAILED\n  Expected '%s', got '%s' (line %d)\n", (expected), (actual), __LINE__); \
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

// Mock edge provider that generates simple edges
static int mock_provider_simple(const GraphserverVertex* current_vertex,
                                GraphserverEdgeList* out_edges,
                                void* user_data) {
    (void)current_vertex; // Unused
    (void)user_data; // Unused
    
    // Create a simple target vertex
    GraphserverVertex* target = create_named_vertex_safe("target");
    if (!target) return -1;
    
    // Create an edge with distance 1.0
    double distance = 1.0;
    GraphserverEdge* edge = gs_edge_create(target, &distance, 1);
    if (!edge) {
        gs_vertex_destroy(target);
        return -1;
    }
    
    // Set edge to own the target vertex since we created it specifically for this edge
    gs_edge_set_owns_target_vertex(edge, true);
    
    // Add to output list
    GraphserverResult result = gs_edge_list_add_edge(out_edges, edge);
    return (result == GS_SUCCESS) ? 0 : -1;
}

// Mock provider that generates multiple edges
static int mock_provider_multiple(const GraphserverVertex* current_vertex,
                                  GraphserverEdgeList* out_edges,
                                  void* user_data) {
    (void)current_vertex; // Unused
    int* num_edges = (int*)user_data;
    int edges_to_create = num_edges ? *num_edges : 3;
    
    for (int i = 0; i < edges_to_create; i++) {
        char name[32];
        snprintf(name, sizeof(name), "target_%d", i);
        
        GraphserverVertex* target = create_named_vertex_safe(name);
        if (!target) return -1;
        
        double distance = (double)(i + 1);
        GraphserverEdge* edge = gs_edge_create(target, &distance, 1);
        if (!edge) {
            gs_vertex_destroy(target);
            return -1;
        }
        
        // Set edge to own the target vertex since we created it specifically for this edge
        gs_edge_set_owns_target_vertex(edge, true);
        
        gs_edge_list_add_edge(out_edges, edge);
    }
    
    return 0;
}

// Mock provider that always fails
static int mock_provider_failing(const GraphserverVertex* current_vertex,
                                 GraphserverEdgeList* out_edges,
                                 void* user_data) {
    (void)current_vertex;
    (void)out_edges;
    (void)user_data;
    return -1; // Always fail
}

// Helper function to create a test vertex
GraphserverVertex* create_test_vertex(const char* name) {
    return create_named_vertex_safe(name);
}

// Simple goal predicate that's never satisfied (for testing)
static bool never_satisfied_goal(const GraphserverVertex* vertex, void* user_data) {
    (void)vertex; (void)user_data;
    return false; // Never satisfied
}

// Test engine creation and destruction
TEST(engine_lifecycle) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    ASSERT_EQ(0, gs_engine_get_provider_count(engine));
    
    gs_engine_destroy(engine);
    // Should not crash
}

// Test engine creation with custom config
TEST(engine_custom_config) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.default_arena_size = 2048;
    config.default_timeout_seconds = 60.0;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    GraphserverEngineConfig retrieved_config;
    GraphserverResult result = gs_engine_get_config(engine, &retrieved_config);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2048, retrieved_config.default_arena_size);
    
    gs_engine_destroy(engine);
}

// Test provider registration
TEST(engine_provider_registration) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register a provider
    GraphserverResult result = gs_engine_register_provider(
        engine, "test_provider", mock_provider_simple, NULL);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_engine_get_provider_count(engine));
    
    // Check if provider exists
    ASSERT(gs_engine_has_provider(engine, "test_provider"));
    ASSERT(!gs_engine_has_provider(engine, "nonexistent"));
    
    // Try to register same provider again (should fail)
    result = gs_engine_register_provider(
        engine, "test_provider", mock_provider_simple, NULL);
    ASSERT_EQ(GS_ERROR_INVALID_ARGUMENT, result);
    
    // Register another provider
    result = gs_engine_register_provider(
        engine, "second_provider", mock_provider_multiple, NULL);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2, gs_engine_get_provider_count(engine));
    
    gs_engine_destroy(engine);
}

// Test provider unregistration
TEST(engine_provider_unregistration) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register providers
    gs_engine_register_provider(engine, "provider1", mock_provider_simple, NULL);
    gs_engine_register_provider(engine, "provider2", mock_provider_multiple, NULL);
    ASSERT_EQ(2, gs_engine_get_provider_count(engine));
    
    // Unregister one
    GraphserverResult result = gs_engine_unregister_provider(engine, "provider1");
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_engine_get_provider_count(engine));
    ASSERT(!gs_engine_has_provider(engine, "provider1"));
    ASSERT(gs_engine_has_provider(engine, "provider2"));
    
    // Try to unregister non-existent provider
    result = gs_engine_unregister_provider(engine, "nonexistent");
    ASSERT_EQ(GS_ERROR_KEY_NOT_FOUND, result);
    
    gs_engine_destroy(engine);
}

// Test provider enable/disable
TEST(engine_provider_enable_disable) {
    GraphserverEngine* engine = gs_engine_create();
    
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    // Disable provider
    GraphserverResult result = gs_engine_set_provider_enabled(engine, "test_provider", false);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Enable provider
    result = gs_engine_set_provider_enabled(engine, "test_provider", true);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Try with non-existent provider
    result = gs_engine_set_provider_enabled(engine, "nonexistent", true);
    ASSERT_EQ(GS_ERROR_KEY_NOT_FOUND, result);
    
    gs_engine_destroy(engine);
}

// Test provider listing
TEST(engine_provider_listing) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Empty engine
    GraphserverProviderInfo* providers;
    size_t count;
    GraphserverResult result = gs_engine_list_providers(engine, &providers, &count);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(0, count);
    ASSERT_NULL(providers);
    
    // Add some providers
    int user_data = 5;
    gs_engine_register_provider(engine, "provider1", mock_provider_simple, NULL);
    gs_engine_register_provider(engine, "provider2", mock_provider_multiple, &user_data);
    
    result = gs_engine_list_providers(engine, &providers, &count);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2, count);
    ASSERT_NOT_NULL(providers);
    
    // Check provider details
    bool found_provider1 = false, found_provider2 = false;
    for (size_t i = 0; i < count; i++) {
        if (strcmp(providers[i].name, "provider1") == 0) {
            found_provider1 = true;
            ASSERT_EQ(mock_provider_simple, providers[i].generator);
            ASSERT_NULL(providers[i].user_data);
            ASSERT(providers[i].is_enabled);
        } else if (strcmp(providers[i].name, "provider2") == 0) {
            found_provider2 = true;
            ASSERT_EQ(mock_provider_multiple, providers[i].generator);
            ASSERT_EQ(&user_data, providers[i].user_data);
            ASSERT(providers[i].is_enabled);
        }
    }
    
    ASSERT(found_provider1);
    ASSERT(found_provider2);
    
    free(providers);
    gs_engine_destroy(engine);
}

// Test vertex expansion
TEST(engine_vertex_expansion) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register a provider
    gs_engine_register_provider(engine, "simple_provider", mock_provider_simple, NULL);
    
    // Create test vertex
    GraphserverVertex* vertex = create_test_vertex("start");
    
    // Create edge list for output
    GraphserverEdgeList* edges = gs_edge_list_create();
    ASSERT_NOT_NULL(edges);
    
    // Set edge list to own its edges since providers create transient edges
    gs_edge_list_set_owns_edges(edges, true);
    
    // Expand vertex
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should have one edge
    ASSERT_EQ(1, gs_edge_list_get_count(edges));
    
    GraphserverEdge* edge;
    result = gs_edge_list_get_edge(edges, 0, &edge);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(edge);
    
    // Check edge properties
    ASSERT_EQ(1, gs_edge_get_distance_vector_size(edge));
    const double* dist = gs_edge_get_distance_vector(edge);
    ASSERT_NOT_NULL(dist);
    ASSERT_EQ(1.0, dist[0]);
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test expansion with multiple providers
TEST(engine_multiple_provider_expansion) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register multiple providers
    int num_edges = 2;
    gs_engine_register_provider(engine, "simple_provider", mock_provider_simple, NULL);
    gs_engine_register_provider(engine, "multiple_provider", mock_provider_multiple, &num_edges);
    
    GraphserverVertex* vertex = create_test_vertex("start");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should have edges from both providers (1 + 2 = 3)
    ASSERT_EQ(3, gs_edge_list_get_count(edges));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test expansion with disabled provider
TEST(engine_disabled_provider_expansion) {
    GraphserverEngine* engine = gs_engine_create();
    
    gs_engine_register_provider(engine, "provider1", mock_provider_simple, NULL);
    gs_engine_register_provider(engine, "provider2", mock_provider_simple, NULL);
    
    // Disable one provider
    gs_engine_set_provider_enabled(engine, "provider1", false);
    
    GraphserverVertex* vertex = create_test_vertex("start");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should only have edges from enabled provider
    ASSERT_EQ(1, gs_edge_list_get_count(edges));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test expansion with failing provider
TEST(engine_failing_provider_expansion) {
    GraphserverEngine* engine = gs_engine_create();
    
    gs_engine_register_provider(engine, "good_provider", mock_provider_simple, NULL);
    gs_engine_register_provider(engine, "bad_provider", mock_provider_failing, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("start");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result); // Should still succeed overall
    
    // Should have edge from good provider only
    ASSERT_EQ(1, gs_edge_list_get_count(edges));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test basic planning (placeholder implementation)
TEST(engine_basic_planning) {
    GraphserverEngine* engine = gs_engine_create();
    
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* start = create_test_vertex("start");
    
    GraphserverPlanStats stats;
    GraphserverPath* path = gs_plan_simple(engine, start, never_satisfied_goal, NULL, &stats);
    
    // Since goal is never satisfied, should return NULL
    ASSERT_NULL(path);
    
    gs_vertex_destroy(start);
    gs_engine_destroy(engine);
}

// Test error conditions
TEST(engine_error_conditions) {
    // NULL pointer checks
    ASSERT_NULL(gs_engine_create_with_config(NULL));
    
    GraphserverEngine* engine = gs_engine_create();
    
    // Provider registration with NULL
    ASSERT_EQ(GS_ERROR_NULL_POINTER, 
              gs_engine_register_provider(NULL, "test", mock_provider_simple, NULL));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, 
              gs_engine_register_provider(engine, NULL, mock_provider_simple, NULL));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, 
              gs_engine_register_provider(engine, "test", NULL, NULL));
    
    // Vertex expansion with NULL
    GraphserverVertex* vertex = create_test_vertex("test");
    GraphserverEdgeList* edges = gs_edge_list_create();
    
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_engine_expand_vertex(NULL, vertex, edges));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_engine_expand_vertex(engine, NULL, edges));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_engine_expand_vertex(engine, vertex, NULL));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test edge cache configuration
TEST(engine_cache_configuration) {
    // Test engine with caching disabled (default)
    GraphserverEngine* engine1 = gs_engine_create();
    ASSERT_NOT_NULL(engine1);
    
    GraphserverEngineConfig config1;
    GraphserverResult result = gs_engine_get_config(engine1, &config1);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(!config1.enable_edge_caching); // Should be disabled by default
    
    gs_engine_destroy(engine1);
    
    // Test engine with caching enabled
    GraphserverEngineConfig config2 = gs_engine_get_default_config();
    config2.enable_edge_caching = true;
    
    GraphserverEngine* engine2 = gs_engine_create_with_config(&config2);
    ASSERT_NOT_NULL(engine2);
    
    GraphserverEngineConfig retrieved_config;
    result = gs_engine_get_config(engine2, &retrieved_config);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(retrieved_config.enable_edge_caching); // Should be enabled
    
    gs_engine_destroy(engine2);
}

// Test cache creation and destruction
TEST(engine_cache_lifecycle) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    // Engine should be created successfully with cache enabled
    GraphserverEngineConfig retrieved_config;
    GraphserverResult result = gs_engine_get_config(engine, &retrieved_config);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(retrieved_config.enable_edge_caching);
    
    // Engine destruction should clean up cache without errors
    gs_engine_destroy(engine);
}

// Test cache hit performance and behavior
TEST(engine_cache_hit_performance) {
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    // Register a provider
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    ASSERT_NOT_NULL(vertex);
    
    // First expansion - should be a cache miss
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result1 = gs_engine_expand_vertex(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result1);
    
    size_t first_edge_count = gs_edge_list_get_count(edges1);
    ASSERT(first_edge_count > 0); // Should have generated some edges
    
    // Verify cache miss statistics
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_puts);
    ASSERT_EQ(1U, stats.providers_called);
    
    // Second expansion of same vertex - should be a cache hit
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    // Reset providers_called to verify cache hit doesn't call providers
    // Note: We can't directly modify stats, so we'll verify the difference instead
    
    GraphserverResult result2 = gs_engine_expand_vertex(engine, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result2);
    
    size_t second_edge_count = gs_edge_list_get_count(edges2);
    ASSERT_EQ(first_edge_count, second_edge_count); // Should have same number of edges
    
    // Verify cache hit statistics
    GraphserverResult stats_result2 = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result2);
    ASSERT_EQ(1U, stats.cache_misses); // Still 1
    ASSERT_EQ(1U, stats.cache_hits);   // Now 1
    ASSERT_EQ(1U, stats.cache_puts);   // Still 1
    ASSERT_EQ(1U, stats.providers_called); // Should still be 1 (providers not called for cache hit)
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test cache miss behavior
TEST(engine_cache_miss_behavior) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("miss_test");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Verify cache miss behavior
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_puts);
    ASSERT_EQ(1U, stats.providers_called);
    
    // Verify edges were generated normally
    ASSERT(gs_edge_list_get_count(edges) > 0);
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test caching disabled behavior
TEST(engine_cache_disabled_behavior) {
    // Create engine with caching disabled (default)
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("disabled_test");
    
    // Expand vertex multiple times
    for (int i = 0; i < 3; i++) {
        GraphserverEdgeList* edges = gs_edge_list_create();
        gs_edge_list_set_owns_edges(edges, true);
        
        GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT(gs_edge_list_get_count(edges) > 0);
        
        gs_edge_list_destroy(edges);
    }
    
    // Verify cache statistics remain zero
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    // Providers should be called every time
    ASSERT_EQ(3U, stats.providers_called);
    
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test mixed cache hit/miss scenario
TEST(engine_mixed_cache_scenario) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertexA = create_test_vertex("vertex_A");
    GraphserverVertex* vertexB = create_test_vertex("vertex_B");
    
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    // Expand vertex A (cache miss)
    gs_engine_expand_vertex(engine, vertexA, edges);
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Expand vertex B (cache miss)
    gs_edge_list_clear(edges);
    gs_engine_expand_vertex(engine, vertexB, edges);
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(2U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(2U, stats.cache_puts);
    
    // Expand vertex A again (cache hit)
    gs_edge_list_clear(edges);
    gs_engine_expand_vertex(engine, vertexA, edges);
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(2U, stats.cache_misses); // Still 2
    ASSERT_EQ(1U, stats.cache_hits);   // Now 1
    ASSERT_EQ(2U, stats.cache_puts);   // Still 2
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertexA);
    gs_vertex_destroy(vertexB);
    gs_engine_destroy(engine);
}

// Test cache invalidation when provider is registered
TEST(engine_cache_invalidation_on_provider_register) {
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    // Register initial provider
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    ASSERT_NOT_NULL(vertex);
    
    // First expansion - cache miss
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result1 = gs_engine_expand_vertex(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result1);
    
    // Verify cache statistics
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_puts);
    ASSERT_EQ(1U, stats.cache_misses);
    
    // Register another provider - this should clear the cache
    GraphserverResult reg_result = gs_engine_register_provider(engine, "test_provider2", mock_provider_simple, NULL);
    ASSERT_EQ(GS_SUCCESS, reg_result);
    
    // Verify cache statistics are reset
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    
    // Second expansion should be a cache miss (not a hit)
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    GraphserverResult result2 = gs_engine_expand_vertex(engine, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result2);
    
    // Verify it was a cache miss
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(1U, stats.cache_puts);
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test cache invalidation when provider is unregistered
TEST(engine_cache_invalidation_on_provider_unregister) {
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    // Register providers
    gs_engine_register_provider(engine, "test_provider1", mock_provider_simple, NULL);
    gs_engine_register_provider(engine, "test_provider2", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    ASSERT_NOT_NULL(vertex);
    
    // First expansion - cache miss
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result1 = gs_engine_expand_vertex(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result1);
    
    // Verify cache has data
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Unregister a provider - this should clear the cache
    GraphserverResult unreg_result = gs_engine_unregister_provider(engine, "test_provider1");
    ASSERT_EQ(GS_SUCCESS, unreg_result);
    
    // Verify cache statistics are reset
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    
    // Second expansion should be a cache miss
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    GraphserverResult result2 = gs_engine_expand_vertex(engine, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result2);
    
    // Verify it was a cache miss
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_misses);
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test cache invalidation when provider is disabled
TEST(engine_cache_invalidation_on_provider_disable) {
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    // Register provider
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    ASSERT_NOT_NULL(vertex);
    
    // First expansion - cache miss
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result1 = gs_engine_expand_vertex(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result1);
    
    // Verify cache has data
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Disable the provider - this should clear the cache
    GraphserverResult disable_result = gs_engine_set_provider_enabled(engine, "test_provider", false);
    ASSERT_EQ(GS_SUCCESS, disable_result);
    
    // Verify cache statistics are reset
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    
    // Re-enable the provider
    GraphserverResult enable_result = gs_engine_set_provider_enabled(engine, "test_provider", true);
    ASSERT_EQ(GS_SUCCESS, enable_result);
    
    // Verify cache is still cleared
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    
    gs_edge_list_destroy(edges1);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test cache invalidation on configuration changes
TEST(engine_cache_invalidation_on_config_change) {
    // Create engine with caching enabled
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    // Register provider
    gs_engine_register_provider(engine, "test_provider", mock_provider_simple, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    ASSERT_NOT_NULL(vertex);
    
    // First expansion - cache miss
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result1 = gs_engine_expand_vertex(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result1);
    
    // Verify cache has data
    GraphserverPlanStats stats;
    GraphserverResult stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Change configuration while keeping caching enabled - should clear cache
    GraphserverEngineConfig new_config = config;
    GraphserverResult config_result = gs_engine_set_config(engine, &new_config);
    ASSERT_EQ(GS_SUCCESS, config_result);
    
    // Verify cache statistics are reset
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    
    // Test disabling caching - should destroy cache
    new_config.enable_edge_caching = false;
    config_result = gs_engine_set_config(engine, &new_config);
    ASSERT_EQ(GS_SUCCESS, config_result);
    
    // Verify cache statistics remain zero
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_puts);
    
    // Test re-enabling caching - should create new cache
    new_config.enable_edge_caching = true;
    config_result = gs_engine_set_config(engine, &new_config);
    ASSERT_EQ(GS_SUCCESS, config_result);
    
    // Second expansion should be a cache miss
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    GraphserverResult result2 = gs_engine_expand_vertex(engine, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result2);
    
    // Verify it was a cache miss
    stats_result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, stats_result);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(1U, stats.cache_puts);
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test utility functions
TEST(utility_functions) {
    // Test version string
    const char* version = gs_get_version();
    ASSERT_NOT_NULL(version);
    ASSERT_STR_EQ("2.0.0", version);
    
    // Test error messages
    ASSERT_STR_EQ("Success", gs_get_error_message(GS_SUCCESS));
    ASSERT_STR_EQ("Null pointer", gs_get_error_message(GS_ERROR_NULL_POINTER));
    ASSERT_STR_EQ("Out of memory", gs_get_error_message(GS_ERROR_OUT_OF_MEMORY));
    
    // Test initialization/cleanup
    ASSERT_EQ(GS_SUCCESS, gs_initialize());
    gs_cleanup(); // Should not crash
}

// Main test runner
int main(void) {
    printf("Running Graphserver Engine Tests\n");
    printf("=================================\n");
    
    run_test_engine_lifecycle();
    run_test_engine_custom_config();
    run_test_engine_provider_registration();
    run_test_engine_provider_unregistration();
    run_test_engine_provider_enable_disable();
    run_test_engine_provider_listing();
    run_test_engine_vertex_expansion();
    run_test_engine_multiple_provider_expansion();
    run_test_engine_disabled_provider_expansion();
    run_test_engine_failing_provider_expansion();
    run_test_engine_basic_planning();
    run_test_engine_error_conditions();
    run_test_engine_cache_configuration();
    run_test_engine_cache_lifecycle();
    run_test_engine_cache_hit_performance();
    run_test_engine_cache_miss_behavior();
    run_test_engine_cache_disabled_behavior();
    run_test_engine_mixed_cache_scenario();
    run_test_engine_cache_invalidation_on_provider_register();
    run_test_engine_cache_invalidation_on_provider_unregister();
    run_test_engine_cache_invalidation_on_provider_disable();
    run_test_engine_cache_invalidation_on_config_change();
    run_test_utility_functions();
    
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