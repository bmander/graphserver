#include "../include/gs_vertex.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>

// Internal vertex structure
struct GraphserverVertex {
    GraphserverKeyPair* pairs;
    size_t num_pairs;
    uint64_t hash;           // Stored hash value
    bool hash_provided;      // Whether hash was provided at creation
};

// Hash function (FNV-1a)
static uint64_t hash_bytes(const void* data, size_t len) {
    const uint8_t* bytes = (const uint8_t*)data;
    uint64_t hash = 14695981039346656037ULL;
    
    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= 1099511628211ULL;
    }
    
    return hash;
}

// String duplication
static char* duplicate_string(const char* str) {
    if (!str) return NULL;
    
    size_t len = strlen(str);
    char* copy = malloc(len + 1);
    if (!copy) return NULL;
    
    memcpy(copy, str, len + 1);
    return copy;
}

// Array duplication helper
static void* duplicate_array(const void* data, size_t element_size, size_t count) {
    if (!data || count == 0) return NULL;
    
    size_t total_size = element_size * count;
    void* copy = malloc(total_size);
    if (!copy) return NULL;
    
    memcpy(copy, data, total_size);
    return copy;
}

// String array duplication
static char** duplicate_string_array(const char* const* data, size_t count) {
    if (!data || count == 0) return NULL;
    
    char** copy = malloc(sizeof(char*) * count);
    if (!copy) return NULL;
    
    for (size_t i = 0; i < count; i++) {
        copy[i] = duplicate_string(data[i]);
        if (!copy[i]) {
            // Cleanup on failure
            for (size_t j = 0; j < i; j++) {
                free(copy[j]);
            }
            free(copy);
            return NULL;
        }
    }
    
    return copy;
}

// Compare key-value pairs by key for sorting
static int compare_key_pairs(const void* a, const void* b) {
    const GraphserverKeyPair* pair_a = (const GraphserverKeyPair*)a;
    const GraphserverKeyPair* pair_b = (const GraphserverKeyPair*)b;
    return strcmp(pair_a->key, pair_b->key);
}

// Calculate hash for vertex data
static uint64_t calculate_vertex_hash(const GraphserverKeyPair* pairs, size_t num_pairs) {
    if (!pairs || num_pairs == 0) return 0;
    
    uint64_t hash = 14695981039346656037ULL;
    
    for (size_t i = 0; i < num_pairs; i++) {
        // Hash the key
        hash ^= hash_bytes(pairs[i].key, strlen(pairs[i].key));
        hash *= 1099511628211ULL;
        
        // Hash the value based on its type
        const GraphserverValue* value = &pairs[i].value;
        hash ^= hash_bytes(&value->type, sizeof(value->type));
        hash *= 1099511628211ULL;
        
        switch (value->type) {
            case GS_VALUE_INT:
                hash ^= hash_bytes(&value->as.i_val, sizeof(value->as.i_val));
                break;
            case GS_VALUE_FLOAT:
                hash ^= hash_bytes(&value->as.f_val, sizeof(value->as.f_val));
                break;
            case GS_VALUE_BOOL:
                hash ^= hash_bytes(&value->as.b_val, sizeof(value->as.b_val));
                break;
            case GS_VALUE_STRING:
                if (value->as.s_val) {
                    hash ^= hash_bytes(value->as.s_val, strlen(value->as.s_val));
                }
                break;
            case GS_VALUE_INT_ARRAY:
            case GS_VALUE_FLOAT_ARRAY:
            case GS_VALUE_BOOL_ARRAY:
                hash ^= hash_bytes(&value->as.array_val.size, sizeof(value->as.array_val.size));
                if (value->as.array_val.data) {
                    size_t element_size = (value->type == GS_VALUE_INT_ARRAY) ? sizeof(int64_t) :
                                        (value->type == GS_VALUE_FLOAT_ARRAY) ? sizeof(double) : sizeof(bool);
                    hash ^= hash_bytes(value->as.array_val.data, 
                                    value->as.array_val.size * element_size);
                }
                break;
            case GS_VALUE_STRING_ARRAY:
                hash ^= hash_bytes(&value->as.array_val.size, sizeof(value->as.array_val.size));
                if (value->as.array_val.data) {
                    char** strings = (char**)value->as.array_val.data;
                    for (size_t j = 0; j < value->as.array_val.size; j++) {
                        if (strings[j]) {
                            hash ^= hash_bytes(strings[j], strlen(strings[j]));
                        }
                    }
                }
                break;
        }
        hash *= 1099511628211ULL;
    }
    
    return hash;
}

// Value creation functions
GraphserverValue gs_value_create_int(int64_t val) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_INT;
    value.as.i_val = val;
    return value;
}

GraphserverValue gs_value_create_float(double val) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_FLOAT;
    value.as.f_val = val;
    return value;
}

GraphserverValue gs_value_create_string(const char* val) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_STRING;
    value.as.s_val = duplicate_string(val);
    return value;
}

GraphserverValue gs_value_create_bool(bool val) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_BOOL;
    value.as.b_val = val;
    return value;
}

GraphserverValue gs_value_create_int_array(const int64_t* data, size_t size) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_INT_ARRAY;
    value.as.array_val.size = size;
    value.as.array_val.data = duplicate_array(data, sizeof(int64_t), size);
    return value;
}

GraphserverValue gs_value_create_float_array(const double* data, size_t size) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_FLOAT_ARRAY;
    value.as.array_val.size = size;
    value.as.array_val.data = duplicate_array(data, sizeof(double), size);
    return value;
}

GraphserverValue gs_value_create_string_array(const char* const* data, size_t size) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_STRING_ARRAY;
    value.as.array_val.size = size;
    value.as.array_val.data = duplicate_string_array(data, size);
    return value;
}

GraphserverValue gs_value_create_bool_array(const bool* data, size_t size) {
    GraphserverValue value = {0};
    value.type = GS_VALUE_BOOL_ARRAY;
    value.as.array_val.size = size;
    value.as.array_val.data = duplicate_array(data, sizeof(bool), size);
    return value;
}

// Value destruction
void gs_value_destroy(GraphserverValue* value) {
    if (!value) return;
    
    switch (value->type) {
        case GS_VALUE_STRING:
            free((void*)value->as.s_val);
            break;
        case GS_VALUE_INT_ARRAY:
        case GS_VALUE_FLOAT_ARRAY:
        case GS_VALUE_BOOL_ARRAY:
            free(value->as.array_val.data);
            break;
        case GS_VALUE_STRING_ARRAY:
            if (value->as.array_val.data) {
                char** strings = (char**)value->as.array_val.data;
                for (size_t i = 0; i < value->as.array_val.size; i++) {
                    free(strings[i]);
                }
                free(strings);
            }
            break;
        default:
            // Primitive types don't need cleanup
            break;
    }
    
    memset(value, 0, sizeof(GraphserverValue));
}

// Value comparison
bool gs_value_equals(const GraphserverValue* a, const GraphserverValue* b) {
    if (!a || !b || a->type != b->type) return false;
    
    switch (a->type) {
        case GS_VALUE_INT:
            return a->as.i_val == b->as.i_val;
        case GS_VALUE_FLOAT:
            return a->as.f_val == b->as.f_val;
        case GS_VALUE_BOOL:
            return a->as.b_val == b->as.b_val;
        case GS_VALUE_STRING:
            if (!a->as.s_val && !b->as.s_val) return true;
            if (!a->as.s_val || !b->as.s_val) return false;
            return strcmp(a->as.s_val, b->as.s_val) == 0;
        case GS_VALUE_INT_ARRAY:
            if (a->as.array_val.size != b->as.array_val.size) return false;
            return memcmp(a->as.array_val.data, b->as.array_val.data, 
                         a->as.array_val.size * sizeof(int64_t)) == 0;
        case GS_VALUE_FLOAT_ARRAY:
            if (a->as.array_val.size != b->as.array_val.size) return false;
            return memcmp(a->as.array_val.data, b->as.array_val.data, 
                         a->as.array_val.size * sizeof(double)) == 0;
        case GS_VALUE_BOOL_ARRAY:
            if (a->as.array_val.size != b->as.array_val.size) return false;
            return memcmp(a->as.array_val.data, b->as.array_val.data, 
                         a->as.array_val.size * sizeof(bool)) == 0;
        case GS_VALUE_STRING_ARRAY:
            if (a->as.array_val.size != b->as.array_val.size) return false;
            char** a_strings = (char**)a->as.array_val.data;
            char** b_strings = (char**)b->as.array_val.data;
            for (size_t i = 0; i < a->as.array_val.size; i++) {
                if (strcmp(a_strings[i], b_strings[i]) != 0) return false;
            }
            return true;
    }
    
    return false;
}

// Value copying
GraphserverValue gs_value_copy(const GraphserverValue* value) {
    if (!value) {
        GraphserverValue empty = {0};
        return empty;
    }
    
    switch (value->type) {
        case GS_VALUE_INT:
            return gs_value_create_int(value->as.i_val);
        case GS_VALUE_FLOAT:
            return gs_value_create_float(value->as.f_val);
        case GS_VALUE_BOOL:
            return gs_value_create_bool(value->as.b_val);
        case GS_VALUE_STRING:
            return gs_value_create_string(value->as.s_val);
        case GS_VALUE_INT_ARRAY:
            return gs_value_create_int_array((const int64_t*)value->as.array_val.data, 
                                           value->as.array_val.size);
        case GS_VALUE_FLOAT_ARRAY:
            return gs_value_create_float_array((const double*)value->as.array_val.data, 
                                             value->as.array_val.size);
        case GS_VALUE_BOOL_ARRAY:
            return gs_value_create_bool_array((const bool*)value->as.array_val.data, 
                                            value->as.array_val.size);
        case GS_VALUE_STRING_ARRAY:
            return gs_value_create_string_array((const char* const*)value->as.array_val.data, 
                                              value->as.array_val.size);
    }
    
    GraphserverValue empty = {0};
    return empty;
}

// Vertex lifecycle
GraphserverVertex* gs_vertex_create(const GraphserverKeyPair* pairs, size_t num_pairs, const uint64_t* optional_hash) {
    GraphserverVertex* vertex = malloc(sizeof(GraphserverVertex));
    if (!vertex) return NULL;
    
    // Initialize vertex
    vertex->pairs = NULL;
    vertex->num_pairs = num_pairs;
    vertex->hash_provided = (optional_hash != NULL);
    
    // Handle empty vertex
    if (num_pairs == 0) {
        vertex->hash = optional_hash ? *optional_hash : 0;
        return vertex;
    }
    
    // Allocate memory for pairs
    vertex->pairs = malloc(sizeof(GraphserverKeyPair) * num_pairs);
    if (!vertex->pairs) {
        free(vertex);
        return NULL;
    }
    
    // Copy and sort the pairs
    for (size_t i = 0; i < num_pairs; i++) {
        // Duplicate the key
        vertex->pairs[i].key = duplicate_string(pairs[i].key);
        if (!vertex->pairs[i].key) {
            // Cleanup on failure
            for (size_t j = 0; j < i; j++) {
                free((void*)vertex->pairs[j].key);
                gs_value_destroy(&vertex->pairs[j].value);
            }
            free(vertex->pairs);
            free(vertex);
            return NULL;
        }
        
        // Copy the value
        vertex->pairs[i].value = gs_value_copy(&pairs[i].value);
    }
    
    // Sort pairs by key for consistent ordering
    qsort(vertex->pairs, num_pairs, sizeof(GraphserverKeyPair), compare_key_pairs);
    
    // Set hash
    if (optional_hash) {
        vertex->hash = *optional_hash;
    } else {
        vertex->hash = calculate_vertex_hash(vertex->pairs, num_pairs);
    }
    
    return vertex;
}

void gs_vertex_destroy(GraphserverVertex* vertex) {
    if (!vertex) return;
    
    for (size_t i = 0; i < vertex->num_pairs; i++) {
        free((void*)vertex->pairs[i].key);
        gs_value_destroy(&vertex->pairs[i].value);
    }
    
    free(vertex->pairs);
    free(vertex);
}

GraphserverVertex* gs_vertex_clone(const GraphserverVertex* vertex) {
    if (!vertex) return NULL;
    
    // Create clone with same pairs and hash
    return gs_vertex_create(vertex->pairs, vertex->num_pairs, &vertex->hash);
}

// Binary search for key position
static size_t find_key_position(const GraphserverVertex* vertex, const char* key, bool* found) {
    *found = false;
    
    if (vertex->num_pairs == 0) return 0;
    
    size_t left = 0;
    size_t right = vertex->num_pairs;
    
    while (left < right) {
        size_t mid = left + (right - left) / 2;
        int cmp = strcmp(key, vertex->pairs[mid].key);
        
        if (cmp == 0) {
            *found = true;
            return mid;
        } else if (cmp < 0) {
            right = mid;
        } else {
            left = mid + 1;
        }
    }
    
    return left;
}


GraphserverResult gs_vertex_get_value(const GraphserverVertex* vertex, const char* key, GraphserverValue* out_value) {
    if (!vertex || !key || !out_value) return GS_ERROR_NULL_POINTER;
    
    bool found;
    size_t pos = find_key_position(vertex, key, &found);
    
    if (!found) return GS_ERROR_KEY_NOT_FOUND;
    
    *out_value = gs_value_copy(&vertex->pairs[pos].value);
    return GS_SUCCESS;
}

GraphserverResult gs_vertex_has_key(const GraphserverVertex* vertex, const char* key, bool* out_has_key) {
    if (!vertex || !key || !out_has_key) return GS_ERROR_NULL_POINTER;
    
    find_key_position(vertex, key, out_has_key);
    return GS_SUCCESS;
}


// Vertex introspection
size_t gs_vertex_get_key_count(const GraphserverVertex* vertex) {
    return vertex ? vertex->num_pairs : 0;
}

GraphserverResult gs_vertex_get_key_at_index(const GraphserverVertex* vertex, size_t index, const char** out_key) {
    if (!vertex || !out_key) return GS_ERROR_NULL_POINTER;
    if (index >= vertex->num_pairs) return GS_ERROR_INVALID_ARGUMENT;
    
    *out_key = vertex->pairs[index].key;
    return GS_SUCCESS;
}

GraphserverResult gs_vertex_get_keys(const GraphserverVertex* vertex, const char*** out_keys, size_t* out_count) {
    if (!vertex || !out_keys || !out_count) return GS_ERROR_NULL_POINTER;
    
    if (vertex->num_pairs == 0) {
        *out_keys = NULL;
        *out_count = 0;
        return GS_SUCCESS;
    }
    
    const char** keys = malloc(sizeof(const char*) * vertex->num_pairs);
    if (!keys) return GS_ERROR_OUT_OF_MEMORY;
    
    for (size_t i = 0; i < vertex->num_pairs; i++) {
        keys[i] = vertex->pairs[i].key;
    }
    
    *out_keys = keys;
    *out_count = vertex->num_pairs;
    return GS_SUCCESS;
}

// Vertex comparison and hashing
bool gs_vertex_equals(const GraphserverVertex* a, const GraphserverVertex* b) {
    if (!a || !b) return false;
    
    // Fast hash-based comparison
    if (a->hash != b->hash) return false;
    
    // If hashes match, we can be confident they're equal, but do a fallback check
    // for the rare case of hash collisions
    if (a->num_pairs != b->num_pairs) return false;
    
    // Since keys are sorted, we can compare sequentially
    for (size_t i = 0; i < a->num_pairs; i++) {
        if (strcmp(a->pairs[i].key, b->pairs[i].key) != 0) return false;
        if (!gs_value_equals(&a->pairs[i].value, &b->pairs[i].value)) return false;
    }
    
    return true;
}

uint64_t gs_vertex_hash(const GraphserverVertex* vertex) {
    if (!vertex) return 0;
    return vertex->hash;
}

// Vertex serialization (for debugging)
char* gs_vertex_to_string(const GraphserverVertex* vertex) {
    if (!vertex) return duplicate_string("null");
    
    // Estimate buffer size (this is a rough estimate)
    size_t buffer_size = 1024;
    char* buffer = malloc(buffer_size);
    if (!buffer) return NULL;
    
    size_t pos = 0;
    pos += snprintf(buffer + pos, buffer_size - pos, "{");
    
    for (size_t i = 0; i < vertex->num_pairs; i++) {
        if (i > 0) {
            pos += snprintf(buffer + pos, buffer_size - pos, ", ");
        }
        
        pos += snprintf(buffer + pos, buffer_size - pos, "\"%s\": ", vertex->pairs[i].key);
        
        const GraphserverValue* value = &vertex->pairs[i].value;
        switch (value->type) {
            case GS_VALUE_INT:
                pos += snprintf(buffer + pos, buffer_size - pos, "%ld", value->as.i_val);
                break;
            case GS_VALUE_FLOAT:
                pos += snprintf(buffer + pos, buffer_size - pos, "%f", value->as.f_val);
                break;
            case GS_VALUE_BOOL:
                pos += snprintf(buffer + pos, buffer_size - pos, "%s", value->as.b_val ? "true" : "false");
                break;
            case GS_VALUE_STRING:
                pos += snprintf(buffer + pos, buffer_size - pos, "\"%s\"", 
                              value->as.s_val ? value->as.s_val : "null");
                break;
            default:
                pos += snprintf(buffer + pos, buffer_size - pos, "[array]");
                break;
        }
        
        // Ensure we don't overflow the buffer
        if (pos >= buffer_size - 100) {
            buffer_size *= 2;
            char* new_buffer = realloc(buffer, buffer_size);
            if (!new_buffer) {
                free(buffer);
                return NULL;
            }
            buffer = new_buffer;
        }
    }
    
    pos += snprintf(buffer + pos, buffer_size - pos, "}");
    
    return buffer;
}