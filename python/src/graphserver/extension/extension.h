#ifndef GRAPHSERVER_EXTENSION_H
#define GRAPHSERVER_EXTENSION_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "../../../../core/include/graphserver.h"
#include "../../../../core/include/gs_string_dict.h"
#include "../../../../core/include/gs_common_keys.h"

/**
 * @file extension.h
 * @brief Shared declarations for Graphserver Python C extension modules
 */

// Data structures for Python provider information
typedef struct {
    PyObject* out_edges_function;
    PyObject* in_edges_function;
    char* provider_name;
} PythonProviderData;

// Data structure for goal predicate wrapper
typedef struct {
    GraphserverVertex* goal_vertex;
} GoalPredicateData;

// Engine management functions (engine.c)
PyObject* py_create_engine(PyObject* self, PyObject* args, PyObject* kwargs);
PyObject* py_get_engine_stats(PyObject* self, PyObject* args);
PyObject* py_precache_subgraph(PyObject* self, PyObject* args, PyObject* kwargs);
void engine_capsule_destructor(PyObject* capsule);

// Provider functions (providers.c)
PyObject* py_register_provider(PyObject* self, PyObject* args);
PyObject* py_plan(PyObject* self, PyObject* args, PyObject* kwargs);
int python_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data);
int python_incoming_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* in_edges,
    void* user_data);
bool identity_aware_goal_predicate(
    const GraphserverVertex* vertex,
    void* user_data);

// Conversion functions (conversion.c)
PyObject* vertex_to_python_dict(const GraphserverVertex* vertex);
PyObject* safe_vertex_to_python_dict(const GraphserverVertex* vertex);
PyObject* vertex_to_python_vertex_object(const GraphserverVertex* vertex);
GraphserverVertex* python_dict_to_vertex(PyObject* dict);
GraphserverVertex* python_vertex_to_vertex(PyObject* vertex_obj);
int python_object_to_graphserver_value(PyObject* value, GraphserverValue* out_value);
GraphserverVertex* python_vertex_object_to_vertex(PyObject* vertex_obj);
PyObject* path_to_python_list(const GraphserverPath* path);
int python_edges_to_c_edges(PyObject* edge_list, GraphserverEdgeList* out_edges);
int python_vertex_edge_pairs_to_c_edges(PyObject* pair_list, GraphserverEdgeList* out_edges);
PyObject* convert_cost_vector(const double* vector, size_t size);
PyObject* convert_edge_to_dict(const GraphserverEdge* edge);
PyObject* create_python_edge_object(const GraphserverEdge* edge);
PyObject* create_python_vertex_object(const GraphserverVertex* vertex);
PyObject* convert_path_to_edge_vertex_pairs(const GraphserverPath* path, const GraphserverVertex* start_vertex);

// Validation and error handling functions (validation.c)
PyObject* handle_graphserver_error(GraphserverResult result, const char* operation);
int validate_engine_capsule(PyObject* capsule, GraphserverEngine** out_engine);
int validate_callable(PyObject* obj, const char* name);

// Cleanup functions (cleanup.c)
void cleanup_plan_resources(PyObject* python_path, GraphserverPath* path, 
                           GraphserverVertex* start_vertex, GraphserverVertex* goal_vertex);
void cleanup_vertex_pairs(GraphserverKeyPair* pairs, size_t count);
void cleanup_vertex_array(GraphserverVertex** vertices, size_t count);

// Cache functions (cache.c)
PyObject* py_invalidate_vertex_cache(PyObject* self, PyObject* args);
PyObject* py_invalidate_vertices_cache(PyObject* self, PyObject* args);
PyObject* py_clear_cache(PyObject* self, PyObject* args);

// Key registration functions (keys.c)
PyObject* py_register_key(PyObject* self, PyObject* args);
PyObject* py_get_key_string(PyObject* self, PyObject* args);

#endif // GRAPHSERVER_EXTENSION_H