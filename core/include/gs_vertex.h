#ifndef GS_VERTEX_H
#define GS_VERTEX_H

#include "gs_types.h"

#ifdef __cplusplus
extern "C" {
#endif

// Value creation functions
GraphserverValue gs_value_create_int(int64_t val);
GraphserverValue gs_value_create_float(double val);
GraphserverValue gs_value_create_string(const char* val);
GraphserverValue gs_value_create_bool(bool val);
GraphserverValue gs_value_create_int_array(const int64_t* data, size_t size);
GraphserverValue gs_value_create_float_array(const double* data, size_t size);
GraphserverValue gs_value_create_string_array(const char* const* data, size_t size);
GraphserverValue gs_value_create_bool_array(const bool* data, size_t size);

// Value destruction
void gs_value_destroy(GraphserverValue* value);

// Value comparison
bool gs_value_equals(const GraphserverValue* a, const GraphserverValue* b);

// Value copying
GraphserverValue gs_value_copy(const GraphserverValue* value);

// Vertex lifecycle
GraphserverVertex* gs_vertex_create(const GraphserverKeyPair* pairs, size_t num_pairs, const uint64_t* optional_hash);
void gs_vertex_destroy(GraphserverVertex* vertex);
GraphserverVertex* gs_vertex_clone(const GraphserverVertex* vertex);

// Vertex access (immutable - no mutation functions)
GraphserverResult gs_vertex_get_value(const GraphserverVertex* vertex, const char* key, GraphserverValue* out_value);
GraphserverResult gs_vertex_has_key(const GraphserverVertex* vertex, const char* key, bool* out_has_key);

// Vertex introspection
size_t gs_vertex_get_key_count(const GraphserverVertex* vertex);
GraphserverResult gs_vertex_get_key_at_index(const GraphserverVertex* vertex, size_t index, const char** out_key);
GraphserverResult gs_vertex_get_keys(const GraphserverVertex* vertex, const char*** out_keys, size_t* out_count);

// Vertex comparison and hashing
bool gs_vertex_equals(const GraphserverVertex* a, const GraphserverVertex* b);
uint64_t gs_vertex_hash(const GraphserverVertex* vertex);

// Vertex serialization (for debugging)
char* gs_vertex_to_string(const GraphserverVertex* vertex);

#ifdef __cplusplus
}
#endif

#endif // GS_VERTEX_H