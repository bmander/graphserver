#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/gs_cache.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"

/**
 * @file test_cache.c
 * @brief Comprehensive unit tests for the edge caching system
 * 
 * This test suite covers all aspects of the EdgeCache implementation,
 * including basic operations, edge cases, performance characteristics,
 * and integration scenarios.
 */

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

// Helper function to create a test vertex with a name
static GraphserverVertex* create_test_vertex(const char* name) {
    GraphserverVertex* vertex = gs_vertex_create();
    if (!vertex) return NULL;
    
    GraphserverValue name_val = gs_value_create_string(name);
    gs_vertex_set_kv(vertex, "name", name_val);
    
    return vertex;
}

// Helper function to create a test vertex with coordinates
static GraphserverVertex* create_location_vertex(double lat, double lon) {
    GraphserverVertex* vertex = gs_vertex_create();
    if (!vertex) return NULL;
    
    GraphserverValue lat_val = gs_value_create_float(lat);
    GraphserverValue lon_val = gs_value_create_float(lon);
    
    gs_vertex_set_kv(vertex, "lat", lat_val);
    gs_vertex_set_kv(vertex, "lon", lon_val);
    
    return vertex;
}

// Helper function to create a test edge list with specified number of edges
static GraphserverEdgeList* create_test_edge_list(size_t num_edges) {
    GraphserverEdgeList* list = gs_edge_list_create();
    if (!list) return NULL;
    
    gs_edge_list_set_owns_edges(list, true);
    
    for (size_t i = 0; i < num_edges; i++) {
        char target_name[32];
        snprintf(target_name, sizeof(target_name), "target_%zu", i);
        
        GraphserverVertex* target = create_test_vertex(target_name);
        if (!target) {
            gs_edge_list_destroy(list);
            return NULL;
        }
        
        double cost = (double)(i + 1) * 10.0;
        GraphserverEdge* edge = gs_edge_create(target, &cost, 1);
        if (!edge) {
            gs_vertex_destroy(target);
            gs_edge_list_destroy(list);
            return NULL;
        }
        
        gs_edge_set_owns_target_vertex(edge, true);
        gs_edge_list_add_edge(list, edge);
    }
    
    return list;
}

// Test 1: Basic cache lifecycle
TEST(cache_lifecycle) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    ASSERT_EQ(0, edge_cache_size(cache));
    
    edge_cache_destroy(cache);
    
    // Test destroying NULL cache (should not crash)
    edge_cache_destroy(NULL);
}

// Test 2: Basic put and get operations
TEST(cache_basic_operations) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    // Create test vertex and edge list
    GraphserverVertex* vertex = create_test_vertex("test_vertex");
    GraphserverEdgeList* edges = create_test_edge_list(3);
    ASSERT_NOT_NULL(vertex);
    ASSERT_NOT_NULL(edges);
    
    // Initially cache should be empty
    ASSERT(!edge_cache_contains(cache, vertex));
    ASSERT_EQ(0, edge_cache_size(cache));
    
    // Put edges in cache
    GraphserverResult result = edge_cache_put(cache, vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, edge_cache_size(cache));
    ASSERT(edge_cache_contains(cache, vertex));
    
    // Get edges from cache
    GraphserverEdgeList* retrieved_edges = NULL;
    result = edge_cache_get(cache, vertex, &retrieved_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(retrieved_edges);
    
    // Verify the retrieved edges match the original
    ASSERT_EQ(gs_edge_list_get_count(edges), gs_edge_list_get_count(retrieved_edges));
    
    // Clean up
    gs_edge_list_destroy(retrieved_edges);
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    edge_cache_destroy(cache);
}

// Test 3: Cache miss behavior
TEST(cache_miss_behavior) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    GraphserverVertex* vertex = create_test_vertex("missing_vertex");
    ASSERT_NOT_NULL(vertex);
    
    // Try to get from empty cache
    GraphserverEdgeList* edges = NULL;
    GraphserverResult result = edge_cache_get(cache, vertex, &edges);
    ASSERT_EQ(GS_ERROR_KEY_NOT_FOUND, result);
    ASSERT_NULL(edges);
    
    ASSERT(!edge_cache_contains(cache, vertex));
    
    gs_vertex_destroy(vertex);
    edge_cache_destroy(cache);
}

// Test 4: Cache update (overwrite existing entry)
TEST(cache_update_entry) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    GraphserverVertex* vertex = create_test_vertex("update_vertex");
    GraphserverEdgeList* edges1 = create_test_edge_list(2);
    GraphserverEdgeList* edges2 = create_test_edge_list(5);
    ASSERT_NOT_NULL(vertex);
    ASSERT_NOT_NULL(edges1);
    ASSERT_NOT_NULL(edges2);
    
    // Put initial edges
    GraphserverResult result = edge_cache_put(cache, vertex, edges1);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, edge_cache_size(cache));
    
    // Update with different edges
    result = edge_cache_put(cache, vertex, edges2);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, edge_cache_size(cache)); // Size should remain 1
    
    // Verify updated edges
    GraphserverEdgeList* retrieved = NULL;
    result = edge_cache_get(cache, vertex, &retrieved);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(5U, gs_edge_list_get_count(retrieved)); // Should have 5 edges now
    
    gs_edge_list_destroy(retrieved);
    gs_edge_list_destroy(edges2);
    gs_edge_list_destroy(edges1);
    gs_vertex_destroy(vertex);
    edge_cache_destroy(cache);
}

// Test 5: Multiple vertices in cache
TEST(cache_multiple_vertices) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    const size_t num_vertices = 10;
    GraphserverVertex* vertices[num_vertices];
    GraphserverEdgeList* edge_lists[num_vertices];
    
    // Create and cache multiple vertices
    for (size_t i = 0; i < num_vertices; i++) {
        char name[32];
        snprintf(name, sizeof(name), "vertex_%zu", i);
        
        vertices[i] = create_test_vertex(name);
        edge_lists[i] = create_test_edge_list(i + 1); // Different number of edges for each
        ASSERT_NOT_NULL(vertices[i]);
        ASSERT_NOT_NULL(edge_lists[i]);
        
        GraphserverResult result = edge_cache_put(cache, vertices[i], edge_lists[i]);
        ASSERT_EQ(GS_SUCCESS, result);
    }
    
    ASSERT_EQ(num_vertices, edge_cache_size(cache));
    
    // Verify all vertices are cached with correct data
    for (size_t i = 0; i < num_vertices; i++) {
        ASSERT(edge_cache_contains(cache, vertices[i]));
        
        GraphserverEdgeList* retrieved = NULL;
        GraphserverResult result = edge_cache_get(cache, vertices[i], &retrieved);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ((size_t)(i + 1), gs_edge_list_get_count(retrieved));
        
        gs_edge_list_destroy(retrieved);
    }
    
    // Clean up
    for (size_t i = 0; i < num_vertices; i++) {
        gs_edge_list_destroy(edge_lists[i]);
        gs_vertex_destroy(vertices[i]);
    }
    edge_cache_destroy(cache);
}

// Test 6: Cache clear operation
TEST(cache_clear_operation) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    // Add several entries
    for (int i = 0; i < 5; i++) {
        char name[32];
        snprintf(name, sizeof(name), "vertex_%d", i);
        
        GraphserverVertex* vertex = create_test_vertex(name);
        GraphserverEdgeList* edges = create_test_edge_list(3);
        
        edge_cache_put(cache, vertex, edges);
        
        gs_edge_list_destroy(edges);
        gs_vertex_destroy(vertex);
    }
    
    ASSERT_EQ(5, edge_cache_size(cache));
    
    // Clear cache
    edge_cache_clear(cache);
    ASSERT_EQ(0, edge_cache_size(cache));
    
    // Verify cache is empty
    GraphserverVertex* test_vertex = create_test_vertex("test");
    ASSERT(!edge_cache_contains(cache, test_vertex));
    
    gs_vertex_destroy(test_vertex);
    edge_cache_destroy(cache);
}

// Test 7: Error handling with NULL parameters
TEST(cache_null_parameter_handling) {
    EdgeCache* cache = edge_cache_create();
    GraphserverVertex* vertex = create_test_vertex("test");
    GraphserverEdgeList* edges = create_test_edge_list(1);
    GraphserverEdgeList* out_edges = NULL;
    
    // Test NULL cache
    ASSERT_EQ(GS_ERROR_NULL_POINTER, edge_cache_put(NULL, vertex, edges));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, edge_cache_get(NULL, vertex, &out_edges));
    ASSERT(!edge_cache_contains(NULL, vertex));
    ASSERT_EQ(0, edge_cache_size(NULL));
    
    // Test NULL vertex
    ASSERT_EQ(GS_ERROR_NULL_POINTER, edge_cache_put(cache, NULL, edges));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, edge_cache_get(cache, NULL, &out_edges));
    ASSERT(!edge_cache_contains(cache, NULL));
    
    // Test NULL edges
    ASSERT_EQ(GS_ERROR_NULL_POINTER, edge_cache_put(cache, vertex, NULL));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, edge_cache_get(cache, vertex, NULL));
    
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(vertex);
    edge_cache_destroy(cache);
}

// Test 8: Empty edge list caching
TEST(cache_empty_edge_list) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    GraphserverVertex* vertex = create_test_vertex("empty_vertex");
    GraphserverEdgeList* empty_edges = gs_edge_list_create();
    ASSERT_NOT_NULL(vertex);
    ASSERT_NOT_NULL(empty_edges);
    ASSERT_EQ(0U, gs_edge_list_get_count(empty_edges));
    
    // Cache empty edge list
    GraphserverResult result = edge_cache_put(cache, vertex, empty_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(edge_cache_contains(cache, vertex));
    
    // Retrieve empty edge list
    GraphserverEdgeList* retrieved = NULL;
    result = edge_cache_get(cache, vertex, &retrieved);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_NOT_NULL(retrieved);
    ASSERT_EQ(0U, gs_edge_list_get_count(retrieved));
    
    gs_edge_list_destroy(retrieved);
    gs_edge_list_destroy(empty_edges);
    gs_vertex_destroy(vertex);
    edge_cache_destroy(cache);
}

// Test 9: Cache with complex vertex data
TEST(cache_complex_vertex_data) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    // Create vertex with multiple attributes
    GraphserverVertex* complex_vertex = gs_vertex_create();
    ASSERT_NOT_NULL(complex_vertex);
    
    GraphserverValue name_val = gs_value_create_string("complex_vertex");
    GraphserverValue lat_val = gs_value_create_float(40.7128);
    GraphserverValue lon_val = gs_value_create_float(-74.0060);
    GraphserverValue id_val = gs_value_create_int(12345);
    
    gs_vertex_set_kv(complex_vertex, "name", name_val);
    gs_vertex_set_kv(complex_vertex, "latitude", lat_val);
    gs_vertex_set_kv(complex_vertex, "longitude", lon_val);
    gs_vertex_set_kv(complex_vertex, "id", id_val);
    
    GraphserverEdgeList* edges = create_test_edge_list(4);
    ASSERT_NOT_NULL(edges);
    
    // Cache and retrieve
    GraphserverResult result = edge_cache_put(cache, complex_vertex, edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    GraphserverEdgeList* retrieved = NULL;
    result = edge_cache_get(cache, complex_vertex, &retrieved);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(4U, gs_edge_list_get_count(retrieved));
    
    gs_edge_list_destroy(retrieved);
    gs_edge_list_destroy(edges);
    gs_vertex_destroy(complex_vertex);
    edge_cache_destroy(cache);
}

// Test 10: Cache resizing and performance
TEST(cache_resizing_performance) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    const size_t large_count = 100;
    
    // Add many entries to trigger resizing
    for (size_t i = 0; i < large_count; i++) {
        GraphserverVertex* vertex = create_location_vertex(
            40.0 + (double)i * 0.001, 
            -74.0 + (double)i * 0.001
        );
        GraphserverEdgeList* edges = create_test_edge_list(i % 10 + 1);
        
        GraphserverResult result = edge_cache_put(cache, vertex, edges);
        ASSERT_EQ(GS_SUCCESS, result);
        
        gs_edge_list_destroy(edges);
        gs_vertex_destroy(vertex);
    }
    
    ASSERT_EQ(large_count, edge_cache_size(cache));
    
    // Verify all entries are still accessible after resizing
    for (size_t i = 0; i < large_count; i++) {
        GraphserverVertex* vertex = create_location_vertex(
            40.0 + (double)i * 0.001, 
            -74.0 + (double)i * 0.001
        );
        
        ASSERT(edge_cache_contains(cache, vertex));
        
        GraphserverEdgeList* retrieved = NULL;
        GraphserverResult result = edge_cache_get(cache, vertex, &retrieved);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ((size_t)(i % 10 + 1), gs_edge_list_get_count(retrieved));
        
        gs_edge_list_destroy(retrieved);
        gs_vertex_destroy(vertex);
    }
    
    edge_cache_destroy(cache);
}

// Test 11: Hash collision handling
TEST(cache_hash_collision_handling) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    // Create multiple vertices that might have hash collisions
    // (using similar coordinates to increase collision probability)
    GraphserverVertex* vertices[20];
    GraphserverEdgeList* edge_lists[20];
    
    for (int i = 0; i < 20; i++) {
        vertices[i] = create_location_vertex(40.0, -74.0 + (double)i * 0.0001);
        edge_lists[i] = create_test_edge_list(i + 1);
        
        GraphserverResult result = edge_cache_put(cache, vertices[i], edge_lists[i]);
        ASSERT_EQ(GS_SUCCESS, result);
    }
    
    // Verify all entries are distinct and retrievable
    for (int i = 0; i < 20; i++) {
        ASSERT(edge_cache_contains(cache, vertices[i]));
        
        GraphserverEdgeList* retrieved = NULL;
        GraphserverResult result = edge_cache_get(cache, vertices[i], &retrieved);
        ASSERT_EQ(GS_SUCCESS, result);
        ASSERT_EQ((size_t)(i + 1), gs_edge_list_get_count(retrieved));
        
        gs_edge_list_destroy(retrieved);
    }
    
    ASSERT_EQ(20, edge_cache_size(cache));
    
    // Clean up
    for (int i = 0; i < 20; i++) {
        gs_edge_list_destroy(edge_lists[i]);
        gs_vertex_destroy(vertices[i]);
    }
    edge_cache_destroy(cache);
}

// Test 12: Deep copy verification
TEST(cache_deep_copy_verification) {
    EdgeCache* cache = edge_cache_create();
    ASSERT_NOT_NULL(cache);
    
    GraphserverVertex* vertex = create_test_vertex("copy_test");
    GraphserverEdgeList* original_edges = create_test_edge_list(3);
    ASSERT_NOT_NULL(vertex);
    ASSERT_NOT_NULL(original_edges);
    
    // Cache the edges
    GraphserverResult result = edge_cache_put(cache, vertex, original_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Retrieve the edges
    GraphserverEdgeList* retrieved_edges = NULL;
    result = edge_cache_get(cache, vertex, &retrieved_edges);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Verify they are different objects (deep copies)
    ASSERT(original_edges != retrieved_edges);
    ASSERT_EQ(gs_edge_list_get_count(original_edges), gs_edge_list_get_count(retrieved_edges));
    
    // Modify original edges (should not affect cached copy)
    GraphserverVertex* new_target = create_test_vertex("new_target");
    double cost = 999.0;
    GraphserverEdge* new_edge = gs_edge_create(new_target, &cost, 1);
    gs_edge_set_owns_target_vertex(new_edge, true);
    gs_edge_list_add_edge(original_edges, new_edge);
    
    // Verify cached copy is unchanged
    GraphserverEdgeList* retrieved_again = NULL;
    result = edge_cache_get(cache, vertex, &retrieved_again);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(3U, gs_edge_list_get_count(retrieved_again)); // Still 3, not 4
    
    gs_edge_list_destroy(retrieved_again);
    gs_edge_list_destroy(retrieved_edges);
    gs_edge_list_destroy(original_edges);
    gs_vertex_destroy(vertex);
    edge_cache_destroy(cache);
}

// Main test runner
int main(void) {
    printf("Running Edge Cache Unit Tests\n");
    printf("=============================\n");
    
    run_test_cache_lifecycle();
    run_test_cache_basic_operations();
    run_test_cache_miss_behavior();
    run_test_cache_update_entry();
    run_test_cache_multiple_vertices();
    run_test_cache_clear_operation();
    run_test_cache_null_parameter_handling();
    run_test_cache_empty_edge_list();
    run_test_cache_complex_vertex_data();
    run_test_cache_resizing_performance();
    run_test_cache_hash_collision_handling();
    run_test_cache_deep_copy_verification();
    
    printf("\n=============================\n");
    printf("Cache tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All cache tests PASSED!\n");
        return 0;
    } else {
        printf("Some cache tests FAILED!\n");
        return 1;
    }
}