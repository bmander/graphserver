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
    GraphserverVertex* vertex = gs_vertex_create();
    ASSERT_NOT_NULL(vertex);
    ASSERT_EQ(0, gs_vertex_get_key_count(vertex));
    
    gs_vertex_destroy(vertex);
    // Should not crash
}

// Test vertex key-value operations
TEST(vertex_key_value_ops) {
    GraphserverVertex* vertex = gs_vertex_create();
    
    // Set some values
    GraphserverValue int_val = gs_value_create_int(42);
    GraphserverResult result = gs_vertex_set_kv(vertex, "number", int_val);
    ASSERT_EQ(GS_SUCCESS, result);
    
    GraphserverValue str_val = gs_value_create_string("hello");
    result = gs_vertex_set_kv(vertex, "greeting", str_val);
    ASSERT_EQ(GS_SUCCESS, result);
    
    ASSERT_EQ(2, gs_vertex_get_key_count(vertex));
    
    // Check if keys exist
    bool has_key;
    result = gs_vertex_has_key(vertex, "number", &has_key);
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
}

// Test vertex key ordering (keys should be stored in sorted order)
TEST(vertex_key_ordering) {
    GraphserverVertex* vertex = gs_vertex_create();
    
    // Add keys in non-alphabetical order
    GraphserverValue val1 = gs_value_create_int(1);
    GraphserverValue val2 = gs_value_create_int(2);
    GraphserverValue val3 = gs_value_create_int(3);
    
    gs_vertex_set_kv(vertex, "zebra", val1);
    gs_vertex_set_kv(vertex, "apple", val2);
    gs_vertex_set_kv(vertex, "monkey", val3);
    
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
    GraphserverVertex* v1 = gs_vertex_create();
    GraphserverVertex* v2 = gs_vertex_create();
    GraphserverVertex* v3 = gs_vertex_create();
    
    // Empty vertices should be equal
    ASSERT(gs_vertex_equals(v1, v2));
    ASSERT_EQ(gs_vertex_hash(v1), gs_vertex_hash(v2));
    
    // Add same data to v1 and v2
    GraphserverValue val1 = gs_value_create_int(42);
    GraphserverValue val2 = gs_value_create_string("test");
    gs_vertex_set_kv(v1, "number", val1);
    gs_vertex_set_kv(v1, "text", val2);
    
    GraphserverValue val3 = gs_value_create_int(42);
    GraphserverValue val4 = gs_value_create_string("test");
    gs_vertex_set_kv(v2, "number", val3);
    gs_vertex_set_kv(v2, "text", val4);
    
    // Should be equal
    ASSERT(gs_vertex_equals(v1, v2));
    ASSERT_EQ(gs_vertex_hash(v1), gs_vertex_hash(v2));
    
    // Add different data to v3
    GraphserverValue val5 = gs_value_create_int(24);
    gs_vertex_set_kv(v3, "number", val5);
    
    // Should not be equal
    ASSERT(!gs_vertex_equals(v1, v3));
    // Hashes might be different (not guaranteed, but likely)
    
    gs_vertex_destroy(v1);
    gs_vertex_destroy(v2);
    gs_vertex_destroy(v3);
}

// Test vertex cloning
TEST(vertex_cloning) {
    GraphserverVertex* original = gs_vertex_create();
    
    GraphserverValue val1 = gs_value_create_int(42);
    GraphserverValue val2 = gs_value_create_string("hello");
    gs_vertex_set_kv(original, "number", val1);
    gs_vertex_set_kv(original, "text", val2);
    
    GraphserverVertex* clone = gs_vertex_clone(original);
    ASSERT_NOT_NULL(clone);
    
    // Should be equal but different objects
    ASSERT(gs_vertex_equals(original, clone));
    ASSERT(original != clone);
    
    // Modifying clone shouldn't affect original
    GraphserverValue val3 = gs_value_create_int(99);
    gs_vertex_set_kv(clone, "new_key", val3);
    
    ASSERT(!gs_vertex_equals(original, clone));
    ASSERT_EQ(2, gs_vertex_get_key_count(original));
    ASSERT_EQ(3, gs_vertex_get_key_count(clone));
    
    gs_vertex_destroy(original);
    gs_vertex_destroy(clone);
}

// Test vertex string representation
TEST(vertex_string_representation) {
    GraphserverVertex* vertex = gs_vertex_create();
    
    GraphserverValue val1 = gs_value_create_int(42);
    GraphserverValue val2 = gs_value_create_string("hello");
    gs_vertex_set_kv(vertex, "number", val1);
    gs_vertex_set_kv(vertex, "greeting", val2);
    
    char* str = gs_vertex_to_string(vertex);
    ASSERT_NOT_NULL(str);
    
    // Should contain the data (exact format may vary)
    ASSERT(strstr(str, "greeting") != NULL);
    ASSERT(strstr(str, "number") != NULL);
    ASSERT(strstr(str, "42") != NULL);
    ASSERT(strstr(str, "hello") != NULL);
    
    free(str);
    gs_vertex_destroy(vertex);
}

// Test error conditions
TEST(vertex_error_conditions) {
    // NULL pointer checks
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_set_kv(NULL, "key", gs_value_create_int(1)));
    
    GraphserverVertex* vertex = gs_vertex_create();
    GraphserverValue val = gs_value_create_int(1);
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_set_kv(vertex, NULL, val));
    
    GraphserverValue out_val;
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_get_value(NULL, "key", &out_val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_get_value(vertex, NULL, &out_val));
    ASSERT_EQ(GS_ERROR_NULL_POINTER, gs_vertex_get_value(vertex, "key", NULL));
    
    gs_vertex_destroy(vertex);
}

// Main test runner
int main(void) {
    printf("Running Graphserver Vertex Tests\n");
    printf("=================================\n");
    
    run_test_value_creation();
    run_test_value_equality();
    run_test_value_copying();
    run_test_vertex_lifecycle();
    run_test_vertex_key_value_ops();
    run_test_vertex_key_ordering();
    run_test_vertex_equality_and_hashing();
    run_test_vertex_cloning();
    run_test_vertex_string_representation();
    run_test_vertex_error_conditions();
    
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