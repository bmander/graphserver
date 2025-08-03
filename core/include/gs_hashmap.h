#ifndef GS_HASHMAP_H
#define GS_HASHMAP_H

/**
 * @file gs_hashmap.h
 * @brief Generic hash map implementation with Robin Hood hashing
 * 
 * This provides a high-performance hash map with dynamic resizing,
 * Robin Hood hashing for cache efficiency, and arena allocation support.
 */

#include "gs_memory.h"
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Opaque hash map structure
 */
typedef struct HashMap HashMap;

/**
 * Hash function type for keys
 * @param key Pointer to the key
 * @return Hash value for the key
 */
typedef size_t (*hashmap_hash_fn)(const void* key);

/**
 * Equality function type for keys
 * @param a First key
 * @param b Second key
 * @return true if keys are equal, false otherwise
 */
typedef bool (*hashmap_eq_fn)(const void* a, const void* b);

/**
 * Create a new hash map
 * @param hash_fn Hash function for keys
 * @param eq_fn Equality function for keys
 * @param arena Optional arena allocator (NULL for malloc)
 * @return New hash map instance, or NULL on failure
 */
HashMap* hashmap_create(
    hashmap_hash_fn hash_fn,
    hashmap_eq_fn eq_fn,
    GraphserverArena* arena
);

/**
 * Get a value from the hash map
 * @param map Hash map
 * @param key Key to look up
 * @return Value associated with key, or NULL if not found
 */
void* hashmap_get(HashMap* map, const void* key);

/**
 * Put a key-value pair into the hash map
 * @param map Hash map
 * @param key Key to store
 * @param value Value to associate with key
 * @return true on success, false on failure
 */
bool hashmap_put(HashMap* map, void* key, void* value);

/**
 * Check if a key exists in the hash map
 * @param map Hash map
 * @param key Key to check
 * @return true if key exists, false otherwise
 */
bool hashmap_contains(HashMap* map, const void* key);

/**
 * Remove a key-value pair from the hash map
 * @param map Hash map
 * @param key Key to remove
 * @return true if key was found and removed, false otherwise
 */
bool hashmap_remove(HashMap* map, const void* key);

/**
 * Get the number of key-value pairs in the hash map
 * @param map Hash map
 * @return Number of pairs
 */
size_t hashmap_size(HashMap* map);

/**
 * Get the capacity of the hash map
 * @param map Hash map
 * @return Capacity (number of slots)
 */
size_t hashmap_capacity(HashMap* map);

/**
 * Get the load factor of the hash map
 * @param map Hash map
 * @return Load factor (size / capacity)
 */
double hashmap_load_factor(HashMap* map);

/**
 * Clear all entries from the hash map
 * @param map Hash map
 */
void hashmap_clear(HashMap* map);

/**
 * Destroy the hash map and free memory
 * @param map Hash map
 */
void hashmap_destroy(HashMap* map);

/**
 * Iterator for traversing hash map entries
 */
typedef struct {
    HashMap* map;
    size_t current_index;
} HashMapIterator;

/**
 * Initialize an iterator for the hash map
 * @param map Hash map
 * @return Iterator structure
 */
HashMapIterator hashmap_iterator_create(HashMap* map);

/**
 * Get the next key-value pair from the iterator
 * @param iter Iterator
 * @param out_key Pointer to store the key (can be NULL)
 * @param out_value Pointer to store the value (can be NULL)
 * @return true if a pair was found, false if iteration is complete
 */
bool hashmap_iterator_next(HashMapIterator* iter, void** out_key, void** out_value);

#ifdef __cplusplus
}
#endif

#endif // GS_HASHMAP_H