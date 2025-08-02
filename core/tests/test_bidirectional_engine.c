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

// Mock provider that supports both outgoing and incoming edges
static int mock_bidirectional_outgoing(const GraphserverVertex* current_vertex,
                                       GraphserverEdgeList* out_edges,
                                       void* user_data) {
    (void)current_vertex; // Unused
    (void)user_data; // Unused
    
    // Create outgoing edge to "out_target"
    GraphserverVertex* target = create_named_vertex_safe("out_target");
    if (!target) return -1;
    
    double distance = 2.0;
    GraphserverEdge* edge = gs_edge_create(target, &distance, 1);
    if (!edge) {
        gs_vertex_destroy(target);
        return -1;
    }
    
    gs_edge_set_owns_target_vertex(edge, true);
    GraphserverResult result = gs_edge_list_add_edge(out_edges, edge);
    return (result == GS_SUCCESS) ? 0 : -1;
}

static int mock_bidirectional_incoming(const GraphserverVertex* current_vertex,
                                       GraphserverEdgeList* in_edges,
                                       void* user_data) {
    (void)current_vertex; // Unused
    (void)user_data; // Unused
    
    // Create incoming edge from "in_source"
    GraphserverVertex* source = create_named_vertex_safe("in_source");
    if (!source) return -1;
    
    double distance = 3.0;
    GraphserverEdge* edge = gs_edge_create(source, &distance, 1);
    if (!edge) {
        gs_vertex_destroy(source);
        return -1;
    }
    
    gs_edge_set_owns_target_vertex(edge, true);
    GraphserverResult result = gs_edge_list_add_edge(in_edges, edge);
    return (result == GS_SUCCESS) ? 0 : -1;
}

// Mock provider that only supports outgoing edges
static int mock_outgoing_only(const GraphserverVertex* current_vertex,
                              GraphserverEdgeList* out_edges,
                              void* user_data) {
    (void)current_vertex;
    (void)user_data;
    
    GraphserverVertex* target = create_named_vertex_safe("outgoing_only_target");
    if (!target) return -1;
    
    double distance = 1.5;
    GraphserverEdge* edge = gs_edge_create(target, &distance, 1);
    if (!edge) {
        gs_vertex_destroy(target);
        return -1;
    }
    
    gs_edge_set_owns_target_vertex(edge, true);
    GraphserverResult result = gs_edge_list_add_edge(out_edges, edge);
    return (result == GS_SUCCESS) ? 0 : -1;
}

// Mock provider that only supports incoming edges
static int mock_incoming_only(const GraphserverVertex* current_vertex,
                              GraphserverEdgeList* in_edges,
                              void* user_data) {
    (void)current_vertex;
    (void)user_data;
    
    GraphserverVertex* source = create_named_vertex_safe("incoming_only_source");
    if (!source) return -1;
    
    double distance = 2.5;
    GraphserverEdge* edge = gs_edge_create(source, &distance, 1);
    if (!edge) {
        gs_vertex_destroy(source);
        return -1;
    }
    
    gs_edge_set_owns_target_vertex(edge, true);
    GraphserverResult result = gs_edge_list_add_edge(in_edges, edge);
    return (result == GS_SUCCESS) ? 0 : -1;
}

// Mock provider that fails for both directions
static int mock_failing_provider(const GraphserverVertex* current_vertex,
                                 GraphserverEdgeList* edges,
                                 void* user_data) {
    (void)current_vertex;
    (void)edges;
    (void)user_data;
    return -1; // Always fail
}

// Helper function to create test vertex
GraphserverVertex* create_test_vertex(const char* name) {
    return create_named_vertex_safe(name);
}

// Test bidirectional provider registration with both generators
TEST(bidirectional_registration_both) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Register bidirectional provider with both generators
    GraphserverResult result = gs_engine_register_bidirectional_provider(
        engine, "bidirectional_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Verify provider is registered
    ASSERT_EQ(1, gs_engine_get_provider_count(engine));
    ASSERT(gs_engine_has_provider(engine, "bidirectional_provider"));
    
    gs_engine_destroy(engine);
}

// Test bidirectional provider registration with only outgoing generator
TEST(bidirectional_registration_outgoing_only) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Register with outgoing generator only
    GraphserverResult result = gs_engine_register_bidirectional_provider(
        engine, "outgoing_provider", 
        mock_outgoing_only, NULL, NULL);
    ASSERT_EQ(GS_SUCCESS, result);
    
    ASSERT_EQ(1, gs_engine_get_provider_count(engine));
    ASSERT(gs_engine_has_provider(engine, "outgoing_provider"));
    
    gs_engine_destroy(engine);
}

// Test bidirectional provider registration with only incoming generator
TEST(bidirectional_registration_incoming_only) {
    GraphserverEngine* engine = gs_engine_create();
    ASSERT_NOT_NULL(engine);
    
    // Register with incoming generator only
    GraphserverResult result = gs_engine_register_bidirectional_provider(
        engine, "incoming_provider", 
        NULL, mock_incoming_only, NULL);
    ASSERT_EQ(GS_SUCCESS, result);
    
    ASSERT_EQ(1, gs_engine_get_provider_count(engine));
    ASSERT(gs_engine_has_provider(engine, "incoming_provider"));
    
    gs_engine_destroy(engine);
}

// Test bidirectional provider registration error cases
TEST(bidirectional_registration_errors) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Test both generators NULL (should fail)
    GraphserverResult result = gs_engine_register_bidirectional_provider(
        engine, "invalid_provider", NULL, NULL, NULL);
    ASSERT_EQ(GS_ERROR_INVALID_ARGUMENT, result);
    
    // Test NULL engine
    result = gs_engine_register_bidirectional_provider(
        NULL, "provider", mock_bidirectional_outgoing, NULL, NULL);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, result);
    
    // Test NULL provider name
    result = gs_engine_register_bidirectional_provider(
        engine, NULL, mock_bidirectional_outgoing, NULL, NULL);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, result);
    
    // Register a provider first
    result = gs_engine_register_bidirectional_provider(
        engine, "test_provider", mock_bidirectional_outgoing, NULL, NULL);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Try to register with same name (should fail)
    result = gs_engine_register_bidirectional_provider(
        engine, "test_provider", mock_bidirectional_incoming, NULL, NULL);
    ASSERT_EQ(GS_ERROR_INVALID_ARGUMENT, result);
    
    gs_engine_destroy(engine);
}

// Test outgoing edge expansion with bidirectional provider
TEST(outgoing_expansion_bidirectional) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register bidirectional provider
    gs_engine_register_bidirectional_provider(
        engine, "bidirectional", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("start");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    // Expand outgoing edges
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should have one outgoing edge
    ASSERT_EQ(1, gs_edge_list_get_count(edges));
    
    GraphserverEdge* edge;
    result = gs_edge_list_get_edge(edges, 0, &edge);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(edge);
    
    // Check edge properties
    const double* dist = gs_edge_get_distance_vector(edge);
    ASSERT_NOT_NULL(dist);
    ASSERT_EQ(2.0, dist[0]); // Distance from mock_bidirectional_outgoing
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test incoming edge expansion with bidirectional provider
TEST(incoming_expansion_bidirectional) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register bidirectional provider
    gs_engine_register_bidirectional_provider(
        engine, "bidirectional", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("end");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    // Expand incoming edges
    GraphserverResult result = gs_engine_expand_vertex_incoming(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should have one incoming edge
    ASSERT_EQ(1, gs_edge_list_get_count(edges));
    
    GraphserverEdge* edge;
    result = gs_edge_list_get_edge(edges, 0, &edge);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(edge);
    
    // Check edge properties
    const double* dist = gs_edge_get_distance_vector(edge);
    ASSERT_NOT_NULL(dist);
    ASSERT_EQ(3.0, dist[0]); // Distance from mock_bidirectional_incoming
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test incoming expansion with outgoing-only provider
TEST(incoming_expansion_outgoing_only) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register outgoing-only provider
    gs_engine_register_bidirectional_provider(
        engine, "outgoing_only", mock_outgoing_only, NULL, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("end");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    // Incoming expansion should succeed but produce no edges
    GraphserverResult result = gs_engine_expand_vertex_incoming(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should have no incoming edges
    ASSERT_EQ(0, gs_edge_list_get_count(edges));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test outgoing expansion with incoming-only provider
TEST(outgoing_expansion_incoming_only) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register incoming-only provider
    gs_engine_register_bidirectional_provider(
        engine, "incoming_only", NULL, mock_incoming_only, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("start");
    GraphserverEdgeList* edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges, true);
    
    // Outgoing expansion should succeed but produce no edges
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Should have no outgoing edges
    ASSERT_EQ(0, gs_edge_list_get_count(edges));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test multiple bidirectional providers
TEST(multiple_bidirectional_providers) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register multiple providers
    gs_engine_register_bidirectional_provider(
        engine, "provider1", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    gs_engine_register_bidirectional_provider(
        engine, "provider2", 
        mock_outgoing_only, NULL, NULL);
    gs_engine_register_bidirectional_provider(
        engine, "provider3", 
        NULL, mock_incoming_only, NULL);
    
    ASSERT_EQ(3, gs_engine_get_provider_count(engine));
    
    GraphserverVertex* vertex = create_test_vertex("test");
    
    // Test outgoing expansion - should get edges from provider1 and provider2
    GraphserverEdgeList* out_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(out_edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, out_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2, gs_edge_list_get_count(out_edges)); // provider1 + provider2
    
    // Test incoming expansion - should get edges from provider1 and provider3
    GraphserverEdgeList* in_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(in_edges, true);
    
    result = gs_engine_expand_vertex_incoming(engine, vertex, in_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2, gs_edge_list_get_count(in_edges)); // provider1 + provider3
    
    gs_edge_list_destroy(out_edges);
    gs_edge_list_destroy(in_edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test disabled bidirectional provider
TEST(disabled_bidirectional_provider) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register and then disable provider
    gs_engine_register_bidirectional_provider(
        engine, "disabled_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    gs_engine_set_provider_enabled(engine, "disabled_provider", false);
    
    GraphserverVertex* vertex = create_test_vertex("test");
    
    // Test outgoing expansion with disabled provider
    GraphserverEdgeList* out_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(out_edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, out_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(0, gs_edge_list_get_count(out_edges)); // No edges from disabled provider
    
    // Test incoming expansion with disabled provider
    GraphserverEdgeList* in_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(in_edges, true);
    
    result = gs_engine_expand_vertex_incoming(engine, vertex, in_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(0, gs_edge_list_get_count(in_edges)); // No edges from disabled provider
    
    gs_edge_list_destroy(out_edges);
    gs_edge_list_destroy(in_edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test failing bidirectional provider
TEST(failing_bidirectional_provider) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register failing providers
    gs_engine_register_bidirectional_provider(
        engine, "failing_provider", 
        mock_failing_provider, mock_failing_provider, NULL);
    
    // Also register a good provider to ensure engine still works
    gs_engine_register_bidirectional_provider(
        engine, "good_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("test");
    
    // Test outgoing expansion - should get edges from good provider only
    GraphserverEdgeList* out_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(out_edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, out_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(out_edges)); // Only from good provider
    
    // Test incoming expansion - should get edges from good provider only
    GraphserverEdgeList* in_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(in_edges, true);
    
    result = gs_engine_expand_vertex_incoming(engine, vertex, in_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(in_edges)); // Only from good provider
    
    gs_edge_list_destroy(out_edges);
    gs_edge_list_destroy(in_edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test incoming expansion error conditions
TEST(incoming_expansion_errors) {
    GraphserverEngine* engine = gs_engine_create();
    gs_engine_register_bidirectional_provider(
        engine, "test_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("test");
    GraphserverEdgeList* edges = gs_edge_list_create();
    
    // Test NULL engine
    GraphserverResult result = gs_engine_expand_vertex_incoming(NULL, vertex, edges);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, result);
    
    // Test NULL vertex
    result = gs_engine_expand_vertex_incoming(engine, NULL, edges);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, result);
    
    // Test NULL edges
    result = gs_engine_expand_vertex_incoming(engine, vertex, NULL);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, result);
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test bidirectional caching - outgoing edges
TEST(bidirectional_cache_outgoing) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_bidirectional_provider(
        engine, "cached_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    
    // First outgoing expansion - cache miss
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(edges1));
    
    // Verify cache miss
    GraphserverPlanStats stats;
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Second outgoing expansion - cache hit
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    result = gs_engine_expand_vertex(engine, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(edges2));
    
    // Verify cache hit
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1U, stats.cache_misses); // Still 1
    ASSERT_EQ(1U, stats.cache_hits);   // Now 1
    ASSERT_EQ(1U, stats.cache_puts);   // Still 1
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test bidirectional caching - incoming edges
// NOTE: Incoming edge caching is not yet implemented in the core engine
TEST(bidirectional_cache_incoming) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_bidirectional_provider(
        engine, "cached_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("cache_test");
    
    // First incoming expansion - incoming edges are not cached yet
    GraphserverEdgeList* edges1 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges1, true);
    
    GraphserverResult result = gs_engine_expand_vertex_incoming(engine, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(edges1));
    
    // Verify that cache is not used for incoming edges (implementation limitation)
    GraphserverPlanStats stats;
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(0U, stats.cache_misses); // No cache operations for incoming edges
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_puts);
    
    // Second incoming expansion - still no caching
    GraphserverEdgeList* edges2 = gs_edge_list_create();
    gs_edge_list_set_owns_edges(edges2, true);
    
    result = gs_engine_expand_vertex_incoming(engine, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(edges2));
    
    // Verify no cache operations still
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(0U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(0U, stats.cache_puts);
    
    gs_edge_list_destroy(edges1);
    gs_edge_list_destroy(edges2);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test mixed cache scenario - outgoing and incoming
// NOTE: Only outgoing edges are cached; incoming edges are not cached yet
TEST(bidirectional_cache_mixed) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    config.enable_edge_caching = true;
    
    GraphserverEngine* engine = gs_engine_create_with_config(&config);
    ASSERT_NOT_NULL(engine);
    
    gs_engine_register_bidirectional_provider(
        engine, "cached_provider", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    GraphserverVertex* vertex = create_test_vertex("mixed_cache_test");
    
    // Outgoing expansion - cache miss
    GraphserverEdgeList* out_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(out_edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, out_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    GraphserverPlanStats stats;
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1U, stats.cache_misses);
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Incoming expansion - no cache operations (not implemented)
    GraphserverEdgeList* in_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(in_edges, true);
    
    result = gs_engine_expand_vertex_incoming(engine, vertex, in_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1U, stats.cache_misses); // Still 1 (no change from incoming)
    ASSERT_EQ(0U, stats.cache_hits);
    ASSERT_EQ(1U, stats.cache_puts);
    
    // Repeat outgoing expansion - cache hit
    gs_edge_list_clear(out_edges);
    result = gs_engine_expand_vertex(engine, vertex, out_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1U, stats.cache_misses); // Still 1
    ASSERT_EQ(1U, stats.cache_hits);   // Now 1
    ASSERT_EQ(1U, stats.cache_puts);   // Still 1
    
    // Repeat incoming expansion - still no caching
    gs_edge_list_clear(in_edges);
    result = gs_engine_expand_vertex_incoming(engine, vertex, in_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    result = gs_engine_get_stats(engine, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1U, stats.cache_misses); // Still 1
    ASSERT_EQ(1U, stats.cache_hits);   // Still 1
    ASSERT_EQ(1U, stats.cache_puts);   // Still 1
    
    gs_edge_list_destroy(out_edges);
    gs_edge_list_destroy(in_edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Test mixed traditional and bidirectional provider integration
TEST(mixed_provider_integration) {
    GraphserverEngine* engine = gs_engine_create();
    
    // Register traditional provider (using old API)
    gs_engine_register_provider(engine, "traditional", mock_outgoing_only, NULL);
    
    // Register bidirectional provider
    gs_engine_register_bidirectional_provider(
        engine, "bidirectional", 
        mock_bidirectional_outgoing, mock_bidirectional_incoming, NULL);
    
    ASSERT_EQ(2, gs_engine_get_provider_count(engine));
    
    GraphserverVertex* vertex = create_test_vertex("mixed_test");
    
    // Test outgoing expansion - should get edges from both providers
    GraphserverEdgeList* out_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(out_edges, true);
    
    GraphserverResult result = gs_engine_expand_vertex(engine, vertex, out_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2, gs_edge_list_get_count(out_edges)); // traditional + bidirectional
    
    // Test incoming expansion - should get edges only from bidirectional provider
    GraphserverEdgeList* in_edges = gs_edge_list_create();
    gs_edge_list_set_owns_edges(in_edges, true);
    
    result = gs_engine_expand_vertex_incoming(engine, vertex, in_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(in_edges)); // Only bidirectional
    
    gs_edge_list_destroy(out_edges);
    gs_edge_list_destroy(in_edges);
    gs_vertex_destroy(vertex);
    gs_engine_destroy(engine);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Bidirectional Engine Tests\n");
    printf("==============================================\n");
    
    // Bidirectional provider registration tests
    run_test_bidirectional_registration_both();
    run_test_bidirectional_registration_outgoing_only();
    run_test_bidirectional_registration_incoming_only();
    run_test_bidirectional_registration_errors();
    
    // Edge expansion tests
    run_test_outgoing_expansion_bidirectional();
    run_test_incoming_expansion_bidirectional();
    run_test_incoming_expansion_outgoing_only();
    run_test_outgoing_expansion_incoming_only();
    run_test_multiple_bidirectional_providers();
    run_test_disabled_bidirectional_provider();
    run_test_failing_bidirectional_provider();
    run_test_incoming_expansion_errors();
    
    // Caching tests
    run_test_bidirectional_cache_outgoing();
    run_test_bidirectional_cache_incoming();
    run_test_bidirectional_cache_mixed();
    
    // Integration tests
    run_test_mixed_provider_integration();
    
    printf("\n==============================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All bidirectional tests PASSED!\n");
        return 0;
    } else {
        printf("Some bidirectional tests FAILED!\n");
        return 1;
    }
}