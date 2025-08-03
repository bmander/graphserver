#include "../include/gs_hashmap.h"
#include "../include/gs_memory.h"
#include "../include/gs_vertex.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/**
 * @file hashmap.c
 * @brief Generic hash map implementation with Robin Hood hashing
 * 
 * Uses open addressing with Robin Hood hashing for excellent cache performance
 * and minimal memory overhead. Dynamically resizes to maintain good performance.
 */

// Hash map entry
typedef struct {
    void* key;
    void* value;
    size_t hash;
    uint32_t distance; // Distance from ideal position (Robin Hood)
} HashEntry;

// Hash map structure
struct HashMap {
    HashEntry* entries;
    size_t capacity;
    size_t size;
    size_t mask; // capacity - 1 (for fast modulo when capacity is power of 2)
    
    // Function pointers for key operations
    hashmap_hash_fn hash_fn;
    hashmap_eq_fn eq_fn;
    
    // Memory management
    GraphserverArena* arena;
};

// Constants
#define INITIAL_CAPACITY 32
#define MAX_LOAD_FACTOR 0.75
#define EMPTY_HASH 0

// Hash and equality functions for vertices (used in compatibility functions)
size_t vertex_hash(const void* vertex_ptr) {
    const GraphserverVertex* vertex = (const GraphserverVertex*)vertex_ptr;
    return gs_vertex_hash(vertex);
}

bool vertex_equals(const void* a, const void* b) {
    const GraphserverVertex* vertex_a = (const GraphserverVertex*)a;
    const GraphserverVertex* vertex_b = (const GraphserverVertex*)b;
    return gs_vertex_equals(vertex_a, vertex_b);
}

/**
 * Ensure capacity is a power of 2
 */
static size_t next_power_of_2(size_t n) {
    if (n == 0) return 1;
    
    size_t result = 1;
    while (result < n) {
        result <<= 1;
    }
    return result;
}


/**
 * Find the position for a key (for lookup or insertion)
 */
static size_t find_position(HashMap* map, const void* key, size_t hash) {
    size_t pos = hash & map->mask;
    
    while (map->entries[pos].key != NULL) {
        if (map->entries[pos].hash == hash && 
            map->eq_fn(map->entries[pos].key, key)) {
            return pos; // Found
        }
        pos = (pos + 1) & map->mask;
    }
    
    return pos; // Empty slot
}

/**
 * Insert an entry using Robin Hood hashing
 */
static void robin_hood_insert(HashMap* map, void* key, void* value, size_t hash) {
    size_t ideal_pos = hash & map->mask;
    size_t pos = ideal_pos;
    uint32_t distance = 0;
    
    HashEntry entry = {key, value, hash, distance};
    
    while (map->entries[pos].key != NULL) {
        uint32_t existing_distance = map->entries[pos].distance;
        
        if (distance > existing_distance) {
            // Swap with existing entry (Robin Hood principle)
            HashEntry temp = map->entries[pos];
            map->entries[pos] = entry;
            entry = temp;
            distance = existing_distance;
        }
        
        pos = (pos + 1) & map->mask;
        distance++;
    }
    
    // Insert at empty position
    map->entries[pos] = entry;
    map->entries[pos].distance = distance;
}

/**
 * Resize the hash map to double capacity
 */
static bool resize_hashmap(HashMap* map) {
    size_t old_capacity = map->capacity;
    HashEntry* old_entries = map->entries;
    
    // Double the capacity
    size_t new_capacity = old_capacity * 2;
    HashEntry* new_entries;
    
    if (map->arena) {
        new_entries = gs_arena_calloc_array(map->arena, HashEntry, new_capacity);
    } else {
        new_entries = calloc(new_capacity, sizeof(HashEntry));
    }
    
    if (!new_entries) return false;
    
    // Update map structure
    map->entries = new_entries;
    map->capacity = new_capacity;
    map->mask = new_capacity - 1;
    size_t old_size = map->size;
    map->size = 0;
    
    // Rehash all entries
    for (size_t i = 0; i < old_capacity; i++) {
        if (old_entries[i].key != NULL) {
            robin_hood_insert(map, old_entries[i].key, old_entries[i].value, old_entries[i].hash);
            map->size++;
        }
    }
    
    // Verify rehashing worked correctly
    assert(map->size == old_size);
    
    // Free old entries if not using arena
    if (!map->arena) {
        free(old_entries);
    }
    
    return true;
}

// Public API implementations

HashMap* hashmap_create(hashmap_hash_fn hash_fn, hashmap_eq_fn eq_fn, GraphserverArena* arena) {
    if (!hash_fn || !eq_fn) return NULL;
    
    size_t capacity = next_power_of_2(INITIAL_CAPACITY);
    
    HashMap* map;
    HashEntry* entries;
    
    if (arena) {
        map = gs_arena_alloc_type(arena, HashMap);
        entries = gs_arena_calloc_array(arena, HashEntry, capacity);
    } else {
        map = malloc(sizeof(HashMap));
        entries = calloc(capacity, sizeof(HashEntry));
    }
    
    if (!map || !entries) {
        if (!arena) {
            free(map);
            free(entries);
        }
        return NULL;
    }
    
    map->entries = entries;
    map->capacity = capacity;
    map->size = 0;
    map->mask = capacity - 1;
    map->hash_fn = hash_fn;
    map->eq_fn = eq_fn;
    map->arena = arena;
    
    return map;
}

void* hashmap_get(HashMap* map, const void* key) {
    if (!map || !key) return NULL;
    
    size_t hash = map->hash_fn(key);
    if (hash == EMPTY_HASH) hash = 1; // Avoid empty marker
    
    size_t pos = find_position(map, key, hash);
    return map->entries[pos].key ? map->entries[pos].value : NULL;
}

bool hashmap_put(HashMap* map, void* key, void* value) {
    if (!map || !key) return false;
    
    size_t hash = map->hash_fn(key);
    if (hash == EMPTY_HASH) hash = 1;
    
    // Check if key already exists
    size_t pos = find_position(map, key, hash);
    if (map->entries[pos].key != NULL) {
        // Update existing entry
        map->entries[pos].value = value;
        return true;
    }
    
    // Check load factor and resize if needed
    if ((double)(map->size + 1) / map->capacity > MAX_LOAD_FACTOR) {
        if (!resize_hashmap(map)) {
            return false;
        }
    }
    
    // Insert new entry
    robin_hood_insert(map, key, value, hash);
    map->size++;
    
    return true;
}

bool hashmap_contains(HashMap* map, const void* key) {
    return hashmap_get(map, key) != NULL;
}

bool hashmap_remove(HashMap* map, const void* key) {
    if (!map || !key) return false;
    
    size_t hash = map->hash_fn(key);
    if (hash == EMPTY_HASH) hash = 1;
    
    size_t pos = find_position(map, key, hash);
    if (map->entries[pos].key == NULL) {
        return false; // Key not found
    }
    
    // Mark slot as empty
    map->entries[pos].key = NULL;
    map->entries[pos].value = NULL;
    map->entries[pos].hash = EMPTY_HASH;
    map->entries[pos].distance = 0;
    map->size--;
    
    // Backward shift deletion to maintain Robin Hood invariant
    size_t next_pos = (pos + 1) & map->mask;
    while (map->entries[next_pos].key != NULL && map->entries[next_pos].distance > 0) {
        // Shift entry back
        map->entries[pos] = map->entries[next_pos];
        map->entries[pos].distance--;
        
        // Clear the old position
        map->entries[next_pos].key = NULL;
        map->entries[next_pos].value = NULL;
        map->entries[next_pos].hash = EMPTY_HASH;
        map->entries[next_pos].distance = 0;
        
        pos = next_pos;
        next_pos = (next_pos + 1) & map->mask;
    }
    
    return true;
}

size_t hashmap_size(HashMap* map) {
    return map ? map->size : 0;
}

size_t hashmap_capacity(HashMap* map) {
    return map ? map->capacity : 0;
}

double hashmap_load_factor(HashMap* map) {
    if (!map || map->capacity == 0) return 0.0;
    return (double)map->size / map->capacity;
}

void hashmap_clear(HashMap* map) {
    if (!map) return;
    
    // Clear all entries
    for (size_t i = 0; i < map->capacity; i++) {
        map->entries[i].key = NULL;
        map->entries[i].value = NULL;
        map->entries[i].hash = EMPTY_HASH;
        map->entries[i].distance = 0;
    }
    
    map->size = 0;
}

void hashmap_destroy(HashMap* map) {
    if (!map) return;
    
    // If not using arena, free the arrays and structure
    if (!map->arena) {
        free(map->entries);
        free(map);
    }
    // If using arena, memory will be freed when arena is destroyed
}

HashMapIterator hashmap_iterator_create(HashMap* map) {
    HashMapIterator iter = {map, 0};
    return iter;
}

bool hashmap_iterator_next(HashMapIterator* iter, void** out_key, void** out_value) {
    if (!iter || !iter->map) return false;
    
    while (iter->current_index < iter->map->capacity) {
        if (iter->map->entries[iter->current_index].key != NULL) {
            if (out_key) {
                *out_key = iter->map->entries[iter->current_index].key;
            }
            if (out_value) {
                *out_value = iter->map->entries[iter->current_index].value;
            }
            iter->current_index++;
            return true;
        }
        iter->current_index++;
    }
    
    return false; // End of iteration
}

// Compatibility functions for old vertex_set API
// These are thin wrappers around the hashmap API

typedef HashMap VertexSet;

VertexSet* vertex_set_create(GraphserverArena* arena) {
    return hashmap_create(vertex_hash, vertex_equals, arena);
}

bool vertex_set_add(VertexSet* set, GraphserverVertex* vertex) {
    return hashmap_put(set, vertex, vertex); // Value doesn't matter for set
}

bool vertex_set_contains(const VertexSet* set, const GraphserverVertex* vertex) {
    return hashmap_contains((HashMap*)set, vertex);
}

void vertex_set_clear(VertexSet* set) {
    hashmap_clear(set);
}

void vertex_set_destroy(VertexSet* set) {
    hashmap_destroy(set);
}

