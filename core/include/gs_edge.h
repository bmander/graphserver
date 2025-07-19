#ifndef GS_EDGE_H
#define GS_EDGE_H

#include "gs_types.h"

#ifdef __cplusplus
extern "C" {
#endif

// Edge creation and destruction
GraphserverEdge* gs_edge_create(GraphserverVertex* target_vertex, 
                               const double* distance_vector, 
                               size_t distance_vector_size);
void gs_edge_destroy(GraphserverEdge* edge);
GraphserverEdge* gs_edge_clone(const GraphserverEdge* edge);

// Edge metadata management
GraphserverResult gs_edge_set_metadata(GraphserverEdge* edge, const char* key, GraphserverValue value);
GraphserverResult gs_edge_get_metadata(const GraphserverEdge* edge, const char* key, GraphserverValue* out_value);
GraphserverResult gs_edge_has_metadata_key(const GraphserverEdge* edge, const char* key, bool* out_has_key);
GraphserverResult gs_edge_remove_metadata_key(GraphserverEdge* edge, const char* key);

// Edge introspection
GraphserverVertex* gs_edge_get_target_vertex(const GraphserverEdge* edge);
const double* gs_edge_get_distance_vector(const GraphserverEdge* edge);
size_t gs_edge_get_distance_vector_size(const GraphserverEdge* edge);
size_t gs_edge_get_metadata_count(const GraphserverEdge* edge);

// Edge list management
GraphserverEdgeList* gs_edge_list_create(void);
void gs_edge_list_destroy(GraphserverEdgeList* edge_list);
GraphserverResult gs_edge_list_add_edge(GraphserverEdgeList* edge_list, GraphserverEdge* edge);
GraphserverResult gs_edge_list_get_edge(const GraphserverEdgeList* edge_list, size_t index, GraphserverEdge** out_edge);
size_t gs_edge_list_get_count(const GraphserverEdgeList* edge_list);
void gs_edge_list_clear(GraphserverEdgeList* edge_list);

// Edge comparison and utilities
bool gs_edge_equals(const GraphserverEdge* a, const GraphserverEdge* b);
char* gs_edge_to_string(const GraphserverEdge* edge);

#ifdef __cplusplus
}
#endif

#endif // GS_EDGE_H