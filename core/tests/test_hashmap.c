#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include "../include/gs_hashmap.h"
#include "../include/gs_vertex.h"
#include "../include/gs_memory.h"
#include "../include/gs_planner_internal.h"
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

// Declare the vertex hash and equals functions used in hashmap.c
extern size_t vertex_hash(const void* vertex_ptr);
extern bool vertex_equals(const void* a, const void* b);

// Test basic hashmap operations
TEST(hashmap_basic_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    // Initially empty
    ASSERT_EQ(0, hashmap_size(map));
    ASSERT(hashmap_capacity(map) > 0);
    
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    
    // Test put and get
    ASSERT(hashmap_put(map, v1, v1));
    ASSERT(hashmap_put(map, v2, v2));
    ASSERT_EQ(2, hashmap_size(map));
    
    ASSERT(hashmap_get(map, v1) == v1);
    ASSERT(hashmap_get(map, v2) == v2);
    
    // Test contains
    ASSERT(hashmap_contains(map, v1));
    ASSERT(hashmap_contains(map, v2));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_arena_destroy(arena);
}

// Test hashmap remove functionality - this is the critical bug fix test
TEST(hashmap_remove_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    // Create test vertices
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex_safe(3, 3);
    GraphserverVertex* v4 = create_coordinate_vertex_safe(4, 4);
    GraphserverVertex* v5 = create_coordinate_vertex_safe(5, 5);
    
    // Add all vertices
    ASSERT(hashmap_put(map, v1, v1));
    ASSERT(hashmap_put(map, v2, v2));
    ASSERT(hashmap_put(map, v3, v3));
    ASSERT(hashmap_put(map, v4, v4));
    ASSERT(hashmap_put(map, v5, v5));
    ASSERT_EQ(5, hashmap_size(map));
    
    // Verify all vertices are present
    ASSERT(hashmap_contains(map, v1));
    ASSERT(hashmap_contains(map, v2));
    ASSERT(hashmap_contains(map, v3));
    ASSERT(hashmap_contains(map, v4));
    ASSERT(hashmap_contains(map, v5));
    
    // Remove middle vertex - this tests the backward shift logic fix
    ASSERT(hashmap_remove(map, v3));
    ASSERT_EQ(4, hashmap_size(map));
    
    // Critical test: ensure other vertices are still findable after removal
    // This would fail with the original buggy backward shift logic
    ASSERT(hashmap_contains(map, v1));
    ASSERT(hashmap_contains(map, v2));
    ASSERT(!hashmap_contains(map, v3)); // Should be gone
    ASSERT(hashmap_contains(map, v4));
    ASSERT(hashmap_contains(map, v5));
    
    // Remove another vertex
    ASSERT(hashmap_remove(map, v1));
    ASSERT_EQ(3, hashmap_size(map));
    
    // Check remaining vertices are still accessible
    ASSERT(!hashmap_contains(map, v1));
    ASSERT(hashmap_contains(map, v2));
    ASSERT(!hashmap_contains(map, v3));
    ASSERT(hashmap_contains(map, v4));
    ASSERT(hashmap_contains(map, v5));
    
    // Test removing non-existent key
    ASSERT(!hashmap_remove(map, v3)); // Already removed
    ASSERT_EQ(3, hashmap_size(map));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_vertex_destroy(v4);
    gs_vertex_destroy(v5);
    gs_arena_destroy(arena);
}

// Test hashmap resize behavior with removes
TEST(hashmap_remove_with_resize) {
    GraphserverArena* arena = gs_arena_create(8192);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    // Add vertices with different coordinates to avoid hash collisions
    GraphserverVertex* vertices[20];
    for (int i = 0; i < 20; i++) {
        vertices[i] = create_coordinate_vertex_safe(i * 10, i * 10);
        ASSERT(hashmap_put(map, vertices[i], vertices[i]));
    }
    ASSERT_EQ(20, hashmap_size(map));
    
    // Verify all are present
    for (int i = 0; i < 20; i++) {
        ASSERT(hashmap_contains(map, vertices[i]));
    }
    
    // Remove every other vertex
    for (int i = 0; i < 20; i += 2) {
        ASSERT(hashmap_remove(map, vertices[i]));
    }
    ASSERT_EQ(10, hashmap_size(map));
    
    // Verify correct vertices remain
    for (int i = 0; i < 20; i++) {
        if (i % 2 == 0) {
            ASSERT(!hashmap_contains(map, vertices[i]));
        } else {
            ASSERT(hashmap_contains(map, vertices[i]));
        }
    }
    
    // Clean up
    for (int i = 0; i < 20; i++) {
        gs_vertex_destroy(vertices[i]);
    }
    gs_arena_destroy(arena);
}

// Test iterator functionality
TEST(hashmap_iterator) {
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex_safe(3, 3);
    
    hashmap_put(map, v1, v1);
    hashmap_put(map, v2, v2);
    hashmap_put(map, v3, v3);
    
    // Test iterator
    HashMapIterator iter = hashmap_iterator_create(map);
    int count = 0;
    void* key;
    void* value;
    
    while (hashmap_iterator_next(&iter, &key, &value)) {
        ASSERT_NOT_NULL(key);
        ASSERT_NOT_NULL(value);
        ASSERT(key == value); // For our test, key and value are the same
        count++;
    }
    
    ASSERT_EQ(3, count);
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_arena_destroy(arena);
}

// Test hashmap clear
TEST(hashmap_clear) {
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    
    hashmap_put(map, v1, v1);
    hashmap_put(map, v2, v2);
    ASSERT_EQ(2, hashmap_size(map));
    
    hashmap_clear(map);
    ASSERT_EQ(0, hashmap_size(map));
    ASSERT(!hashmap_contains(map, v1));
    ASSERT(!hashmap_contains(map, v2));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_arena_destroy(arena);
}

// Test that specifically triggers the backward shift distance bug
TEST(hashmap_backward_shift_bug) {
    GraphserverArena* arena = gs_arena_create(8192);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    // Create many vertices with pattern that forces hash collisions and triggers the bug
    GraphserverVertex* vertices[40];
    
    for (int i = 0; i < 40; i++) {
        // Use the pattern that we know triggered the bug: (i % 8, i / 8)
        vertices[i] = create_coordinate_vertex_safe(i % 8, i / 8);
        ASSERT(hashmap_put(map, vertices[i], vertices[i]));
    }
    
    // Verify all are present initially  
    for (int i = 0; i < 40; i++) {
        ASSERT(hashmap_contains(map, vertices[i]));
    }
    
    // Remove the specific pattern that triggered the bug
    int to_remove[] = {3, 7, 11, 15, 19, 23, 27, 31};
    int num_to_remove = sizeof(to_remove) / sizeof(to_remove[0]);
    
    for (int i = 0; i < num_to_remove; i++) {
        bool removed = hashmap_remove(map, vertices[to_remove[i]]);
        ASSERT(removed);
    }
    
    // The critical test: verify all remaining entries are still findable
    // This is where the backward shift distance bug manifests!
    for (int i = 0; i < 40; i++) {
        bool should_exist = true;
        
        // Check if this index was removed
        for (int j = 0; j < num_to_remove; j++) {
            if (i == to_remove[j]) {
                should_exist = false;
                break;
            }
        }
        
        bool exists = hashmap_contains(map, vertices[i]);
        
        if (should_exist && !exists) {
            printf("\nBUG: Vertex %d should exist but was not found!\n", i);
            printf("This demonstrates the backward shift distance bug.\n");
        }
        
        // Assert the expected behavior - this will fail with buggy code
        if (should_exist) {
            ASSERT(exists);
        } else {
            ASSERT(!exists);
        }
    }
    
    // Clean up
    for (int i = 0; i < 40; i++) {
        gs_vertex_destroy(vertices[i]);
    }
    gs_arena_destroy(arena);
}

// Test error conditions
TEST(hashmap_error_conditions) {
    // Test NULL parameters
    ASSERT_NULL(hashmap_create(NULL, vertex_equals, NULL));
    ASSERT_NULL(hashmap_create(vertex_hash, NULL, NULL));
    
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    
    // Test NULL parameters to functions
    ASSERT_NULL(hashmap_get(NULL, v1));
    ASSERT_NULL(hashmap_get(map, NULL));
    ASSERT(!hashmap_put(NULL, v1, v1));
    ASSERT(!hashmap_put(map, NULL, v1));
    ASSERT(!hashmap_contains(NULL, v1));
    ASSERT(!hashmap_remove(NULL, v1));
    ASSERT(!hashmap_remove(map, NULL));
    
    gs_vertex_destroy(v1);
    gs_arena_destroy(arena);
}

// Test load factor calculation and tracking
TEST(hashmap_load_factor_tracking) {
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    // Initially empty - load factor should be 0
    ASSERT_EQ(0, hashmap_size(map));
    ASSERT(hashmap_load_factor(map) == 0.0);
    
    // Add elements and check load factor increases
    GraphserverVertex* vertices[20];
    for (int i = 0; i < 10; i++) {
        vertices[i] = create_coordinate_vertex_safe(i, i);
        ASSERT(hashmap_put(map, vertices[i], vertices[i]));
        
        double load_factor = hashmap_load_factor(map);
        ASSERT(load_factor > 0.0);
        ASSERT(load_factor <= 1.0); // Should never exceed 1.0
    }
    
    // Verify load factor calculation: size / capacity
    double expected_load = (double)hashmap_size(map) / hashmap_capacity(map);
    ASSERT(fabs(hashmap_load_factor(map) - expected_load) < 1e-6);
    
    // Cleanup
    for (int i = 0; i < 10; i++) {
        gs_vertex_destroy(vertices[i]);
    }
    gs_arena_destroy(arena);
}

// Test hashmap destruction edge cases
TEST(hashmap_destroy_edge_cases) {
    GraphserverArena* arena = gs_arena_create(4096);
    
    // Test destroying NULL map (should not crash)
    hashmap_destroy(NULL);
    
    // Test destroying empty map
    HashMap* empty_map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(empty_map);
    hashmap_destroy(empty_map); // Should not crash
    
    // Test destroying map with elements
    HashMap* filled_map = hashmap_create(vertex_hash, vertex_equals, arena);
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    
    hashmap_put(filled_map, v1, v1);
    hashmap_put(filled_map, v2, v2);
    
    hashmap_destroy(filled_map); // Should not crash or leak
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_arena_destroy(arena);
}

// Test vertex set wrapper functions
TEST(hashmap_vertex_set_operations) {
    GraphserverArena* arena = gs_arena_create(4096);
    VertexSet* set = vertex_set_create(arena);
    ASSERT_NOT_NULL(set);
    
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    GraphserverVertex* v3 = create_coordinate_vertex_safe(3, 3);
    
    // Initially empty
    ASSERT(!vertex_set_contains(set, v1));
    ASSERT(!vertex_set_contains(set, v2));
    
    // Add vertices
    ASSERT(vertex_set_add(set, v1));
    ASSERT(vertex_set_add(set, v2));
    
    // Check contains
    ASSERT(vertex_set_contains(set, v1));
    ASSERT(vertex_set_contains(set, v2));
    ASSERT(!vertex_set_contains(set, v3));
    
    // Add duplicate (should still work)
    ASSERT(vertex_set_add(set, v1));
    ASSERT(vertex_set_contains(set, v1));
    
    // Clear set
    vertex_set_clear(set);
    ASSERT(!vertex_set_contains(set, v1));
    ASSERT(!vertex_set_contains(set, v2));
    
    // Test edge cases
    ASSERT(!vertex_set_contains(NULL, v1));
    ASSERT(!vertex_set_contains(set, NULL));
    ASSERT(!vertex_set_add(NULL, v1));
    ASSERT(!vertex_set_add(set, NULL));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    vertex_set_destroy(set);
    gs_arena_destroy(arena);
}

// Test hashmap with large datasets (stress test)
TEST(hashmap_stress_testing) {
    GraphserverArena* arena = gs_arena_create(1024 * 1024); // 1MB arena
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    const size_t num_elements = 1000;
    GraphserverVertex** vertices = malloc(sizeof(GraphserverVertex*) * num_elements);
    
    // Insert many elements
    for (size_t i = 0; i < num_elements; i++) {
        vertices[i] = create_coordinate_vertex_safe((int)i, (int)(i * 2));
        ASSERT(hashmap_put(map, vertices[i], vertices[i]));
    }
    
    ASSERT_EQ(num_elements, hashmap_size(map));
    
    // Verify all elements can be retrieved
    for (size_t i = 0; i < num_elements; i++) {
        ASSERT(hashmap_contains(map, vertices[i]));
        ASSERT(hashmap_get(map, vertices[i]) == vertices[i]);
    }
    
    // Remove half the elements
    for (size_t i = 0; i < num_elements / 2; i++) {
        ASSERT(hashmap_remove(map, vertices[i]));
        ASSERT(!hashmap_contains(map, vertices[i]));
    }
    
    ASSERT_EQ(num_elements / 2, hashmap_size(map));
    
    // Verify remaining elements are still accessible
    for (size_t i = num_elements / 2; i < num_elements; i++) {
        ASSERT(hashmap_contains(map, vertices[i]));
    }
    
    // Verify load factor is reasonable
    ASSERT(hashmap_load_factor(map) > 0.0);
    ASSERT(hashmap_load_factor(map) < 1.0);
    
    // Cleanup
    for (size_t i = 0; i < num_elements; i++) {
        gs_vertex_destroy(vertices[i]);
    }
    free(vertices);
    
    gs_arena_destroy(arena);
}

// Test memory management paths (arena vs malloc)
TEST(hashmap_memory_management) {
    // Test with arena allocation
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* arena_map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(arena_map);
    
    GraphserverVertex* v1 = create_coordinate_vertex_safe(1, 1);
    ASSERT(hashmap_put(arena_map, v1, v1));
    ASSERT(hashmap_contains(arena_map, v1));
    
    // Arena-based maps should work normally
    ASSERT_EQ(1, hashmap_size(arena_map));
    ASSERT(hashmap_capacity(arena_map) > 0);
    
    gs_vertex_destroy(v1);
    gs_arena_destroy(arena); // This should clean up the map too
    
    // Test with NULL arena (malloc allocation)
    HashMap* malloc_map = hashmap_create(vertex_hash, vertex_equals, NULL);
    ASSERT_NOT_NULL(malloc_map);
    
    GraphserverVertex* v2 = create_coordinate_vertex_safe(2, 2);
    ASSERT(hashmap_put(malloc_map, v2, v2));
    ASSERT(hashmap_contains(malloc_map, v2));
    
    ASSERT_EQ(1, hashmap_size(malloc_map));
    ASSERT(hashmap_capacity(malloc_map) > 0);
    
    // Must explicitly destroy malloc-based map
    hashmap_destroy(malloc_map);
    gs_vertex_destroy(v2);
}

// Test detailed capacity expansion behavior
TEST(hashmap_capacity_expansion) {
    GraphserverArena* arena = gs_arena_create(4096);
    HashMap* map = hashmap_create(vertex_hash, vertex_equals, arena);
    ASSERT_NOT_NULL(map);
    
    size_t initial_capacity = hashmap_capacity(map);
    ASSERT(initial_capacity > 0);
    
    // Add elements until we trigger a resize
    GraphserverVertex** vertices = malloc(sizeof(GraphserverVertex*) * 100);
    size_t count = 0;
    
    for (int i = 0; i < 100; i++) {
        vertices[i] = create_coordinate_vertex_safe(i, i);
        ASSERT(hashmap_put(map, vertices[i], vertices[i]));
        count++;
        
        size_t current_capacity = hashmap_capacity(map);
        
        // Check if capacity expanded
        if (current_capacity > initial_capacity) {
            // Capacity should have at least doubled
            ASSERT(current_capacity >= initial_capacity * 2);
            break;
        }
        
        // Ensure we don't exceed reasonable load factor before resize
        ASSERT(hashmap_load_factor(map) <= 0.75); // Common threshold
    }
    
    // Verify all elements are still accessible after potential resizes
    for (size_t i = 0; i < count; i++) {
        ASSERT(hashmap_contains(map, vertices[i]));
        ASSERT(hashmap_get(map, vertices[i]) == vertices[i]);
    }
    
    // Cleanup
    for (size_t i = 0; i < count; i++) {
        gs_vertex_destroy(vertices[i]);
    }
    free(vertices);
    gs_arena_destroy(arena);
}

// Main test runner
int main(void) {
    printf("Running Graphserver HashMap Tests\n");
    printf("=================================\n");
    
    run_test_hashmap_basic_operations();
    run_test_hashmap_remove_operations();
    run_test_hashmap_remove_with_resize();
    run_test_hashmap_iterator();
    run_test_hashmap_clear();
    run_test_hashmap_backward_shift_bug();
    run_test_hashmap_error_conditions();
    run_test_hashmap_load_factor_tracking();
    run_test_hashmap_destroy_edge_cases();
    run_test_hashmap_vertex_set_operations();
    run_test_hashmap_stress_testing();
    run_test_hashmap_memory_management();
    run_test_hashmap_capacity_expansion();
    
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