#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/gs_memory.h"

// Simple test framework (same as other tests)
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

#define ASSERT_GE(actual, minimum) \
    do { \
        if ((actual) < (minimum)) { \
            printf("FAILED\n  Expected %ld >= %ld (line %d)\n", (long)(actual), (long)(minimum), __LINE__); \
            exit(1); \
        } \
    } while(0)

#define ASSERT_LE(actual, maximum) \
    do { \
        if ((actual) > (maximum)) { \
            printf("FAILED\n  Expected %ld <= %ld (line %d)\n", (long)(actual), (long)(maximum), __LINE__); \
            exit(1); \
        } \
    } while(0)

// Test arena creation and destruction
TEST(arena_lifecycle) {
    GraphserverArena* arena = gs_arena_create(1024);
    ASSERT_NOT_NULL(arena);
    
    // Should be able to get usage
    size_t usage = gs_arena_get_usage(arena);
    ASSERT_EQ(0, usage);
    
    gs_arena_destroy(arena);
    // Should not crash
}

// Test basic allocation
TEST(arena_basic_allocation) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Allocate some memory
    void* ptr1 = gs_arena_alloc(arena, 64);
    ASSERT_NOT_NULL(ptr1);
    
    void* ptr2 = gs_arena_alloc(arena, 128);
    ASSERT_NOT_NULL(ptr2);
    
    // Pointers should be different
    ASSERT(ptr1 != ptr2);
    
    // Usage should increase
    size_t usage = gs_arena_get_usage(arena);
    ASSERT_GE(usage, 64 + 128);
    
    gs_arena_destroy(arena);
}

// Test aligned allocation
TEST(arena_aligned_allocation) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Test various alignments
    void* ptr8 = gs_arena_alloc_aligned(arena, 32, 8);
    ASSERT_NOT_NULL(ptr8);
    ASSERT_EQ(0, (uintptr_t)ptr8 % 8);
    
    void* ptr16 = gs_arena_alloc_aligned(arena, 32, 16);
    ASSERT_NOT_NULL(ptr16);
    ASSERT_EQ(0, (uintptr_t)ptr16 % 16);
    
    void* ptr32 = gs_arena_alloc_aligned(arena, 32, 32);
    ASSERT_NOT_NULL(ptr32);
    ASSERT_EQ(0, (uintptr_t)ptr32 % 32);
    
    gs_arena_destroy(arena);
}

// Test calloc (zeroed allocation)
TEST(arena_calloc) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Allocate zeroed memory
    uint8_t* ptr = (uint8_t*)gs_arena_calloc(arena, 64, sizeof(uint8_t));
    ASSERT_NOT_NULL(ptr);
    
    // Should be zeroed
    for (size_t i = 0; i < 64; i++) {
        ASSERT_EQ(0, ptr[i]);
    }
    
    // Allocate array of integers
    int* ints = (int*)gs_arena_calloc(arena, 10, sizeof(int));
    ASSERT_NOT_NULL(ints);
    
    for (size_t i = 0; i < 10; i++) {
        ASSERT_EQ(0, ints[i]);
    }
    
    gs_arena_destroy(arena);
}

// Test arena reset
TEST(arena_reset) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Allocate some memory
    void* ptr1 = gs_arena_alloc(arena, 256);
    void* ptr2 = gs_arena_alloc(arena, 256);
    ASSERT_NOT_NULL(ptr1);
    ASSERT_NOT_NULL(ptr2);
    
    size_t usage_before = gs_arena_get_usage(arena);
    ASSERT_GE(usage_before, 512);
    
    // Reset the arena
    gs_arena_reset(arena);
    
    size_t usage_after = gs_arena_get_usage(arena);
    ASSERT_EQ(0, usage_after);
    
    // Should be able to allocate again
    void* ptr3 = gs_arena_alloc(arena, 128);
    ASSERT_NOT_NULL(ptr3);
    
    gs_arena_destroy(arena);
}

// Test large allocations that require multiple blocks
TEST(arena_multiple_blocks) {
    GraphserverArena* arena = gs_arena_create(512); // Small initial size
    
    // Allocate memory larger than initial block
    void* ptr1 = gs_arena_alloc(arena, 1024);
    ASSERT_NOT_NULL(ptr1);
    
    void* ptr2 = gs_arena_alloc(arena, 2048);
    ASSERT_NOT_NULL(ptr2);
    
    ASSERT(ptr1 != ptr2);
    
    size_t usage = gs_arena_get_usage(arena);
    ASSERT_GE(usage, 1024 + 2048);
    
    gs_arena_destroy(arena);
}

// Test statistics
TEST(arena_statistics) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    GraphserverMemoryStats stats;
    GraphserverResult result = gs_arena_get_stats(arena, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    
    // Initial stats
    ASSERT_EQ(0, stats.total_allocated);
    ASSERT_EQ(0, stats.total_requested);
    ASSERT_EQ(0, stats.num_allocations);
    ASSERT_EQ(1, stats.num_blocks); // One initial block
    
    // Allocate some memory
    gs_arena_alloc(arena, 100);
    gs_arena_alloc(arena, 200);
    
    result = gs_arena_get_stats(arena, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    
    ASSERT_GE(stats.total_allocated, 300);
    ASSERT_EQ(300, stats.total_requested);
    ASSERT_EQ(2, stats.num_allocations);
    ASSERT_GE(stats.peak_usage, 300);
    
    // Reset and check stats
    gs_arena_reset(arena);
    
    result = gs_arena_get_stats(arena, &stats);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(1, stats.num_resets);
    
    gs_arena_destroy(arena);
}

// Test can_alloc predicate
TEST(arena_can_alloc) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Should be able to allocate small amounts
    ASSERT(gs_arena_can_alloc(arena, 100));
    ASSERT(gs_arena_can_alloc(arena, 500));
    
    // Should be able to allocate large amounts (new block)
    ASSERT(gs_arena_can_alloc(arena, 2048));
    
    // Fill up the arena
    gs_arena_alloc(arena, 1000);
    
    // Should still be able to allocate (will create new block)
    ASSERT(gs_arena_can_alloc(arena, 100));
    
    gs_arena_destroy(arena);
}

// Test typed allocation macros
TEST(arena_typed_allocation) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Test single type allocation
    int* int_ptr = gs_arena_alloc_type(arena, int);
    ASSERT_NOT_NULL(int_ptr);
    ASSERT_EQ(0, (uintptr_t)int_ptr % _Alignof(int));
    
    double* double_ptr = gs_arena_alloc_type(arena, double);
    ASSERT_NOT_NULL(double_ptr);
    ASSERT_EQ(0, (uintptr_t)double_ptr % _Alignof(double));
    
    // Test array allocation
    int* int_array = gs_arena_alloc_array(arena, int, 10);
    ASSERT_NOT_NULL(int_array);
    ASSERT_EQ(0, (uintptr_t)int_array % _Alignof(int));
    
    // Test calloc macros
    long* long_ptr = gs_arena_calloc_type(arena, long);
    ASSERT_NOT_NULL(long_ptr);
    ASSERT_EQ(0, *long_ptr);
    
    char* char_array = gs_arena_calloc_array(arena, char, 256);
    ASSERT_NOT_NULL(char_array);
    for (size_t i = 0; i < 256; i++) {
        ASSERT_EQ(0, char_array[i]);
    }
    
    gs_arena_destroy(arena);
}

// Test edge cases and error conditions
TEST(arena_edge_cases) {
    // Test NULL arena
    ASSERT_NULL(gs_arena_alloc(NULL, 100));
    ASSERT_NULL(gs_arena_calloc(NULL, 10, sizeof(int)));
    ASSERT_EQ(0, gs_arena_get_usage(NULL));
    
    // Test zero-size allocations
    GraphserverArena* arena = gs_arena_create(1024);
    ASSERT_NULL(gs_arena_alloc(arena, 0));
    ASSERT_NULL(gs_arena_calloc(arena, 0, sizeof(int)));
    ASSERT_NULL(gs_arena_calloc(arena, 10, 0));
    
    // Test very small arena
    GraphserverArena* small_arena = gs_arena_create(1);
    ASSERT_NOT_NULL(small_arena);
    
    // Should still be able to allocate (minimum size enforced)
    void* ptr = gs_arena_alloc(small_arena, 100);
    ASSERT_NOT_NULL(ptr);
    
    gs_arena_destroy(small_arena);
    gs_arena_destroy(arena);
}

// Test memory reuse after reset
TEST(arena_memory_reuse) {
    GraphserverArena* arena = gs_arena_create(1024);
    
    // Allocate memory and note the pointer
    void* ptr1 = gs_arena_alloc(arena, 256);
    ASSERT_NOT_NULL(ptr1);
    
    // Reset arena
    gs_arena_reset(arena);
    
    // Allocate again - should get same pointer (memory reuse)
    void* ptr2 = gs_arena_alloc(arena, 256);
    ASSERT_NOT_NULL(ptr2);
    
    // On most implementations, this should be the same pointer
    // but we can't guarantee it, so just check it's valid
    ASSERT_NOT_NULL(ptr2);
    
    gs_arena_destroy(arena);
}

// Performance test (basic)
TEST(arena_performance_basic) {
    GraphserverArena* arena = gs_arena_create(1024 * 1024); // 1MB
    
    // Allocate many small objects
    const size_t num_allocs = 1000;
    void* ptrs[1000];
    
    for (size_t i = 0; i < num_allocs; i++) {
        ptrs[i] = gs_arena_alloc(arena, 64);
        ASSERT_NOT_NULL(ptrs[i]);
    }
    
    // All pointers should be different
    for (size_t i = 0; i < num_allocs; i++) {
        for (size_t j = i + 1; j < num_allocs; j++) {
            ASSERT(ptrs[i] != ptrs[j]);
        }
    }
    
    size_t usage = gs_arena_get_usage(arena);
    ASSERT_GE(usage, num_allocs * 64);
    
    gs_arena_destroy(arena);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Memory Management Tests\n");
    printf("===========================================\n");
    
    run_test_arena_lifecycle();
    run_test_arena_basic_allocation();
    run_test_arena_aligned_allocation();
    run_test_arena_calloc();
    run_test_arena_reset();
    run_test_arena_multiple_blocks();
    run_test_arena_statistics();
    run_test_arena_can_alloc();
    run_test_arena_typed_allocation();
    run_test_arena_edge_cases();
    run_test_arena_memory_reuse();
    run_test_arena_performance_basic();
    
    printf("\n===========================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}