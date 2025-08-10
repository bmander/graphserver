/**
 * @file cache.c
 * @brief Python bindings for cache invalidation operations
 * 
 * This module provides Python bindings for the cache invalidation functionality,
 * allowing Python code to directly invalidate cached edge entries.
 */

#include "extension.h"

/**
 * Python binding for gs_engine_invalidate_vertex_cache
 * Args: engine_capsule, vertex_object
 */
PyObject* py_invalidate_vertex_cache(PyObject* self, PyObject* args) {
    (void)self;  // Suppress unused parameter warning
    PyObject* engine_capsule = NULL;
    PyObject* vertex_obj = NULL;
    
    if (!PyArg_ParseTuple(args, "OO", &engine_capsule, &vertex_obj)) {
        return NULL;
    }
    
    // Validate engine capsule
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) != 0) {
        return NULL;
    }
    
    // Convert Python vertex to C vertex
    GraphserverVertex* vertex = python_vertex_to_vertex(vertex_obj);
    if (!vertex) {
        return handle_graphserver_error(GS_ERROR_INVALID_ARGUMENT, "invalidate_vertex_cache");
    }
    
    // Call C function
    GraphserverResult result = gs_engine_invalidate_vertex_cache(engine, vertex);
    
    // Cleanup
    gs_vertex_destroy(vertex);
    
    // Handle result
    if (result != GS_SUCCESS) {
        return handle_graphserver_error(result, "invalidate_vertex_cache");
    }
    
    Py_RETURN_NONE;
}

/**
 * Python binding for gs_engine_invalidate_vertices_cache
 * Args: engine_capsule, vertex_list
 */
PyObject* py_invalidate_vertices_cache(PyObject* self, PyObject* args) {
    (void)self;  // Suppress unused parameter warning
    PyObject* engine_capsule = NULL;
    PyObject* vertex_list = NULL;
    
    if (!PyArg_ParseTuple(args, "OO", &engine_capsule, &vertex_list)) {
        return NULL;
    }
    
    // Validate engine capsule
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) != 0) {
        return NULL;
    }
    
    // Validate vertex list
    if (!PyList_Check(vertex_list)) {
        PyErr_SetString(PyExc_TypeError, "Second argument must be a list of vertices");
        return NULL;
    }
    
    Py_ssize_t count = PyList_Size(vertex_list);
    if (count == 0) {
        Py_RETURN_NONE; // Nothing to invalidate
    }
    
    // Convert Python vertices to C vertices
    GraphserverVertex** vertices = calloc(count, sizeof(GraphserverVertex*));
    if (!vertices) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory for vertex array");
        return NULL;
    }
    
    // Convert each vertex
    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject* vertex_obj = PyList_GetItem(vertex_list, i);
        if (!vertex_obj) {
            cleanup_vertex_array(vertices, i);
            return NULL;
        }
        
        vertices[i] = python_vertex_to_vertex(vertex_obj);
        if (!vertices[i]) {
            cleanup_vertex_array(vertices, i);
            return handle_graphserver_error(GS_ERROR_INVALID_ARGUMENT, "invalidate_vertices_cache");
        }
    }
    
    // Call C function
    GraphserverResult result = gs_engine_invalidate_vertices_cache(
        engine, (const GraphserverVertex**)vertices, count);
    
    // Cleanup
    cleanup_vertex_array(vertices, count);
    
    // Handle result
    if (result != GS_SUCCESS) {
        return handle_graphserver_error(result, "invalidate_vertices_cache");
    }
    
    Py_RETURN_NONE;
}

/**
 * Python binding for gs_engine_clear_cache
 * Args: engine_capsule
 */
PyObject* py_clear_cache(PyObject* self, PyObject* args) {
    (void)self;  // Suppress unused parameter warning
    PyObject* engine_capsule = NULL;
    
    if (!PyArg_ParseTuple(args, "O", &engine_capsule)) {
        return NULL;
    }
    
    // Validate engine capsule
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) != 0) {
        return NULL;
    }
    
    // Call C function
    GraphserverResult result = gs_engine_clear_cache(engine);
    
    // Handle result
    if (result != GS_SUCCESS) {
        return handle_graphserver_error(result, "clear_cache");
    }
    
    Py_RETURN_NONE;
}

/**
 * Register a string key and return its uint16_t ID.
 * 
 * @param self Module object (unused)
 * @param args Arguments tuple containing the string key
 * @return Python integer containing the key ID
 */
PyObject* py_register_key(PyObject* self, PyObject* args) {
    (void)self;  // Suppress unused parameter warning
    const char* key_str;
    
    if (!PyArg_ParseTuple(args, "s", &key_str)) {
        return NULL;
    }
    
    uint16_t key_id = gs_string_dict_register(key_str);
    return PyLong_FromUnsignedLong(key_id);
}

/**
 * Get the string representation of a uint16_t key ID.
 * 
 * @param self Module object (unused)
 * @param args Arguments tuple containing the key ID
 * @return Python string containing the key string, or None if invalid
 */
PyObject* py_get_key_string(PyObject* self, PyObject* args) {
    (void)self;  // Suppress unused parameter warning
    unsigned int key_id;
    
    if (!PyArg_ParseTuple(args, "I", &key_id)) {
        return NULL;
    }
    
    if (key_id > UINT16_MAX) {
        PyErr_Format(PyExc_ValueError, "Key ID %u exceeds maximum value %u", key_id, UINT16_MAX);
        return NULL;
    }
    
    const char* key_str = gs_key_to_string((uint16_t)key_id);
    if (key_str) {
        return PyUnicode_FromString(key_str);
    } else {
        Py_RETURN_NONE;
    }
}