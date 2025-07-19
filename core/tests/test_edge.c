#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/gs_edge.h"
#include "../include/gs_vertex.h"

// Simple test framework (same as vertex tests)
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

#define ASSERT_FLOAT_EQ(expected, actual, epsilon) \
    do { \
        double diff = (expected) - (actual); \
        if (diff < 0) diff = -diff; \
        if (diff > (epsilon)) { \
            printf("FAILED\n  Expected %f, got %f (line %d)\n", (expected), (actual), __LINE__); \
            exit(1); \
        } \
    } while(0)

// Helper function to create a test vertex
GraphserverVertex* create_test_vertex(const char* name, double lat, double lon) {
    GraphserverVertex* vertex = gs_vertex_create();
    
    GraphserverValue name_val = gs_value_create_string(name);
    gs_vertex_set_kv(vertex, "name", name_val);
    
    GraphserverValue lat_val = gs_value_create_float(lat);
    gs_vertex_set_kv(vertex, "lat", lat_val);
    
    GraphserverValue lon_val = gs_value_create_float(lon);
    gs_vertex_set_kv(vertex, "lon", lon_val);
    
    return vertex;
}

// Test edge creation and basic properties
TEST(edge_creation) {
    GraphserverVertex* target = create_test_vertex("Target", 40.7, -74.0);
    double distances[] = {100.0, 5.0}; // distance, time
    
    GraphserverEdge* edge = gs_edge_create(target, distances, 2);
    ASSERT_NOT_NULL(edge);
    
    // Check basic properties
    ASSERT_EQ(target, gs_edge_get_target_vertex(edge));
    ASSERT_EQ(2, gs_edge_get_distance_vector_size(edge));
    
    const double* dist_vec = gs_edge_get_distance_vector(edge);
    ASSERT_NOT_NULL(dist_vec);
    ASSERT_FLOAT_EQ(100.0, dist_vec[0], 0.001);
    ASSERT_FLOAT_EQ(5.0, dist_vec[1], 0.001);
    
    ASSERT_EQ(0, gs_edge_get_metadata_count(edge));
    
    // Cleanup
    gs_edge_destroy(edge);
    // Note: We don't destroy target vertex as edge doesn't own it
    gs_vertex_destroy(target);
}

// Test edge with no distance vector
TEST(edge_no_distance) {
    GraphserverVertex* target = create_test_vertex("Target", 40.7, -74.0);
    
    GraphserverEdge* edge = gs_edge_create(target, NULL, 0);
    ASSERT_NOT_NULL(edge);
    
    ASSERT_EQ(0, gs_edge_get_distance_vector_size(edge));
    ASSERT_NULL(gs_edge_get_distance_vector(edge));
    
    gs_edge_destroy(edge);
    gs_vertex_destroy(target);
}

// Test edge metadata operations
TEST(edge_metadata) {
    GraphserverVertex* target = create_test_vertex("Target", 40.7, -74.0);
    double distances[] = {100.0};
    
    GraphserverEdge* edge = gs_edge_create(target, distances, 1);
    
    // Add metadata
    GraphserverValue mode_val = gs_value_create_string("walking");
    GraphserverResult result = gs_edge_set_metadata(edge, "mode", mode_val);
    ASSERT_EQ(GS_SUCCESS, result);
    
    GraphserverValue speed_val = gs_value_create_float(5.0);
    result = gs_edge_set_metadata(edge, "speed_kmh", speed_val);
    ASSERT_EQ(GS_SUCCESS, result);
    
    ASSERT_EQ(2, gs_edge_get_metadata_count(edge));
    
    // Check if metadata exists
    bool has_key;
    result = gs_edge_has_metadata_key(edge, "mode", &has_key);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(has_key);
    
    result = gs_edge_has_metadata_key(edge, "nonexistent", &has_key);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(!has_key);
    
    // Get metadata back
    GraphserverValue retrieved_val;
    result = gs_edge_get_metadata(edge, "mode", &retrieved_val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(GS_VALUE_STRING, retrieved_val.type);
    ASSERT_STR_EQ("walking", retrieved_val.as.s_val);
    gs_value_destroy(&retrieved_val);
    
    result = gs_edge_get_metadata(edge, "speed_kmh", &retrieved_val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(GS_VALUE_FLOAT, retrieved_val.type);
    ASSERT_FLOAT_EQ(5.0, retrieved_val.as.f_val, 0.001);
    
    // Remove metadata
    result = gs_edge_remove_metadata_key(edge, "mode");
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_get_metadata_count(edge));
    
    result = gs_edge_has_metadata_key(edge, "mode", &has_key);
    ASSERT(!has_key);
    
    // Try to get removed metadata
    result = gs_edge_get_metadata(edge, "mode", &retrieved_val);
    ASSERT_EQ(GS_ERROR_KEY_NOT_FOUND, result);
    
    gs_edge_destroy(edge);
    gs_vertex_destroy(target);
}

// Test edge cloning
TEST(edge_cloning) {
    GraphserverVertex* target = create_test_vertex("Target", 40.7, -74.0);
    double distances[] = {100.0, 5.0};
    
    GraphserverEdge* original = gs_edge_create(target, distances, 2);
    
    // Add some metadata
    GraphserverValue mode_val = gs_value_create_string("transit");
    gs_edge_set_metadata(original, "mode", mode_val);
    
    // Clone the edge
    GraphserverEdge* clone = gs_edge_clone(original);
    ASSERT_NOT_NULL(clone);
    
    // Should be equal but different objects
    ASSERT(gs_edge_equals(original, clone));
    ASSERT(original != clone);
    
    // Target vertices should be equal but different objects
    ASSERT(gs_vertex_equals(gs_edge_get_target_vertex(original), 
                           gs_edge_get_target_vertex(clone)));
    ASSERT(gs_edge_get_target_vertex(original) != gs_edge_get_target_vertex(clone));
    
    // Distance vectors should be equal but different memory
    const double* orig_dist = gs_edge_get_distance_vector(original);
    const double* clone_dist = gs_edge_get_distance_vector(clone);
    ASSERT(orig_dist != clone_dist);
    ASSERT_FLOAT_EQ(orig_dist[0], clone_dist[0], 0.001);
    ASSERT_FLOAT_EQ(orig_dist[1], clone_dist[1], 0.001);
    
    // Metadata should be cloned
    GraphserverValue retrieved_val;
    GraphserverResult result = gs_edge_get_metadata(clone, "mode", &retrieved_val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_STR_EQ("transit", retrieved_val.as.s_val);
    gs_value_destroy(&retrieved_val);
    
    // Get cloned target vertex before destroying edge
    GraphserverVertex* cloned_target = gs_edge_get_target_vertex(clone);
    
    gs_edge_destroy(original);
    gs_edge_destroy(clone);
    gs_vertex_destroy(target);
    gs_vertex_destroy(cloned_target);
}

// Test edge list operations
TEST(edge_list_operations) {
    GraphserverEdgeList* edge_list = gs_edge_list_create();
    ASSERT_NOT_NULL(edge_list);
    ASSERT_EQ(0, gs_edge_list_get_count(edge_list));
    
    // Set edge list to own its edges for this test
    gs_edge_list_set_owns_edges(edge_list, true);
    
    // Create some edges
    GraphserverVertex* target1 = create_test_vertex("Target1", 40.7, -74.0);
    GraphserverVertex* target2 = create_test_vertex("Target2", 40.8, -74.1);
    
    double dist1[] = {100.0};
    double dist2[] = {200.0};
    
    GraphserverEdge* edge1 = gs_edge_create(target1, dist1, 1);
    GraphserverEdge* edge2 = gs_edge_create(target2, dist2, 1);
    
    // Add edges to list
    GraphserverResult result = gs_edge_list_add_edge(edge_list, edge1);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, gs_edge_list_get_count(edge_list));
    
    result = gs_edge_list_add_edge(edge_list, edge2);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(2, gs_edge_list_get_count(edge_list));
    
    // Get edges back
    GraphserverEdge* retrieved_edge;
    result = gs_edge_list_get_edge(edge_list, 0, &retrieved_edge);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(edge1, retrieved_edge);
    
    result = gs_edge_list_get_edge(edge_list, 1, &retrieved_edge);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(edge2, retrieved_edge);
    
    // Test invalid index
    result = gs_edge_list_get_edge(edge_list, 2, &retrieved_edge);
    ASSERT_EQ(GS_ERROR_INVALID_ARGUMENT, result);
    
    // Clear the list (this will destroy the edges since list owns them)
    gs_edge_list_clear(edge_list);
    ASSERT_EQ(0, gs_edge_list_get_count(edge_list));
    
    // Cleanup (edges are already destroyed by clear)
    gs_edge_list_destroy(edge_list);
    gs_vertex_destroy(target1);
    gs_vertex_destroy(target2);
}

// Test edge equality
TEST(edge_equality) {
    GraphserverVertex* target1 = create_test_vertex("Target", 40.7, -74.0);
    GraphserverVertex* target2 = create_test_vertex("Target", 40.7, -74.0);
    GraphserverVertex* target3 = create_test_vertex("Different", 40.8, -74.1);
    
    double dist1[] = {100.0, 5.0};
    double dist2[] = {100.0, 5.0};
    double dist3[] = {200.0, 10.0};
    
    GraphserverEdge* edge1 = gs_edge_create(target1, dist1, 2);
    GraphserverEdge* edge2 = gs_edge_create(target2, dist2, 2);
    GraphserverEdge* edge3 = gs_edge_create(target3, dist3, 2);
    
    // Edges with same target and distance should be equal
    ASSERT(gs_edge_equals(edge1, edge2));
    
    // Edges with different targets should not be equal
    ASSERT(!gs_edge_equals(edge1, edge3));
    
    // Add metadata to one edge
    GraphserverValue mode_val = gs_value_create_string("walking");
    gs_edge_set_metadata(edge1, "mode", mode_val);
    
    // Should no longer be equal
    ASSERT(!gs_edge_equals(edge1, edge2));
    
    // Add same metadata to second edge
    GraphserverValue mode_val2 = gs_value_create_string("walking");
    gs_edge_set_metadata(edge2, "mode", mode_val2);
    
    // Should be equal again
    ASSERT(gs_edge_equals(edge1, edge2));
    
    gs_edge_destroy(edge1);
    gs_edge_destroy(edge2);
    gs_edge_destroy(edge3);
    gs_vertex_destroy(target1);
    gs_vertex_destroy(target2);
    gs_vertex_destroy(target3);
}

// Test edge string representation
TEST(edge_string_representation) {
    GraphserverVertex* target = create_test_vertex("TestTarget", 40.7, -74.0);
    double distances[] = {100.0, 5.0};
    
    GraphserverEdge* edge = gs_edge_create(target, distances, 2);
    
    char* str = gs_edge_to_string(edge);
    ASSERT_NOT_NULL(str);
    
    // Should contain some key information
    ASSERT(strstr(str, "Edge") != NULL);
    ASSERT(strstr(str, "100") != NULL);
    ASSERT(strstr(str, "5") != NULL);
    
    free(str);
    gs_edge_destroy(edge);
    gs_vertex_destroy(target);
}

// Test error conditions
TEST(edge_error_conditions) {
    // NULL target vertex should fail
    double dist[] = {100.0};
    GraphserverEdge* edge = gs_edge_create(NULL, dist, 1);
    ASSERT_NULL(edge);
    
    // NULL pointer checks for other functions
    GraphserverVertex* target = create_test_vertex("Test", 40.7, -74.0);
    edge = gs_edge_create(target, dist, 1);
    
    GraphserverValue val = gs_value_create_int(1);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_edge_set_metadata(NULL, "key", val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_edge_set_metadata(edge, NULL, val));
    
    GraphserverValue out_val;
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_edge_get_metadata(NULL, "key", &out_val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_edge_get_metadata(edge, NULL, &out_val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_edge_get_metadata(edge, "key", NULL));
    
    // Key not found
    ASSERT_EQ(GS_ERROR_KEY_NOT_FOUND, gs_edge_get_metadata(edge, "nonexistent", &out_val));
    
    gs_edge_destroy(edge);
    gs_vertex_destroy(target);
    gs_value_destroy(&val);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Edge Tests\n");
    printf("==============================\n");
    
    run_test_edge_creation();
    run_test_edge_no_distance();
    run_test_edge_metadata();
    run_test_edge_cloning();
    run_test_edge_list_operations();
    run_test_edge_equality();
    run_test_edge_string_representation();
    run_test_edge_error_conditions();
    
    printf("\n==============================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}