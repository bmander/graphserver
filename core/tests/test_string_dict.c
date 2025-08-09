#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>

#include "../include/gs_string_dict.h"
#include "../include/gs_common_keys.h"
#include "test_utils.h"

/**
 * @file test_string_dict.c
 * @brief Unit tests for the string dictionary
 */

// Test initialization and cleanup
void test_initialization(void) {
    printf("Testing initialization and cleanup...\n");
    
    // Test double initialization (should be safe)
    gs_string_dict_init();
    gs_string_dict_init();
    assert(gs_string_dict_is_initialized());
    
    // Test basic functionality
    assert(gs_string_dict_size() == 0);
    
    gs_string_dict_cleanup();
    assert(!gs_string_dict_is_initialized());
    assert(gs_string_dict_size() == 0);
    
    printf("✓ Initialization and cleanup tests passed\n");
}

// Test basic registration and lookup
void test_basic_operations(void) {
    printf("Testing basic registration and lookup...\n");
    
    gs_string_dict_init();
    
    // Test registering new strings
    uint16_t id1 = gs_string_dict_register("test1");
    uint16_t id2 = gs_string_dict_register("test2");
    
    assert(id1 != GS_INVALID_KEY_ID);
    assert(id2 != GS_INVALID_KEY_ID);
    assert(id1 != id2);
    assert(gs_string_dict_size() == 2);
    
    // Test lookups
    const char* str1 = gs_string_dict_get(id1);
    const char* str2 = gs_string_dict_get(id2);
    
    assert(str1 != NULL);
    assert(str2 != NULL);
    assert(strcmp(str1, "test1") == 0);
    assert(strcmp(str2, "test2") == 0);
    
    // Test duplicate registration returns same ID
    uint16_t id1_dup = gs_string_dict_register("test1");
    assert(id1_dup == id1);
    assert(gs_string_dict_size() == 2);  // Size shouldn't increase
    
    // Test contains function
    assert(gs_string_dict_contains("test1"));
    assert(gs_string_dict_contains("test2"));
    assert(!gs_string_dict_contains("nonexistent"));
    
    gs_string_dict_cleanup();
    printf("✓ Basic operations tests passed\n");
}

// Test edge cases
void test_edge_cases(void) {
    printf("Testing edge cases...\n");
    
    gs_string_dict_init();
    
    // Test NULL string registration
    uint16_t null_id = gs_string_dict_register(NULL);
    assert(null_id == GS_INVALID_KEY_ID);
    
    // Test empty string
    uint16_t empty_id = gs_string_dict_register("");
    assert(empty_id != GS_INVALID_KEY_ID);
    assert(strcmp(gs_string_dict_get(empty_id), "") == 0);
    
    // Test very long string
    char long_string[1000];
    memset(long_string, 'a', sizeof(long_string) - 1);
    long_string[sizeof(long_string) - 1] = '\0';
    
    uint16_t long_id = gs_string_dict_register(long_string);
    assert(long_id != GS_INVALID_KEY_ID);
    assert(strcmp(gs_string_dict_get(long_id), long_string) == 0);
    
    // Test invalid ID lookup
    assert(gs_string_dict_get(GS_INVALID_KEY_ID) == NULL);
    assert(gs_string_dict_get(65535) == NULL);  // Non-existent high ID
    
    // Test contains with NULL
    assert(!gs_string_dict_contains(NULL));
    
    gs_string_dict_cleanup();
    printf("✓ Edge cases tests passed\n");
}

// Test batch operations
void test_batch_operations(void) {
    printf("Testing batch operations...\n");
    
    gs_string_dict_init();
    
    // Test batch registration
    const char* strings[] = {"batch1", "batch2", "batch3", "batch1"};  // Note duplicate
    uint16_t ids[4];
    
    gs_string_dict_register_batch(strings, ids, 4);
    
    assert(ids[0] != GS_INVALID_KEY_ID);
    assert(ids[1] != GS_INVALID_KEY_ID);
    assert(ids[2] != GS_INVALID_KEY_ID);
    assert(ids[3] == ids[0]);  // Duplicate should have same ID
    
    assert(gs_string_dict_size() == 3);  // Only 3 unique strings
    
    // Verify lookups
    assert(strcmp(gs_string_dict_get(ids[0]), "batch1") == 0);
    assert(strcmp(gs_string_dict_get(ids[1]), "batch2") == 0);
    assert(strcmp(gs_string_dict_get(ids[2]), "batch3") == 0);
    
    // Test batch with NULL
    const char* strings_with_null[] = {"valid", NULL, "also_valid"};
    uint16_t ids_with_null[3];
    
    gs_string_dict_register_batch(strings_with_null, ids_with_null, 3);
    
    assert(ids_with_null[0] != GS_INVALID_KEY_ID);
    assert(ids_with_null[1] == GS_INVALID_KEY_ID);
    assert(ids_with_null[2] != GS_INVALID_KEY_ID);
    
    gs_string_dict_cleanup();
    printf("✓ Batch operations tests passed\n");
}

// Test common keys initialization
void test_common_keys(void) {
    printf("Testing common keys...\n");
    
    gs_string_dict_init();
    assert(gs_common_keys_init());
    assert(gs_common_keys_is_initialized());
    
    // Test that common keys are registered and valid
    assert(GS_KEY_LAT != GS_INVALID_KEY_ID);
    assert(GS_KEY_LON != GS_INVALID_KEY_ID);
    assert(GS_KEY_MODE != GS_INVALID_KEY_ID);
    assert(GS_KEY_TIME != GS_INVALID_KEY_ID);
    
    // Test that keys map to correct strings
    assert(strcmp(gs_string_dict_get(GS_KEY_LAT), "lat") == 0);
    assert(strcmp(gs_string_dict_get(GS_KEY_LON), "lon") == 0);
    assert(strcmp(gs_string_dict_get(GS_KEY_MODE), "mode") == 0);
    assert(strcmp(gs_string_dict_get(GS_KEY_TIME), "time") == 0);
    
    // Test re-initialization (should be safe)
    assert(gs_common_keys_init());
    
    gs_string_dict_cleanup();
    printf("✓ Common keys tests passed\n");
}

// Thread data for concurrent tests
typedef struct {
    int thread_id;
    int num_registrations;
    uint16_t* results;
} ThreadData;

// Thread function for testing concurrent registration
void* thread_register_strings(void* arg) {
    ThreadData* data = (ThreadData*)arg;
    char buffer[64];
    
    for (int i = 0; i < data->num_registrations; i++) {
        snprintf(buffer, sizeof(buffer), "thread_%d_string_%d", data->thread_id, i);
        data->results[i] = gs_string_dict_register(buffer);
    }
    
    return NULL;
}

// Test thread safety
void test_thread_safety(void) {
    printf("Testing thread safety...\n");
    
    gs_string_dict_init();
    
    const int num_threads = 4;
    const int registrations_per_thread = 100;
    
    pthread_t threads[num_threads];
    ThreadData thread_data[num_threads];
    uint16_t results[num_threads][registrations_per_thread];
    
    // Start threads
    for (int i = 0; i < num_threads; i++) {
        thread_data[i].thread_id = i;
        thread_data[i].num_registrations = registrations_per_thread;
        thread_data[i].results = results[i];
        
        int rc = pthread_create(&threads[i], NULL, thread_register_strings, &thread_data[i]);
        assert(rc == 0);
    }
    
    // Wait for threads to complete
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }
    
    // Verify results
    size_t expected_size = num_threads * registrations_per_thread;
    assert(gs_string_dict_size() == expected_size);
    
    // Check that all IDs are valid and unique
    uint16_t all_ids[num_threads * registrations_per_thread];
    int id_count = 0;
    
    for (int i = 0; i < num_threads; i++) {
        for (int j = 0; j < registrations_per_thread; j++) {
            assert(results[i][j] != GS_INVALID_KEY_ID);
            all_ids[id_count++] = results[i][j];
        }
    }
    
    // Check uniqueness (simple O(n^2) check for small test)
    for (int i = 0; i < id_count; i++) {
        for (int j = i + 1; j < id_count; j++) {
            assert(all_ids[i] != all_ids[j]);
        }
    }
    
    gs_string_dict_cleanup();
    printf("✓ Thread safety tests passed\n");
}

// Test capacity expansion
void test_capacity_expansion(void) {
    printf("Testing capacity expansion...\n");
    
    gs_string_dict_init();
    
    // Register enough strings to force capacity expansion
    const size_t num_strings = 300;  // More than initial capacity
    char buffer[64];
    
    for (size_t i = 0; i < num_strings; i++) {
        snprintf(buffer, sizeof(buffer), "expand_test_%zu", i);
        uint16_t id = gs_string_dict_register(buffer);
        assert(id != GS_INVALID_KEY_ID);
    }
    
    assert(gs_string_dict_size() == num_strings);
    
    // Verify all strings can still be looked up correctly
    for (size_t i = 0; i < num_strings; i++) {
        snprintf(buffer, sizeof(buffer), "expand_test_%zu", i);
        assert(gs_string_dict_contains(buffer));
    }
    
    gs_string_dict_cleanup();
    printf("✓ Capacity expansion tests passed\n");
}

int main(void) {
    printf("Running string dictionary tests...\n");
    
    test_initialization();
    test_basic_operations();
    test_edge_cases();
    test_batch_operations();
    test_common_keys();
    test_thread_safety();
    test_capacity_expansion();
    
    printf("\n✅ All string dictionary tests passed!\n");
    return 0;
}