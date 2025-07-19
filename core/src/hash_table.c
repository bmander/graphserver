#include "../include/gs_vertex.h"
#include "../include/gs_memory.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/**
 * @file hash_table.c
 * @brief Hash table implementation for vertex storage
 * 
 * This is an internal implementation used by planners for closed set tracking.
 * Uses open addressing with linear probing and Robin Hood hashing for
 * cache-efficient performance.
 */

// Hash table entry
typedef struct {
    GraphserverVertex* vertex;
    uint64_t hash;
    uint32_t distance; // Distance from ideal position (Robin Hood)
} HashEntry;

// Hash table structure
typedef struct {
    HashEntry* entries;
    size_t capacity;
    size_t size;
    size_t mask; // capacity - 1 (for fast modulo when capacity is power of 2)
    GraphserverArena* arena; // Optional arena for vertex storage
} HashTable;

// Constants
#define INITIAL_CAPACITY 32
#define MAX_LOAD_FACTOR 0.7
#define EMPTY_HASH 0

// Create hash table
static HashTable* hash_table_create_with_arena(size_t initial_capacity, GraphserverArena* arena) {
    if (initial_capacity == 0) {
        initial_capacity = INITIAL_CAPACITY;
    }
    
    // Ensure capacity is power of 2
    size_t capacity = 1;
    while (capacity < initial_capacity) {
        capacity <<= 1;
    }
    
    HashTable* table;
    HashEntry* entries;
    
    if (arena) {
        table = gs_arena_alloc_type(arena, HashTable);
        entries = gs_arena_calloc_array(arena, HashEntry, capacity);
    } else {
        table = malloc(sizeof(HashTable));
        entries = calloc(capacity, sizeof(HashEntry));
    }
    
    if (!table || !entries) {
        if (!arena) {
            free(table);
            free(entries);
        }
        return NULL;
    }
    
    table->entries = entries;
    table->capacity = capacity;
    table->size = 0;
    table->mask = capacity - 1;
    table->arena = arena;
    
    return table;
}

// Create hash table without arena
HashTable* hash_table_create(size_t initial_capacity) {
    return hash_table_create_with_arena(initial_capacity, NULL);
}

// Create hash table with arena
HashTable* hash_table_create_arena(size_t initial_capacity, GraphserverArena* arena) {
    return hash_table_create_with_arena(initial_capacity, arena);
}

// Calculate distance from ideal position (currently unused but may be needed for advanced Robin Hood hashing)
__attribute__((unused))
static uint32_t calculate_distance(const HashTable* table, size_t ideal_pos, size_t actual_pos) {
    if (actual_pos >= ideal_pos) {
        return (uint32_t)(actual_pos - ideal_pos);
    } else {
        // Wrapped around
        return (uint32_t)(table->capacity - ideal_pos + actual_pos);
    }
}

// Find position for insertion or lookup
static size_t find_position(const HashTable* table, const GraphserverVertex* vertex, uint64_t hash) {
    size_t pos = hash & table->mask;
    
    while (table->entries[pos].vertex != NULL) {
        if (table->entries[pos].hash == hash && 
            gs_vertex_equals(table->entries[pos].vertex, vertex)) {
            return pos; // Found
        }
        pos = (pos + 1) & table->mask;
    }
    
    return pos; // Empty slot
}

// Robin Hood insertion helper
static void robin_hood_insert(HashTable* table, GraphserverVertex* vertex, uint64_t hash) {
    size_t ideal_pos = hash & table->mask;
    size_t pos = ideal_pos;
    uint32_t distance = 0;
    
    HashEntry entry = {vertex, hash, distance};
    
    while (table->entries[pos].vertex != NULL) {
        uint32_t existing_distance = table->entries[pos].distance;
        
        if (distance > existing_distance) {
            // Swap with existing entry (Robin Hood)
            HashEntry temp = table->entries[pos];
            table->entries[pos] = entry;
            entry = temp;
            distance = existing_distance;
        }
        
        pos = (pos + 1) & table->mask;
        distance++;
    }
    
    // Insert at empty position
    table->entries[pos] = entry;
    table->entries[pos].distance = distance;
}

// Resize hash table
static bool hash_table_resize(HashTable* table) {
    size_t old_capacity = table->capacity;
    HashEntry* old_entries = table->entries;
    
    // Double the capacity
    size_t new_capacity = old_capacity * 2;
    HashEntry* new_entries;
    
    if (table->arena) {
        new_entries = gs_arena_calloc_array(table->arena, HashEntry, new_capacity);
    } else {
        new_entries = calloc(new_capacity, sizeof(HashEntry));
    }
    
    if (!new_entries) return false;
    
    // Update table
    table->entries = new_entries;
    table->capacity = new_capacity;
    table->mask = new_capacity - 1;
    size_t old_size = table->size;
    table->size = 0;
    
    // Rehash all entries
    for (size_t i = 0; i < old_capacity; i++) {
        if (old_entries[i].vertex != NULL) {
            robin_hood_insert(table, old_entries[i].vertex, old_entries[i].hash);
            table->size++;
        }
    }
    
    // Free old entries if not using arena
    if (!table->arena) {
        free(old_entries);
    }
    
    assert(table->size == old_size);
    return true;
}

// Insert vertex into hash table
bool hash_table_insert(HashTable* table, GraphserverVertex* vertex) {
    if (!table || !vertex) return false;
    
    uint64_t hash = gs_vertex_hash(vertex);
    if (hash == EMPTY_HASH) hash = 1; // Avoid empty marker
    
    // Check if already exists
    size_t pos = find_position(table, vertex, hash);
    if (table->entries[pos].vertex != NULL) {
        return true; // Already exists
    }
    
    // Check load factor and resize if needed
    if ((double)(table->size + 1) / table->capacity > MAX_LOAD_FACTOR) {
        if (!hash_table_resize(table)) {
            return false;
        }
    }
    
    // Insert using Robin Hood hashing
    robin_hood_insert(table, vertex, hash);
    table->size++;
    
    return true;
}

// Check if vertex exists in hash table
bool hash_table_contains(const HashTable* table, const GraphserverVertex* vertex) {
    if (!table || !vertex) return false;
    
    uint64_t hash = gs_vertex_hash(vertex);
    if (hash == EMPTY_HASH) hash = 1;
    
    size_t pos = find_position(table, vertex, hash);
    return table->entries[pos].vertex != NULL;
}

// Get hash table size
size_t hash_table_size(const HashTable* table) {
    return table ? table->size : 0;
}

// Get hash table capacity
size_t hash_table_capacity(const HashTable* table) {
    return table ? table->capacity : 0;
}

// Get load factor
double hash_table_load_factor(const HashTable* table) {
    if (!table || table->capacity == 0) return 0.0;
    return (double)table->size / table->capacity;
}

// Clear hash table
void hash_table_clear(HashTable* table) {
    if (!table) return;
    
    if (table->arena) {
        // If using arena, just zero the entries
        memset(table->entries, 0, sizeof(HashEntry) * table->capacity);
    } else {
        // Zero out entries
        for (size_t i = 0; i < table->capacity; i++) {
            table->entries[i].vertex = NULL;
            table->entries[i].hash = EMPTY_HASH;
            table->entries[i].distance = 0;
        }
    }
    
    table->size = 0;
}

// Destroy hash table
void hash_table_destroy(HashTable* table) {
    if (!table) return;
    
    // If not using arena, free the entries array
    if (!table->arena) {
        free(table->entries);
        free(table);
    }
    // If using arena, memory will be freed when arena is destroyed
}

// Iterator structure for traversing the hash table
typedef struct {
    const HashTable* table;
    size_t current_index;
} HashTableIterator;

// Initialize iterator
HashTableIterator hash_table_iterator_create(const HashTable* table) {
    HashTableIterator iter = {table, 0};
    return iter;
}

// Get next vertex from iterator
GraphserverVertex* hash_table_iterator_next(HashTableIterator* iter) {
    if (!iter || !iter->table) return NULL;
    
    while (iter->current_index < iter->table->capacity) {
        if (iter->table->entries[iter->current_index].vertex != NULL) {
            GraphserverVertex* vertex = iter->table->entries[iter->current_index].vertex;
            iter->current_index++;
            return vertex;
        }
        iter->current_index++;
    }
    
    return NULL; // End of iteration
}

// Hash table statistics for debugging/profiling
typedef struct {
    size_t size;
    size_t capacity;
    double load_factor;
    uint32_t max_distance;
    double avg_distance;
    size_t collisions;
} HashTableStats;

// Get detailed statistics
HashTableStats hash_table_get_stats(const HashTable* table) {
    HashTableStats stats = {0};
    
    if (!table) return stats;
    
    stats.size = table->size;
    stats.capacity = table->capacity;
    stats.load_factor = hash_table_load_factor(table);
    
    uint32_t total_distance = 0;
    size_t filled_slots = 0;
    
    for (size_t i = 0; i < table->capacity; i++) {
        if (table->entries[i].vertex != NULL) {
            filled_slots++;
            uint32_t distance = table->entries[i].distance;
            total_distance += distance;
            
            if (distance > stats.max_distance) {
                stats.max_distance = distance;
            }
            
            if (distance > 0) {
                stats.collisions++;
            }
        }
    }
    
    if (filled_slots > 0) {
        stats.avg_distance = (double)total_distance / filled_slots;
    }
    
    return stats;
}

// Internal API for planners
// These functions are not exposed in public headers but used by planning algorithms

// Hash table type definition for internal use
typedef struct HashTable VertexSet;

// Create vertex set for closed set tracking
VertexSet* vertex_set_create(GraphserverArena* arena) {
    return (VertexSet*)hash_table_create_arena(INITIAL_CAPACITY, arena);
}

// Add vertex to closed set
bool vertex_set_add(VertexSet* set, GraphserverVertex* vertex) {
    return hash_table_insert((HashTable*)set, vertex);
}

// Check if vertex is in closed set
bool vertex_set_contains(const VertexSet* set, const GraphserverVertex* vertex) {
    return hash_table_contains((const HashTable*)set, vertex);
}

// Clear closed set
void vertex_set_clear(VertexSet* set) {
    hash_table_clear((HashTable*)set);
}

// Destroy closed set
void vertex_set_destroy(VertexSet* set) {
    hash_table_destroy((HashTable*)set);
}