#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/gs_vertex.h"

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

// Test value creation and basic operations
TEST(value_creation) {
    GraphserverValue int_val = gs_value_create_int(42);
    ASSERT_EQ(GS_VALUE_INT, int_val.type);
    ASSERT_EQ(42, int_val.as.i_val);
    
    GraphserverValue float_val = gs_value_create_float(3.14);
    ASSERT_EQ(GS_VALUE_FLOAT, float_val.type);
    ASSERT(float_val.as.f_val > 3.13 && float_val.as.f_val < 3.15);
    
    GraphserverValue str_val = gs_value_create_string("hello");
    ASSERT_EQ(GS_VALUE_STRING, str_val.type);
    ASSERT_STR_EQ("hello", str_val.as.s_val);
    
    GraphserverValue bool_val = gs_value_create_bool(true);
    ASSERT_EQ(GS_VALUE_BOOL, bool_val.type);
    ASSERT(bool_val.as.b_val);
    
    // Cleanup
    gs_value_destroy(&str_val);
}

// Test value equality
TEST(value_equality) {
    GraphserverValue int1 = gs_value_create_int(42);
    GraphserverValue int2 = gs_value_create_int(42);
    GraphserverValue int3 = gs_value_create_int(24);
    
    ASSERT(gs_value_equals(&int1, &int2));
    ASSERT(!gs_value_equals(&int1, &int3));
    
    GraphserverValue str1 = gs_value_create_string("test");
    GraphserverValue str2 = gs_value_create_string("test");
    GraphserverValue str3 = gs_value_create_string("different");
    
    ASSERT(gs_value_equals(&str1, &str2));
    ASSERT(!gs_value_equals(&str1, &str3));
    ASSERT(!gs_value_equals(&int1, &str1)); // Different types
    
    // Cleanup
    gs_value_destroy(&str1);
    gs_value_destroy(&str2);
    gs_value_destroy(&str3);
}

// Test value copying
TEST(value_copying) {
    GraphserverValue original = gs_value_create_string("original");
    GraphserverValue copy = gs_value_copy(&original);
    
    ASSERT(gs_value_equals(&original, &copy));
    ASSERT(original.as.s_val != copy.as.s_val); // Different memory
    
    // Cleanup
    gs_value_destroy(&original);
    gs_value_destroy(&copy);
}

// Test vertex creation and destruction
TEST(vertex_lifecycle) {
    GraphserverVertex* vertex = gs_vertex_create(NULL, 0, NULL);
    ASSERT_NOT_NULL(vertex);
    ASSERT_EQ(0, gs_vertex_get_key_count(vertex));
    ASSERT_EQ(0, gs_vertex_hash(vertex));
    
    gs_vertex_destroy(vertex);
    // Should not crash
}

// Test vertex access with immutable data
TEST(vertex_immutable_access) {
    // Create vertex with initial data
    GraphserverValue int_val = gs_value_create_int(42);
    GraphserverValue str_val = gs_value_create_string("hello");
    GraphserverKeyPair pairs[] = {
        {"number", int_val},
        {"greeting", str_val}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 2, NULL);
    ASSERT_NOT_NULL(vertex);
    ASSERT_EQ(2, gs_vertex_get_key_count(vertex));
    
    // Check if keys exist
    bool has_key;
    GraphserverResult result = gs_vertex_has_key(vertex, "number", &has_key);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(has_key);
    
    result = gs_vertex_has_key(vertex, "nonexistent", &has_key);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT(!has_key);
    
    // Get values back
    GraphserverValue retrieved_val;
    result = gs_vertex_get_value(vertex, "number", &retrieved_val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(GS_VALUE_INT, retrieved_val.type);
    ASSERT_EQ(42, retrieved_val.as.i_val);
    
    result = gs_vertex_get_value(vertex, "greeting", &retrieved_val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(GS_VALUE_STRING, retrieved_val.type);
    ASSERT_STR_EQ("hello", retrieved_val.as.s_val);
    gs_value_destroy(&retrieved_val);
    
    // Try to get non-existent key
    result = gs_vertex_get_value(vertex, "nonexistent", &retrieved_val);
    ASSERT_EQ(GS_ERROR_KEY_NOT_FOUND, result);
    
    gs_vertex_destroy(vertex);
    // Clean up original values (vertex makes copies)
    gs_value_destroy(&str_val);
}

// Test vertex key ordering (keys should be stored in sorted order)
TEST(vertex_key_ordering) {
    // Create vertex with keys in non-alphabetical order
    GraphserverKeyPair pairs[] = {
        {"zebra", gs_value_create_int(1)},
        {"apple", gs_value_create_int(2)},
        {"monkey", gs_value_create_int(3)}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 3, NULL);
    ASSERT_NOT_NULL(vertex);
    ASSERT_EQ(3, gs_vertex_get_key_count(vertex));
    
    // Keys should be returned in sorted order
    const char* key;
    gs_vertex_get_key_at_index(vertex, 0, &key);
    ASSERT_STR_EQ("apple", key);
    
    gs_vertex_get_key_at_index(vertex, 1, &key);
    ASSERT_STR_EQ("monkey", key);
    
    gs_vertex_get_key_at_index(vertex, 2, &key);
    ASSERT_STR_EQ("zebra", key);
    
    gs_vertex_destroy(vertex);
}

// Test vertex equality and hashing
TEST(vertex_equality_and_hashing) {
    // Empty vertices should be equal
    GraphserverVertex* v1 = gs_vertex_create(NULL, 0, NULL);
    GraphserverVertex* v2 = gs_vertex_create(NULL, 0, NULL);
    
    ASSERT(gs_vertex_equals(v1, v2));
    ASSERT_EQ(gs_vertex_hash(v1), gs_vertex_hash(v2));
    
    // Create vertices with same data
    GraphserverValue str_val1 = gs_value_create_string("test");
    GraphserverValue str_val2 = gs_value_create_string("test");
    GraphserverKeyPair pairs1[] = {
        {"number", gs_value_create_int(42)},
        {"text", str_val1}
    };
    GraphserverKeyPair pairs2[] = {
        {"number", gs_value_create_int(42)},
        {"text", str_val2}
    };
    
    GraphserverVertex* v3 = gs_vertex_create(pairs1, 2, NULL);
    GraphserverVertex* v4 = gs_vertex_create(pairs2, 2, NULL);
    
    // Should be equal (hash-based equality)
    ASSERT(gs_vertex_equals(v3, v4));
    ASSERT_EQ(gs_vertex_hash(v3), gs_vertex_hash(v4));
    
    // Create vertex with different data
    GraphserverKeyPair pairs3[] = {
        {"number", gs_value_create_int(24)}
    };
    GraphserverVertex* v5 = gs_vertex_create(pairs3, 1, NULL);
    
    // Should not be equal
    ASSERT(!gs_vertex_equals(v3, v5));
    ASSERT(!gs_vertex_equals(v1, v3)); // Empty vs non-empty
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
    gs_vertex_destroy(v4);
    gs_vertex_destroy(v5);
    
    // Clean up original string values
    gs_value_destroy(&str_val1);
    gs_value_destroy(&str_val2);
}

// Test vertex cloning
TEST(vertex_cloning) {
    // Create original vertex with data
    GraphserverValue str_val = gs_value_create_string("hello");
    GraphserverKeyPair pairs[] = {
        {"number", gs_value_create_int(42)},
        {"text", str_val}
    };
    
    GraphserverVertex* original = gs_vertex_create(pairs, 2, NULL);
    ASSERT_NOT_NULL(original);
    
    GraphserverVertex* clone = gs_vertex_clone(original);
    ASSERT_NOT_NULL(clone);
    
    // Should be equal but different objects
    ASSERT(gs_vertex_equals(original, clone));
    ASSERT(original != clone);
    
    // Hash should be preserved
    ASSERT_EQ(gs_vertex_hash(original), gs_vertex_hash(clone));
    
    // Both should have same key count
    ASSERT_EQ(2, gs_vertex_get_key_count(original));
    ASSERT_EQ(2, gs_vertex_get_key_count(clone));
    
    // Values should be the same
    GraphserverValue orig_val, clone_val;
    gs_vertex_get_value(original, "number", &orig_val);
    gs_vertex_get_value(clone, "number", &clone_val);
    ASSERT(gs_value_equals(&orig_val, &clone_val));
    
    gs_vertex_destroy(original);
    gs_vertex_destroy(clone);
    
    // Clean up original string value
    gs_value_destroy(&str_val);
}

// Test vertex string representation
TEST(vertex_string_representation) {
    GraphserverValue str_val = gs_value_create_string("hello");
    GraphserverKeyPair pairs[] = {
        {"number", gs_value_create_int(42)},
        {"greeting", str_val}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 2, NULL);
    ASSERT_NOT_NULL(vertex);
    
    char* str = gs_vertex_to_string(vertex);
    ASSERT_NOT_NULL(str);
    
    // Should contain the data (exact format may vary)
    ASSERT(strstr(str, "greeting") != NULL);
    ASSERT(strstr(str, "number") != NULL);
    ASSERT(strstr(str, "42") != NULL);
    ASSERT(strstr(str, "hello") != NULL);
    
    free(str);
    gs_vertex_destroy(vertex);
    
    // Clean up original string value
    gs_value_destroy(&str_val);
}

// Test error conditions
TEST(vertex_error_conditions) {
    // Create a vertex for testing
    GraphserverKeyPair pairs[] = {
        {"test", gs_value_create_int(42)}
    };
    GraphserverVertex* vertex = gs_vertex_create(pairs, 1, NULL);
    ASSERT_NOT_NULL(vertex);
    
    // NULL pointer checks for get_value
    GraphserverValue out_val;
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_get_value(NULL, "key", &out_val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_get_value(vertex, NULL, &out_val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_get_value(vertex, "key", NULL));
    
    // NULL pointer checks for has_key
    bool has_key;
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_has_key(NULL, "key", &has_key));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_has_key(vertex, NULL, &has_key));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_has_key(vertex, "key", NULL));
    
    gs_vertex_destroy(vertex);
}

// Test vertex with custom hash
TEST(vertex_custom_hash) {
    GraphserverKeyPair pairs[] = {
        {"x", gs_value_create_int(10)},
        {"y", gs_value_create_int(20)}
    };
    
    uint64_t custom_hash = 12345;
    GraphserverVertex* vertex = gs_vertex_create(pairs, 2, &custom_hash);
    ASSERT_NOT_NULL(vertex);
    ASSERT_EQ(custom_hash, gs_vertex_hash(vertex));
    
    // Create another vertex with same data but no custom hash
    GraphserverVertex* vertex2 = gs_vertex_create(pairs, 2, NULL);
    ASSERT_NOT_NULL(vertex2);
    
    // Should have different hashes
    ASSERT(gs_vertex_hash(vertex) != gs_vertex_hash(vertex2));
    
    // But should not be equal due to different hashes
    ASSERT(!gs_vertex_equals(vertex, vertex2));
    
    gs_vertex_destroy(vertex);
    gs_vertex_destroy(vertex2);
}

// Test vertex hash consistency
TEST(vertex_hash_consistency) {
    GraphserverValue str_val = gs_value_create_string("test");
    GraphserverKeyPair pairs[] = {
        {"name", str_val},
        {"value", gs_value_create_int(42)}
    };
    
    // Create multiple vertices with same data
    GraphserverVertex* v1 = gs_vertex_create(pairs, 2, NULL);
    GraphserverVertex* v2 = gs_vertex_create(pairs, 2, NULL);
    
    ASSERT_NOT_NULL(v1);
    ASSERT_NOT_NULL(v2);
    
    // Should have same hash
    ASSERT_EQ(gs_vertex_hash(v1), gs_vertex_hash(v2));
    
    // Should be equal
    ASSERT(gs_vertex_equals(v1, v2));
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    
    // Clean up original string value
    gs_value_destroy(&str_val);
}

// Test empty vertex hash behavior
TEST(vertex_empty_vertex_hash) {
    GraphserverVertex* empty1 = gs_vertex_create(NULL, 0, NULL);
    GraphserverVertex* empty2 = gs_vertex_create(NULL, 0, NULL);
    
    ASSERT_NOT_NULL(empty1);
    ASSERT_NOT_NULL(empty2);
    
    // Empty vertices should have hash 0
    ASSERT_EQ(0, gs_vertex_hash(empty1));
    ASSERT_EQ(0, gs_vertex_hash(empty2));
    
    // Should be equal
    ASSERT(gs_vertex_equals(empty1, empty2));
    
    // Test empty vertex with custom hash
    uint64_t custom_hash = 99999;
    GraphserverVertex* empty3 = gs_vertex_create(NULL, 0, &custom_hash);
    ASSERT_NOT_NULL(empty3);
    ASSERT_EQ(custom_hash, gs_vertex_hash(empty3));
    
    // Should not be equal to other empty vertices
    ASSERT(!gs_vertex_equals(empty1, empty3));
    
    gs_vertex_destroy(empty1);
    gs_vertex_destroy(empty2);
    gs_vertex_destroy(empty3);
}

// Test vertex immutability (verify no mutation functions exist)
TEST(vertex_immutability) {
    GraphserverValue str_val = gs_value_create_string("forever");
    GraphserverKeyPair pairs[] = {
        {"immutable", str_val}
    };
    
    GraphserverVertex* vertex = gs_vertex_create(pairs, 1, NULL);
    ASSERT_NOT_NULL(vertex);
    
    // Store original hash
    uint64_t original_hash = gs_vertex_hash(vertex);
    
    // Verify we can read data
    GraphserverValue val;
    GraphserverResult result = gs_vertex_get_value(vertex, "immutable", &val);
    ASSERT_EQ(GS_SUCCESS, result);
    ASSERT_EQ(GS_VALUE_STRING, val.type);
    ASSERT_STR_EQ("forever", val.as.s_val);
    gs_value_destroy(&val);
    
    // Hash should remain unchanged
    ASSERT_EQ(original_hash, gs_vertex_hash(vertex));
    
    // Key count should remain the same
    ASSERT_EQ(1, gs_vertex_get_key_count(vertex));
    
    gs_vertex_destroy(vertex);
    
    // Clean up original string value
    gs_value_destroy(&str_val);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Vertex Tests (Immutable)\n");
    printf("============================================\n");
    
    run_test_value_creation();
    run_test_value_equality();
    run_test_value_copying();
    run_test_vertex_lifecycle();
    run_test_vertex_immutable_access();
    run_test_vertex_key_ordering();
    run_test_vertex_equality_and_hashing();
    run_test_vertex_cloning();
    run_test_vertex_string_representation();
    run_test_vertex_error_conditions();
    run_test_vertex_custom_hash();
    run_test_vertex_hash_consistency();
    run_test_vertex_empty_vertex_hash();
    run_test_vertex_immutability();
    
    printf("\n============================================\n");
    printf("Tests completed: %d/%d passed\n", tests_passed, tests_run);
    
    if (tests_passed == tests_run) {
        printf("All tests PASSED!\n");
        return 0;
    } else {
        printf("Some tests FAILED!\n");
        return 1;
    }
}