#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include "../include/graphserver.h"
#include "../include/gs_planner_internal.h"

// Forward declaration
uint64_t gs_vertex_hash(const GraphserverVertex* vertex);

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

#define ASSERT_DOUBLE_EQ(expected, actual, epsilon) \
    do { \
        if (fabs((expected) - (actual)) > (epsilon)) { \
            printf("FAILED\n  Expected %f, got %f (line %d)\n", (expected), (actual), __LINE__); \
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

// Helper function to create a test vertex with x,y coordinates
static GraphserverVertex* create_coordinate_vertex(int x, int y) {
    GraphserverKeyPair pairs[] = {
        {"x", gs_value_create_int(x)},
        {"y", gs_value_create_int(y)}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 2, NULL);
    return vertex;
}

// Test priority queue creation and destruction
TEST(pq_creation_and_destruction) {
    // Test with arena
    GraphserverArena* arena = gs_arena_create(4096);
    ASSERT_NOT_NULL(arena);
    
    PriorityQueue* pq = pq_create(arena);
    ASSERT_NOT_NULL(pq);
    
    ASSERT(pq_is_empty(pq));
    ASSERT_EQ(0, pq_size(pq));
    
    pq_destroy(pq);
    gs_arena_destroy(arena);
    
    // Test without arena (uses malloc)
    PriorityQueue* pq_malloc = pq_create(NULL);
    ASSERT_NOT_NULL(pq_malloc);
    
    ASSERT(pq_is_empty(pq_malloc));
    ASSERT_EQ(0, pq_size(pq_malloc));
    
    pq_destroy(pq_malloc);
}

// Test extracting from empty queue
TEST(pq_extract_from_empty) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* out_vertex;
    double out_cost;
    
    // Should return false for empty queue
    ASSERT(!pq_extract_min(pq, &out_vertex, &out_cost));
    ASSERT(!pq_extract_min(pq, &out_vertex, NULL));
    
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test NULL input handling
TEST(pq_null_inputs) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    GraphserverVertex* vertex = create_coordinate_vertex(1, 1);
    GraphserverVertex* out_vertex;
    double out_cost;
    
    // Test NULL priority queue
    ASSERT(!pq_insert(NULL, vertex, 1.0));
    ASSERT(!pq_extract_min(NULL, &out_vertex, &out_cost));
    ASSERT(!pq_decrease_key(NULL, vertex, 1.0));
    ASSERT(pq_is_empty(NULL));
    ASSERT_EQ(0, pq_size(NULL));
    ASSERT(!pq_contains(NULL, vertex));
    ASSERT(!pq_peek_min(NULL, &out_vertex, &out_cost));
    
    // Test NULL vertex
    ASSERT(!pq_insert(pq, NULL, 1.0));
    ASSERT(!pq_extract_min(pq, NULL, &out_cost));
    ASSERT(!pq_decrease_key(pq, NULL, 1.0));
    ASSERT(!pq_contains(pq, NULL));
    ASSERT(!pq_peek_min(pq, NULL, &out_cost));
    
    gs_vertex_destroy(vertex);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test decrease key on non-existent vertex
TEST(pq_decrease_nonexistent_key) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    
    // Insert only v1
    ASSERT(pq_insert(pq, v1, 5.0));
    
    // Try to decrease key for v2 (not in queue)
    ASSERT(!pq_decrease_key(pq, v2, 3.0));
    
    // Try to decrease key with higher value (should fail)
    ASSERT(!pq_decrease_key(pq, v1, 6.0));
    ASSERT(!pq_decrease_key(pq, v1, 5.0)); // Same value should fail
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test inserting vertices with duplicate priorities
TEST(pq_insert_duplicate_priorities) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    
    // Insert all with same priority
    ASSERT(pq_insert(pq, v1, 5.0));
    ASSERT(pq_insert(pq, v2, 5.0));
    ASSERT(pq_insert(pq, v3, 5.0));
    
    ASSERT_EQ(3, pq_size(pq));
    
    // Extract all - order may vary but all should have cost 5.0
    GraphserverVertex* out_vertex;
    double out_cost;
    
    ASSERT(pq_extract_min(pq, &out_vertex, &out_cost));
    ASSERT_DOUBLE_EQ(5.0, out_cost, 1e-6);
    
    ASSERT(pq_extract_min(pq, &out_vertex, &out_cost));
    ASSERT_DOUBLE_EQ(5.0, out_cost, 1e-6);
    
    ASSERT(pq_extract_min(pq, &out_vertex, &out_cost));
    ASSERT_DOUBLE_EQ(5.0, out_cost, 1e-6);
    
    ASSERT(pq_is_empty(pq));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test peek operations
TEST(pq_peek_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    
    // Peek empty queue
    GraphserverVertex* out_vertex;
    double out_cost;
    ASSERT(!pq_peek_min(pq, &out_vertex, &out_cost));
    
    // Insert vertices
    ASSERT(pq_insert(pq, v1, 10.0));
    ASSERT(pq_insert(pq, v2, 3.0));
    
    // Peek should return v2 (minimum) without removing
    ASSERT(pq_peek_min(pq, &out_vertex, &out_cost));
    ASSERT(gs_vertex_equals(out_vertex, v2));
    ASSERT_DOUBLE_EQ(3.0, out_cost, 1e-6);
    ASSERT_EQ(2, pq_size(pq)); // Size unchanged
    
    // Peek again should return same
    ASSERT(pq_peek_min(pq, &out_vertex, &out_cost));
    ASSERT(gs_vertex_equals(out_vertex, v2));
    ASSERT_DOUBLE_EQ(3.0, out_cost, 1e-6);
    
    // Extract should return same
    ASSERT(pq_extract_min(pq, &out_vertex, &out_cost));
    ASSERT(gs_vertex_equals(out_vertex, v2));
    ASSERT_DOUBLE_EQ(3.0, out_cost, 1e-6);
    ASSERT_EQ(1, pq_size(pq)); // Size decreased
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test contains operations
TEST(pq_contains_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    
    // Initially empty
    ASSERT(!pq_contains(pq, v1));
    ASSERT(!pq_contains(pq, v2));
    ASSERT(!pq_contains(pq, v3));
    
    // Insert some vertices
    ASSERT(pq_insert(pq, v1, 5.0));
    ASSERT(pq_insert(pq, v2, 3.0));
    
    ASSERT(pq_contains(pq, v1));
    ASSERT(pq_contains(pq, v2));
    ASSERT(!pq_contains(pq, v3));
    
    // Extract v2 (minimum)
    GraphserverVertex* out_vertex;
    ASSERT(pq_extract_min(pq, &out_vertex, NULL));
    ASSERT(gs_vertex_equals(out_vertex, v2));
    
    ASSERT(pq_contains(pq, v1));
    ASSERT(!pq_contains(pq, v2)); // No longer in queue
    ASSERT(!pq_contains(pq, v3));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test clear operations
TEST(pq_clear_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    
    // Insert vertices
    ASSERT(pq_insert(pq, v1, 5.0));
    ASSERT(pq_insert(pq, v2, 3.0));
    ASSERT(pq_insert(pq, v3, 8.0));
    
    ASSERT_EQ(3, pq_size(pq));
    ASSERT(!pq_is_empty(pq));
    
    // Clear queue
    pq_clear(pq);
    
    ASSERT_EQ(0, pq_size(pq));
    ASSERT(pq_is_empty(pq));
    ASSERT(!pq_contains(pq, v1));
    ASSERT(!pq_contains(pq, v2));
    ASSERT(!pq_contains(pq, v3));
    
    // Should be able to use queue after clearing
    ASSERT(pq_insert(pq, v1, 10.0));
    ASSERT_EQ(1, pq_size(pq));
    ASSERT(pq_contains(pq, v1));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test stress with large number of elements
TEST(pq_stress_test) {
    GraphserverArena* arena = gs_arena_create(1024 * 1024); // 1MB arena
    PriorityQueue* pq = pq_create(arena);
    
    const size_t num_vertices = 1000;
    GraphserverVertex** vertices = malloc(sizeof(GraphserverVertex*) * num_vertices);
    
    // Insert vertices with random priorities
    for (size_t i = 0; i < num_vertices; i++) {
        vertices[i] = create_coordinate_vertex((int)i, (int)i);
        double cost = (double)(num_vertices - i); // Reverse order
        ASSERT(pq_insert(pq, vertices[i], cost));
    }
    
    ASSERT_EQ(num_vertices, pq_size(pq));
    ASSERT(!pq_is_empty(pq));
    
    // Extract all vertices - should come out in priority order
    double last_cost = -1.0;
    for (size_t i = 0; i < num_vertices; i++) {
        GraphserverVertex* out_vertex;
        double out_cost;
        
        ASSERT(pq_extract_min(pq, &out_vertex, &out_cost));
        ASSERT(out_cost >= last_cost); // Should be in non-decreasing order
        last_cost = out_cost;
    }
    
    ASSERT(pq_is_empty(pq));
    ASSERT_EQ(0, pq_size(pq));
    
    // Clean up vertices
    for (size_t i = 0; i < num_vertices; i++) {
        gs_vertex_destroy(vertices[i]);
    }
    free(vertices);
    
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test heap validation
TEST(pq_heap_validation) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    // Empty queue should be valid
    ASSERT(pq_validate_heap(pq));
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    GraphserverVertex* v4 = create_coordinate_vertex(4, 4);
    
    // Insert in random order
    ASSERT(pq_insert(pq, v1, 10.0));
    ASSERT(pq_validate_heap(pq));
    
    ASSERT(pq_insert(pq, v2, 5.0));
    ASSERT(pq_validate_heap(pq));
    
    ASSERT(pq_insert(pq, v3, 15.0));
    ASSERT(pq_validate_heap(pq));
    
    ASSERT(pq_insert(pq, v4, 3.0));
    ASSERT(pq_validate_heap(pq));
    
    // Decrease key and validate
    ASSERT(pq_decrease_key(pq, v1, 1.0));
    ASSERT(pq_validate_heap(pq));
    
    // Extract elements and validate after each
    GraphserverVertex* out_vertex;
    ASSERT(pq_extract_min(pq, &out_vertex, NULL));
    ASSERT(pq_validate_heap(pq));
    
    ASSERT(pq_extract_min(pq, &out_vertex, NULL));
    ASSERT(pq_validate_heap(pq));
    
    ASSERT(pq_extract_min(pq, &out_vertex, NULL));
    ASSERT(pq_validate_heap(pq));
    
    ASSERT(pq_extract_min(pq, &out_vertex, NULL));
    ASSERT(pq_validate_heap(pq));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_vertex_destroy(v4);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test swap debug 
TEST(pq_swap_debug) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    
    ASSERT(pq_insert(pq, v1, 5.0));
    ASSERT(pq_contains(pq, v1));
    
    ASSERT(pq_insert(pq, v2, 3.0));
    ASSERT(pq_contains(pq, v1));
    ASSERT(pq_contains(pq, v2));
    
    // Check which vertex is at the root now
    GraphserverVertex* min_vertex;
    double min_cost;
    ASSERT(pq_peek_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v2));
    ASSERT_DOUBLE_EQ(3.0, min_cost, 1e-6);
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    pq_destroy(pq);
    gs_arena_destroy(arena);
}

// Test basic operations (moved from test_planner.c)
TEST(pq_basic_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    ASSERT_NOT_NULL(arena);
    
    PriorityQueue* pq = pq_create(arena);
    ASSERT_NOT_NULL(pq);
    
    ASSERT(pq_is_empty(pq));
    ASSERT_EQ(0, pq_size(pq));
    
    // Insert some vertices
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex(3, 3);
    
    ASSERT(pq_insert(pq, v1, 5.0));
    ASSERT(pq_insert(pq, v2, 2.0));
    ASSERT(pq_insert(pq, v3, 8.0));
    
    ASSERT(!pq_is_empty(pq));
    ASSERT_EQ(3, pq_size(pq));
    
    // Extract minimum (should be v2 with cost 2.0)
    GraphserverVertex* min_vertex;
    double min_cost;
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v2));
    ASSERT_DOUBLE_EQ(2.0, min_cost, 1e-6);
    
    // Extract next minimum (should be v1 with cost 5.0)
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v1));
    ASSERT_DOUBLE_EQ(5.0, min_cost, 1e-6);
    
    // Extract last (should be v3 with cost 8.0)
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v3));
    ASSERT_DOUBLE_EQ(8.0, min_cost, 1e-6);
    
    ASSERT(pq_is_empty(pq));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_arena_destroy(arena);
}

// Test decrease key operation (moved from test_planner.c)
TEST(pq_decrease_key_basic) {
    GraphserverArena* arena = gs_arena_create(4096);
    PriorityQueue* pq = pq_create(arena);
    
    GraphserverVertex* v1 = create_coordinate_vertex(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex(2, 2);
    
    pq_insert(pq, v1, 10.0);
    pq_insert(pq, v2, 5.0);
    
    // Decrease key for v1
    ASSERT(pq_decrease_key(pq, v1, 3.0));
    
    // v1 should now be minimum
    GraphserverVertex* min_vertex;
    double min_cost;
    ASSERT(pq_extract_min(pq, &min_vertex, &min_cost));
    ASSERT(gs_vertex_equals(min_vertex, v1));
    ASSERT_DOUBLE_EQ(3.0, min_cost, 1e-6);
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_arena_destroy(arena);
}

// Main test runner
int main(void) {
    printf("Running Priority Queue Tests\n");
    printf("=============================\n");
    
    run_test_pq_swap_debug();
    run_test_pq_creation_and_destruction();
    run_test_pq_extract_from_empty();
    run_test_pq_null_inputs();
    run_test_pq_decrease_nonexistent_key();
    run_test_pq_insert_duplicate_priorities();
    run_test_pq_peek_operations();
    run_test_pq_contains_operations();
    run_test_pq_clear_operations();
    run_test_pq_stress_test();
    run_test_pq_heap_validation();
    run_test_pq_basic_operations();
    run_test_pq_decrease_key_basic();
    
    printf("\n=============================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}