#include "../include/gs_edge.h"
#include "../include/gs_vertex.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>

// GraphserverEdgeList is already defined in gs_types.h

// Helper function to duplicate distance vector
static double* duplicate_distance_vector(const double* vector, size_t size) {
    if (!vector || size == 0) return NULL;
    
    double* copy = malloc(sizeof(double) * size);
    if (!copy) return NULL;
    
    memcpy(copy, vector, sizeof(double) * size);
    return copy;
}

// Helper function to find metadata position
static size_t find_metadata_position(const GraphserverEdge* edge, const char* key, bool* found) {
    *found = false;
    
    if (!edge->metadata || edge->metadata_count == 0) return 0;
    
    size_t left = 0;
    size_t right = edge->metadata_count;
    
    while (left < right) {
        size_t mid = left + (right - left) / 2;
        int cmp = strcmp(key, edge->metadata[mid].key);
        
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

// Helper function to ensure metadata capacity
static GraphserverResult ensure_metadata_capacity(GraphserverEdge* edge, size_t min_capacity) {
    if (!edge) return GS_ERROR_NULL_POINTER;
    
    // Calculate current capacity
    size_t current_capacity = 0;
    if (edge->metadata) {
        // We'll track capacity by allocating in powers of 2
        current_capacity = 1;
        while (current_capacity < edge->metadata_count) {
            current_capacity *= 2;
        }
    }
    
    if (current_capacity >= min_capacity) return GS_SUCCESS;
    
    size_t new_capacity = current_capacity == 0 ? 4 : current_capacity * 2;
    while (new_capacity < min_capacity) {
        new_capacity *= 2;
    }
    
    GraphserverKeyPair* new_metadata = realloc(edge->metadata, 
                                              sizeof(GraphserverKeyPair) * new_capacity);
    if (!new_metadata) return GS_ERROR_OUT_OF_MEMORY;
    
    edge->metadata = new_metadata;
    return GS_SUCCESS;
}

// Edge creation and destruction
GraphserverEdge* gs_edge_create(GraphserverVertex* target_vertex, 
                               const double* distance_vector, 
                               size_t distance_vector_size) {
    if (!target_vertex) return NULL;
    
    GraphserverEdge* edge = malloc(sizeof(GraphserverEdge));
    if (!edge) return NULL;
    
    edge->target_vertex = target_vertex;
    edge->distance_vector = duplicate_distance_vector(distance_vector, distance_vector_size);
    edge->distance_vector_size = distance_vector_size;
    edge->metadata = NULL;
    edge->metadata_count = 0;
    edge->owns_target_vertex = false; // By default, edges don't own their target vertices
    
    // If distance vector duplication failed and we had a non-empty vector, cleanup and fail
    if (distance_vector_size > 0 && !edge->distance_vector) {
        free(edge);
        return NULL;
    }
    
    return edge;
}

void gs_edge_destroy(GraphserverEdge* edge) {
    if (!edge) return;
    
    // Destroy the target vertex if this edge owns it
    if (edge->owns_target_vertex && edge->target_vertex) {
        gs_vertex_destroy(edge->target_vertex);
    }
    
    free(edge->distance_vector);
    
    // Cleanup metadata
    if (edge->metadata) {
        for (size_t i = 0; i < edge->metadata_count; i++) {
            free((void*)edge->metadata[i].key);
            gs_value_destroy(&edge->metadata[i].value);
        }
        free(edge->metadata);
    }
    
    free(edge);
}

GraphserverEdge* gs_edge_clone(const GraphserverEdge* edge) {
    if (!edge) return NULL;
    
    // Clone the target vertex
    GraphserverVertex* cloned_vertex = gs_vertex_clone(edge->target_vertex);
    if (!cloned_vertex) return NULL;
    
    // Create the new edge
    GraphserverEdge* cloned_edge = gs_edge_create(cloned_vertex, 
                                                 edge->distance_vector, 
                                                 edge->distance_vector_size);
    if (!cloned_edge) {
        gs_vertex_destroy(cloned_vertex);
        return NULL;
    }
    
    // The cloned edge owns the cloned vertex
    cloned_edge->owns_target_vertex = true;
    
    // Clone metadata
    for (size_t i = 0; i < edge->metadata_count; i++) {
        GraphserverValue value_copy = gs_value_copy(&edge->metadata[i].value);
        GraphserverResult result = gs_edge_set_metadata(cloned_edge, edge->metadata[i].key, value_copy);
        
        if (result != GS_SUCCESS) {
            gs_edge_destroy(cloned_edge);
            return NULL;
        }
    }
    
    return cloned_edge;
}

// Edge metadata management
GraphserverResult gs_edge_set_metadata(GraphserverEdge* edge, const char* key, GraphserverValue value) {
    if (!edge || !key) return GS_ERROR_NULL_POINTER;
    
    bool found;
    size_t pos = find_metadata_position(edge, key, &found);
    
    if (found) {
        // Replace existing value
        gs_value_destroy(&edge->metadata[pos].value);
        edge->metadata[pos].value = value;
        return GS_SUCCESS;
    }
    
    // Insert new metadata pair
    GraphserverResult result = ensure_metadata_capacity(edge, edge->metadata_count + 1);
    if (result != GS_SUCCESS) return result;
    
    // Shift elements to make room
    for (size_t i = edge->metadata_count; i > pos; i--) {
        edge->metadata[i] = edge->metadata[i - 1];
    }
    
    // Insert new pair
    edge->metadata[pos].key = strdup(key);
    if (!edge->metadata[pos].key) return GS_ERROR_OUT_OF_MEMORY;
    
    edge->metadata[pos].value = value;
    edge->metadata_count++;
    
    return GS_SUCCESS;
}

GraphserverResult gs_edge_get_metadata(const GraphserverEdge* edge, const char* key, GraphserverValue* out_value) {
    if (!edge || !key || !out_value) return GS_ERROR_NULL_POINTER;
    
    bool found;
    size_t pos = find_metadata_position(edge, key, &found);
    
    if (!found) return GS_ERROR_KEY_NOT_FOUND;
    
    *out_value = gs_value_copy(&edge->metadata[pos].value);
    return GS_SUCCESS;
}

GraphserverResult gs_edge_has_metadata_key(const GraphserverEdge* edge, const char* key, bool* out_has_key) {
    if (!edge || !key || !out_has_key) return GS_ERROR_NULL_POINTER;
    
    find_metadata_position(edge, key, out_has_key);
    return GS_SUCCESS;
}

GraphserverResult gs_edge_remove_metadata_key(GraphserverEdge* edge, const char* key) {
    if (!edge || !key) return GS_ERROR_NULL_POINTER;
    
    bool found;
    size_t pos = find_metadata_position(edge, key, &found);
    
    if (!found) return GS_ERROR_KEY_NOT_FOUND;
    
    // Cleanup the removed pair
    free((void*)edge->metadata[pos].key);
    gs_value_destroy(&edge->metadata[pos].value);
    
    // Shift elements down
    for (size_t i = pos; i < edge->metadata_count - 1; i++) {
        edge->metadata[i] = edge->metadata[i + 1];
    }
    
    edge->metadata_count--;
    return GS_SUCCESS;
}

// Edge introspection
GraphserverVertex* gs_edge_get_target_vertex(const GraphserverEdge* edge) {
    return edge ? edge->target_vertex : NULL;
}

const double* gs_edge_get_distance_vector(const GraphserverEdge* edge) {
    return edge ? edge->distance_vector : NULL;
}

size_t gs_edge_get_distance_vector_size(const GraphserverEdge* edge) {
    return edge ? edge->distance_vector_size : 0;
}

size_t gs_edge_get_metadata_count(const GraphserverEdge* edge) {
    return edge ? edge->metadata_count : 0;
}

// Edge list management
GraphserverEdgeList* gs_edge_list_create(void) {
    GraphserverEdgeList* edge_list = malloc(sizeof(GraphserverEdgeList));
    if (!edge_list) return NULL;
    
    edge_list->edges = NULL;
    edge_list->num_edges = 0;
    edge_list->capacity = 0;
    edge_list->owns_edges = false; // By default, edge lists don't own their edges for backward compatibility
    
    return edge_list;
}

void gs_edge_list_destroy(GraphserverEdgeList* edge_list) {
    if (!edge_list) return;
    
    // Destroy individual edges if this list owns them
    if (edge_list->owns_edges && edge_list->edges) {
        for (size_t i = 0; i < edge_list->num_edges; i++) {
            if (edge_list->edges[i]) {
                gs_edge_destroy(edge_list->edges[i]);
            }
        }
    }
    
    free(edge_list->edges);
    free(edge_list);
}

static GraphserverResult ensure_edge_list_capacity(GraphserverEdgeList* edge_list, size_t min_capacity) {
    if (edge_list->capacity >= min_capacity) return GS_SUCCESS;
    
    size_t new_capacity = edge_list->capacity == 0 ? 4 : edge_list->capacity * 2;
    while (new_capacity < min_capacity) {
        new_capacity *= 2;
    }
    
    GraphserverEdge** new_edges = realloc(edge_list->edges, 
                                         sizeof(GraphserverEdge*) * new_capacity);
    if (!new_edges) return GS_ERROR_OUT_OF_MEMORY;
    
    edge_list->edges = new_edges;
    edge_list->capacity = new_capacity;
    
    return GS_SUCCESS;
}

GraphserverResult gs_edge_list_add_edge(GraphserverEdgeList* edge_list, GraphserverEdge* edge) {
    if (!edge_list || !edge) return GS_ERROR_NULL_POINTER;
    
    GraphserverResult result = ensure_edge_list_capacity(edge_list, edge_list->num_edges + 1);
    if (result != GS_SUCCESS) return result;
    
    edge_list->edges[edge_list->num_edges] = edge;
    edge_list->num_edges++;
    
    return GS_SUCCESS;
}

GraphserverResult gs_edge_list_get_edge(const GraphserverEdgeList* edge_list, size_t index, GraphserverEdge** out_edge) {
    if (!edge_list || !out_edge) return GS_ERROR_NULL_POINTER;
    if (index >= edge_list->num_edges) return GS_ERROR_INVALID_ARGUMENT;
    
    *out_edge = edge_list->edges[index];
    return GS_SUCCESS;
}

size_t gs_edge_list_get_count(const GraphserverEdgeList* edge_list) {
    return edge_list ? edge_list->num_edges : 0;
}

void gs_edge_list_clear(GraphserverEdgeList* edge_list) {
    if (!edge_list) return;
    
    // Destroy individual edges if this list owns them
    if (edge_list->owns_edges && edge_list->edges) {
        for (size_t i = 0; i < edge_list->num_edges; i++) {
            if (edge_list->edges[i]) {
                gs_edge_destroy(edge_list->edges[i]);
            }
        }
    }
    
    edge_list->num_edges = 0;
}

void gs_edge_list_set_owns_edges(GraphserverEdgeList* edge_list, bool owns_edges) {
    if (edge_list) {
        edge_list->owns_edges = owns_edges;
    }
}

bool gs_edge_list_get_owns_edges(const GraphserverEdgeList* edge_list) {
    return edge_list ? edge_list->owns_edges : false;
}

// Edge comparison and utilities
bool gs_edge_equals(const GraphserverEdge* a, const GraphserverEdge* b) {
    if (!a || !b) return false;
    
    // Compare target vertices
    if (!gs_vertex_equals(a->target_vertex, b->target_vertex)) return false;
    
    // Compare distance vectors
    if (a->distance_vector_size != b->distance_vector_size) return false;
    if (a->distance_vector_size > 0) {
        if (memcmp(a->distance_vector, b->distance_vector, 
                  sizeof(double) * a->distance_vector_size) != 0) return false;
    }
    
    // Compare metadata
    if (a->metadata_count != b->metadata_count) return false;
    for (size_t i = 0; i < a->metadata_count; i++) {
        if (strcmp(a->metadata[i].key, b->metadata[i].key) != 0) return false;
        if (!gs_value_equals(&a->metadata[i].value, &b->metadata[i].value)) return false;
    }
    
    return true;
}

char* gs_edge_to_string(const GraphserverEdge* edge) {
    if (!edge) return strdup("null");
    
    // Estimate buffer size
    size_t buffer_size = 1024;
    char* buffer = malloc(buffer_size);
    if (!buffer) return NULL;
    
    size_t pos = 0;
    pos += snprintf(buffer + pos, buffer_size - pos, "Edge{");
    
    // Add target vertex (abbreviated)
    char* target_str = gs_vertex_to_string(edge->target_vertex);
    if (target_str) {
        pos += snprintf(buffer + pos, buffer_size - pos, "target: %s", target_str);
        free(target_str);
    }
    
    // Add distance vector
    if (edge->distance_vector_size > 0) {
        pos += snprintf(buffer + pos, buffer_size - pos, ", distance: [");
        for (size_t i = 0; i < edge->distance_vector_size; i++) {
            if (i > 0) pos += snprintf(buffer + pos, buffer_size - pos, ", ");
            pos += snprintf(buffer + pos, buffer_size - pos, "%.3f", edge->distance_vector[i]);
        }
        pos += snprintf(buffer + pos, buffer_size - pos, "]");
    }
    
    // Add metadata count
    if (edge->metadata_count > 0) {
        pos += snprintf(buffer + pos, buffer_size - pos, ", metadata: %zu items", edge->metadata_count);
    }
    
    pos += snprintf(buffer + pos, buffer_size - pos, "}");
    
    return buffer;
}

// Edge vertex ownership management
void gs_edge_set_owns_target_vertex(GraphserverEdge* edge, bool owns_target_vertex) {
    if (edge) {
        edge->owns_target_vertex = owns_target_vertex;
    }
}

bool gs_edge_get_owns_target_vertex(const GraphserverEdge* edge) {
    return edge ? edge->owns_target_vertex : false;
}