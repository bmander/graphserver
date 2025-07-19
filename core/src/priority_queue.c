#include "../include/gs_memory.h"
#include "../include/gs_vertex.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/**
 * @file priority_queue.c
 * @brief Binary min-heap priority queue for Dijkstra's algorithm
 * 
 * This implementation provides a binary min-heap specifically optimized for
 * pathfinding algorithms. It supports decrease_key operations for efficient
 * cost updates during planning.
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
} PriorityQueue;

// Constants
#define INITIAL_PQ_CAPACITY 64

// Helper macros for heap navigation
#define PARENT(i) (((i) - 1) / 2)
#define LEFT_CHILD(i) (2 * (i) + 1)
#define RIGHT_CHILD(i) (2 * (i) + 2)

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
    
    pq->entries = entries;
    pq->size = 0;
    pq->capacity = INITIAL_PQ_CAPACITY;
    pq->arena = arena;
    
    return pq;
}

// Swap two entries in the heap
static void pq_swap(PriorityQueue* pq, size_t i, size_t j) {
    PQEntry temp = pq->entries[i];
    pq->entries[i] = pq->entries[j];
    pq->entries[j] = temp;
    
    // Update heap indices
    pq->entries[i].heap_index = i;
    pq->entries[j].heap_index = j;
}

// Bubble up an entry to maintain heap property
static void pq_bubble_up(PriorityQueue* pq, size_t index) {
    while (index > 0) {
        size_t parent = PARENT(index);
        
        if (pq->entries[index].cost >= pq->entries[parent].cost) {
            break; // Heap property satisfied
        }
        
        pq_swap(pq, index, parent);
        index = parent;
    }
}

// Bubble down an entry to maintain heap property
static void pq_bubble_down(PriorityQueue* pq, size_t index) {
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
        
        pq_swap(pq, index, smallest);
        index = smallest;
    }
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
    
    pq->size++;
    
    // Restore heap property
    pq_bubble_up(pq, index);
    
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
    
    // Move last element to root
    pq->size--;
    if (pq->size > 0) {
        pq->entries[0] = pq->entries[pq->size];
        pq->entries[0].heap_index = 0;
        
        // Restore heap property
        pq_bubble_down(pq, 0);
    }
    
    return true;
}

// Find entry for vertex (linear search for now)
static size_t pq_find_vertex(PriorityQueue* pq, const GraphserverVertex* vertex) {
    for (size_t i = 0; i < pq->size; i++) {
        if (gs_vertex_equals(pq->entries[i].vertex, vertex)) {
            return i;
        }
    }
    return SIZE_MAX; // Not found
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
    pq_bubble_up(pq, index);
    
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
    }
}

// Destroy priority queue
void pq_destroy(PriorityQueue* pq) {
    if (!pq) return;
    
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
    return pq_find_vertex((PriorityQueue*)pq, vertex) != SIZE_MAX;
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