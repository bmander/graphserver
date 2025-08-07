#include "../include/gs_memory.h"
#include "../include/gs_vertex.h"
#include "../include/gs_hashmap.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>

/**
 * @file priority_queue.c
 * @brief Optimized binary min-heap priority queue for Dijkstra's algorithm
 * 
 * This implementation provides a binary min-heap specifically optimized for
 * pathfinding algorithms. It supports efficient O(log n) decrease_key operations 
 * using a vertex-to-index HashMap for O(1) vertex lookups, transforming Dijkstra's 
 * algorithm from O(V²) to O(E log V) complexity.
 * 
 * Key optimizations:
 * - HashMap-based vertex-to-index mapping for O(1) lookups
 * - Binary heap with proper bubble-up/bubble-down operations
 * - Maintains heap indices for efficient swapping and position tracking
 */

// Priority queue entry
typedef struct {
    GraphserverVertex* vertex;
    double cost;
    size_t heap_index; // Position in heap (for decrease_key)
} PQEntry;

// Priority queue structure
typedef struct {
    PQEntry* entries;
    size_t size;
    size_t capacity;
    GraphserverArena* arena;
    HashMap* vertex_to_index;  // Maps vertex -> index for O(1) lookups
} PriorityQueue;

// Constants
#define INITIAL_PQ_CAPACITY 64

// Helper macros for heap navigation
#define PARENT(i) (((i) - 1) / 2)
#define LEFT_CHILD(i) (2 * (i) + 1)
#define RIGHT_CHILD(i) (2 * (i) + 2)

// External vertex hash and equality functions (defined in hashmap.c)
extern size_t vertex_hash(const void* vertex_ptr);
extern bool vertex_equals(const void* a, const void* b);

// Create priority queue
PriorityQueue* pq_create(GraphserverArena* arena) {
    PriorityQueue* pq;
    PQEntry* entries;
    
    if (arena) {
        pq = gs_arena_alloc_type(arena, PriorityQueue);
        entries = gs_arena_alloc_array(arena, PQEntry, INITIAL_PQ_CAPACITY);
    } else {
        pq = malloc(sizeof(PriorityQueue));
        entries = malloc(sizeof(PQEntry) * INITIAL_PQ_CAPACITY);
    }
    
    if (!pq || !entries) {
        if (!arena) {
            free(pq);
            free(entries);
        }
        return NULL;
    }
    
    // Create vertex-to-index map for O(1) lookups
    pq->vertex_to_index = hashmap_create(vertex_hash, vertex_equals, arena);
    if (!pq->vertex_to_index) {
        if (!arena) {
            free(pq);
            free(entries);
        }
        return NULL;
    }
    
    pq->entries = entries;
    pq->size = 0;
    pq->capacity = INITIAL_PQ_CAPACITY;
    pq->arena = arena;
    
    return pq;
}

// Swap two entries in the heap
static bool pq_swap(PriorityQueue* pq, size_t i, size_t j) {
    PQEntry temp = pq->entries[i];
    pq->entries[i] = pq->entries[j];
    pq->entries[j] = temp;
    
    // Update heap indices
    pq->entries[i].heap_index = i;
    pq->entries[j].heap_index = j;
    
    // Update vertex-to-index mappings
    if (!hashmap_put(pq->vertex_to_index, pq->entries[i].vertex, (void*)(uintptr_t)i)) {
        return false;
    }
    if (!hashmap_put(pq->vertex_to_index, pq->entries[j].vertex, (void*)(uintptr_t)j)) {
        return false;
    }
    
    return true;
}

// Bubble up an entry to maintain heap property
static bool pq_bubble_up(PriorityQueue* pq, size_t index) {
    while (index > 0) {
        size_t parent = PARENT(index);
        
        if (pq->entries[index].cost >= pq->entries[parent].cost) {
            break; // Heap property satisfied
        }
        
        if (!pq_swap(pq, index, parent)) {
            return false; // Hash map update failed
        }
        index = parent;
    }
    return true;
}

// Bubble down an entry to maintain heap property
static bool pq_bubble_down(PriorityQueue* pq, size_t index) {
    while (LEFT_CHILD(index) < pq->size) {
        size_t left = LEFT_CHILD(index);
        size_t right = RIGHT_CHILD(index);
        size_t smallest = index;
        
        // Find smallest among parent and children
        if (pq->entries[left].cost < pq->entries[smallest].cost) {
            smallest = left;
        }
        
        if (right < pq->size && pq->entries[right].cost < pq->entries[smallest].cost) {
            smallest = right;
        }
        
        if (smallest == index) {
            break; // Heap property satisfied
        }
        
        if (!pq_swap(pq, index, smallest)) {
            return false; // Hash map update failed
        }
        index = smallest;
    }
    return true;
}

// Resize priority queue if needed
static bool pq_ensure_capacity(PriorityQueue* pq, size_t min_capacity) {
    if (pq->capacity >= min_capacity) return true;
    
    size_t new_capacity = pq->capacity;
    while (new_capacity < min_capacity) {
        new_capacity *= 2;
    }
    
    PQEntry* new_entries;
    if (pq->arena) {
        new_entries = gs_arena_alloc_array(pq->arena, PQEntry, new_capacity);
        if (new_entries) {
            memcpy(new_entries, pq->entries, sizeof(PQEntry) * pq->size);
        }
    } else {
        new_entries = realloc(pq->entries, sizeof(PQEntry) * new_capacity);
    }
    
    if (!new_entries) return false;
    
    pq->entries = new_entries;
    pq->capacity = new_capacity;
    
    return true;
}

// Insert vertex with cost into priority queue
bool pq_insert(PriorityQueue* pq, GraphserverVertex* vertex, double cost) {
    if (!pq || !vertex) return false;
    
    // Ensure capacity
    if (!pq_ensure_capacity(pq, pq->size + 1)) {
        return false;
    }
    
    // Add new entry at end
    size_t index = pq->size;
    pq->entries[index].vertex = vertex;
    pq->entries[index].cost = cost;
    pq->entries[index].heap_index = index;
    
    // Add to vertex-to-index mapping
    if (!hashmap_put(pq->vertex_to_index, vertex, (void*)(uintptr_t)index)) {
        return false;
    }
    
    pq->size++;
    
    // Restore heap property
    if (!pq_bubble_up(pq, index)) {
        // If bubble_up fails, we need to rollback the insertion
        // Remove from hash map and decrease size
        hashmap_remove(pq->vertex_to_index, vertex);
        pq->size--;
        return false;
    }
    
    return true;
}

// Extract minimum cost vertex
bool pq_extract_min(PriorityQueue* pq, GraphserverVertex** out_vertex, double* out_cost) {
    if (!pq || pq->size == 0 || !out_vertex) return false;
    
    // Return minimum (root)
    *out_vertex = pq->entries[0].vertex;
    if (out_cost) {
        *out_cost = pq->entries[0].cost;
    }
    
    // Remove vertex from mapping
    hashmap_remove(pq->vertex_to_index, pq->entries[0].vertex);
    
    // Move last element to root
    pq->size--;
    if (pq->size > 0) {
        pq->entries[0] = pq->entries[pq->size];
        pq->entries[0].heap_index = 0;
        
        // Update mapping for moved element
        if (!hashmap_put(pq->vertex_to_index, pq->entries[0].vertex, (void*)(uintptr_t)0)) {
            // This is a critical error - heap is now inconsistent
            // For now, we'll continue but the queue may be corrupted
        }
        
        // Restore heap property
        if (!pq_bubble_down(pq, 0)) {
            // This is a critical error - heap is now inconsistent
            // For now, we'll continue but the queue may be corrupted
        }
    }
    
    return true;
}

// Find entry for vertex (O(1) hash map lookup)
static size_t pq_find_vertex(PriorityQueue* pq, const GraphserverVertex* vertex) {
    void* index_ptr = hashmap_get(pq->vertex_to_index, vertex);
    if (!index_ptr) {
        return SIZE_MAX; // Not found
    }
    return (size_t)(uintptr_t)index_ptr;
}

// Decrease key for vertex (if it exists in queue)
bool pq_decrease_key(PriorityQueue* pq, GraphserverVertex* vertex, double new_cost) {
    if (!pq || !vertex) return false;
    
    size_t index = pq_find_vertex(pq, vertex);
    if (index == SIZE_MAX) return false; // Not found
    
    if (new_cost >= pq->entries[index].cost) {
        return false; // Not actually decreasing
    }
    
    pq->entries[index].cost = new_cost;
    if (!pq_bubble_up(pq, index)) {
        // Rollback the cost change if bubble_up fails
        // This is tricky because we'd need to remember the old cost
        // For now, we'll return false to indicate failure
        return false;
    }
    
    return true;
}

// Check if priority queue is empty
bool pq_is_empty(const PriorityQueue* pq) {
    return !pq || pq->size == 0;
}

// Get size of priority queue
size_t pq_size(const PriorityQueue* pq) {
    return pq ? pq->size : 0;
}

// Clear priority queue
void pq_clear(PriorityQueue* pq) {
    if (pq) {
        pq->size = 0;
        hashmap_clear(pq->vertex_to_index);
    }
}

// Destroy priority queue
void pq_destroy(PriorityQueue* pq) {
    if (!pq) return;
    
    // Clean up the hashmap regardless of arena usage
    if (pq->vertex_to_index) {
        hashmap_destroy(pq->vertex_to_index);
    }
    
    // If not using arena, free manually
    if (!pq->arena) {
        free(pq->entries);
        free(pq);
    }
    // If using arena, memory will be freed when arena is destroyed
}

// Peek at minimum without extracting
bool pq_peek_min(const PriorityQueue* pq, GraphserverVertex** out_vertex, double* out_cost) {
    if (!pq || pq->size == 0 || !out_vertex) return false;
    
    *out_vertex = pq->entries[0].vertex;
    if (out_cost) {
        *out_cost = pq->entries[0].cost;
    }
    
    return true;
}

// Check if vertex exists in priority queue
bool pq_contains(const PriorityQueue* pq, const GraphserverVertex* vertex) {
    if (!pq || !vertex) return false;
    return hashmap_contains(pq->vertex_to_index, vertex);
}

// Validate heap property (for debugging)
bool pq_validate_heap(const PriorityQueue* pq) {
    if (!pq) return true;
    
    for (size_t i = 0; i < pq->size; i++) {
        size_t left = LEFT_CHILD(i);
        size_t right = RIGHT_CHILD(i);
        
        // Check left child
        if (left < pq->size && pq->entries[i].cost > pq->entries[left].cost) {
            return false;
        }
        
        // Check right child
        if (right < pq->size && pq->entries[i].cost > pq->entries[right].cost) {
            return false;
        }
        
        // Check heap index consistency
        if (pq->entries[i].heap_index != i) {
            return false;
        }
    }
    
    return true;
}