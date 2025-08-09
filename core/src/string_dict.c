#include "../include/gs_string_dict.h"
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <assert.h>

/**
 * @file string_dict.c
 * @brief Implementation of the thread-safe string dictionary
 */

// Initial capacity for the dictionary
#define INITIAL_CAPACITY 256

// Maximum number of strings (uint16_t max - 1, since 0 is reserved)
#define MAX_STRINGS 65535

// Global dictionary structure
typedef struct {
    char** strings;           // Array of interned strings
    uint16_t* string_ids;     // Maps to check for duplicates (not used in initial impl)
    size_t count;            // Current number of strings
    size_t capacity;         // Allocated capacity
    pthread_rwlock_t lock;   // Read-write lock for thread safety
    bool initialized;        // Initialization flag
} StringDict;

// Global dictionary instance
static StringDict g_dict = {0};

// Helper function to duplicate a string
static char* duplicate_string(const char* str) {
    if (!str) return NULL;
    
    size_t len = strlen(str);
    char* copy = malloc(len + 1);
    if (!copy) return NULL;
    
    memcpy(copy, str, len + 1);
    return copy;
}

// Helper function to expand capacity
static bool expand_capacity(StringDict* dict) {
    if (dict->capacity >= MAX_STRINGS) {
        return false;  // Cannot expand beyond uint16_t range
    }
    
    size_t new_capacity = dict->capacity * 2;
    if (new_capacity > MAX_STRINGS) {
        new_capacity = MAX_STRINGS;
    }
    
    char** new_strings = realloc(dict->strings, sizeof(char*) * new_capacity);
    if (!new_strings) {
        return false;
    }
    
    dict->strings = new_strings;
    dict->capacity = new_capacity;
    return true;
}

// Helper function to find string in dictionary (assumes read lock is held)
static uint16_t find_string_id(const StringDict* dict, const char* str) {
    for (size_t i = 0; i < dict->count; i++) {
        if (strcmp(dict->strings[i], str) == 0) {
            return (uint16_t)(i + 1);  // IDs start from 1
        }
    }
    return GS_INVALID_KEY_ID;
}

void gs_string_dict_init(void) {
    if (g_dict.initialized) {
        return;  // Already initialized
    }
    
    // Initialize the dictionary
    g_dict.strings = malloc(sizeof(char*) * INITIAL_CAPACITY);
    g_dict.string_ids = NULL;  // Not used in this simple implementation
    g_dict.count = 0;
    g_dict.capacity = INITIAL_CAPACITY;
    
    if (!g_dict.strings) {
        return;  // Initialization failed
    }
    
    // Initialize the read-write lock
    if (pthread_rwlock_init(&g_dict.lock, NULL) != 0) {
        free(g_dict.strings);
        g_dict.strings = NULL;
        return;
    }
    
    g_dict.initialized = true;
}

void gs_string_dict_cleanup(void) {
    if (!g_dict.initialized) {
        return;
    }
    
    // Acquire write lock
    pthread_rwlock_wrlock(&g_dict.lock);
    
    // Free all strings
    for (size_t i = 0; i < g_dict.count; i++) {
        free(g_dict.strings[i]);
    }
    
    // Free arrays
    free(g_dict.strings);
    free(g_dict.string_ids);
    
    // Reset state
    g_dict.strings = NULL;
    g_dict.string_ids = NULL;
    g_dict.count = 0;
    g_dict.capacity = 0;
    g_dict.initialized = false;
    
    // Release and destroy lock
    pthread_rwlock_unlock(&g_dict.lock);
    pthread_rwlock_destroy(&g_dict.lock);
}

uint16_t gs_string_dict_register(const char* str) {
    if (!str || !g_dict.initialized) {
        return GS_INVALID_KEY_ID;
    }
    
    // First, try to find the string with a read lock
    pthread_rwlock_rdlock(&g_dict.lock);
    uint16_t existing_id = find_string_id(&g_dict, str);
    pthread_rwlock_unlock(&g_dict.lock);
    
    if (existing_id != GS_INVALID_KEY_ID) {
        return existing_id;  // String already exists
    }
    
    // String doesn't exist, need to add it with write lock
    pthread_rwlock_wrlock(&g_dict.lock);
    
    // Double-check in case another thread added it while we were waiting
    existing_id = find_string_id(&g_dict, str);
    if (existing_id != GS_INVALID_KEY_ID) {
        pthread_rwlock_unlock(&g_dict.lock);
        return existing_id;
    }
    
    // Check if we need to expand capacity
    if (g_dict.count >= g_dict.capacity) {
        if (!expand_capacity(&g_dict)) {
            pthread_rwlock_unlock(&g_dict.lock);
            return GS_INVALID_KEY_ID;  // Failed to expand
        }
    }
    
    // Check if we've reached the maximum number of strings
    if (g_dict.count >= MAX_STRINGS) {
        pthread_rwlock_unlock(&g_dict.lock);
        return GS_INVALID_KEY_ID;
    }
    
    // Duplicate the string
    char* str_copy = duplicate_string(str);
    if (!str_copy) {
        pthread_rwlock_unlock(&g_dict.lock);
        return GS_INVALID_KEY_ID;
    }
    
    // Add to dictionary
    g_dict.strings[g_dict.count] = str_copy;
    uint16_t new_id = (uint16_t)(g_dict.count + 1);  // IDs start from 1
    g_dict.count++;
    
    pthread_rwlock_unlock(&g_dict.lock);
    return new_id;
}

const char* gs_string_dict_get(uint16_t id) {
    if (id == GS_INVALID_KEY_ID || !g_dict.initialized) {
        return NULL;
    }
    
    pthread_rwlock_rdlock(&g_dict.lock);
    
    // Convert ID to array index (IDs start from 1)
    size_t index = id - 1;
    const char* result = NULL;
    
    if (index < g_dict.count) {
        result = g_dict.strings[index];
    }
    
    pthread_rwlock_unlock(&g_dict.lock);
    return result;
}

void gs_string_dict_register_batch(const char** strings, uint16_t* ids, size_t count) {
    if (!strings || !ids || count == 0 || !g_dict.initialized) {
        // Set all IDs to invalid if inputs are invalid
        if (ids && count > 0) {
            for (size_t i = 0; i < count; i++) {
                ids[i] = GS_INVALID_KEY_ID;
            }
        }
        return;
    }
    
    // Acquire write lock for the entire batch operation
    pthread_rwlock_wrlock(&g_dict.lock);
    
    for (size_t i = 0; i < count; i++) {
        if (!strings[i]) {
            ids[i] = GS_INVALID_KEY_ID;
            continue;
        }
        
        // Check if string already exists
        uint16_t existing_id = find_string_id(&g_dict, strings[i]);
        if (existing_id != GS_INVALID_KEY_ID) {
            ids[i] = existing_id;
            continue;
        }
        
        // Check capacity and limits
        if (g_dict.count >= g_dict.capacity) {
            if (!expand_capacity(&g_dict)) {
                ids[i] = GS_INVALID_KEY_ID;
                continue;
            }
        }
        
        if (g_dict.count >= MAX_STRINGS) {
            ids[i] = GS_INVALID_KEY_ID;
            continue;
        }
        
        // Add new string
        char* str_copy = duplicate_string(strings[i]);
        if (!str_copy) {
            ids[i] = GS_INVALID_KEY_ID;
            continue;
        }
        
        g_dict.strings[g_dict.count] = str_copy;
        ids[i] = (uint16_t)(g_dict.count + 1);
        g_dict.count++;
    }
    
    pthread_rwlock_unlock(&g_dict.lock);
}

bool gs_string_dict_contains(const char* str) {
    if (!str || !g_dict.initialized) {
        return false;
    }
    
    pthread_rwlock_rdlock(&g_dict.lock);
    bool found = (find_string_id(&g_dict, str) != GS_INVALID_KEY_ID);
    pthread_rwlock_unlock(&g_dict.lock);
    
    return found;
}

size_t gs_string_dict_size(void) {
    if (!g_dict.initialized) {
        return 0;
    }
    
    pthread_rwlock_rdlock(&g_dict.lock);
    size_t size = g_dict.count;
    pthread_rwlock_unlock(&g_dict.lock);
    
    return size;
}

bool gs_string_dict_is_initialized(void) {
    return g_dict.initialized;
}