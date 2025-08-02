/**
 * @file cleanup.c
 * @brief Cleanup and resource management functions for Graphserver extension
 * 
 * This module contains utility functions for proper cleanup and memory management
 * of GraphServer C structures and Python objects.
 */

#include "extension.h"

/**
 * Clean up planning resources including path, vertices, and Python objects.
 * 
 * @param python_path Python path object to decref (may be NULL)
 * @param path C GraphserverPath to destroy (may be NULL)
 * @param start_vertex C start vertex to destroy (may be NULL)
 * @param goal_vertex C goal vertex to destroy (may be NULL)
 */
void cleanup_plan_resources(PyObject* python_path, GraphserverPath* path, 
                           GraphserverVertex* start_vertex, GraphserverVertex* goal_vertex) {
    Py_XDECREF(python_path);
    if (path) gs_path_destroy(path);
    if (start_vertex) gs_vertex_destroy(start_vertex);
    if (goal_vertex) gs_vertex_destroy(goal_vertex);
}

/**
 * Clean up an array of GraphserverKeyPair structures.
 * 
 * @param pairs Array of key-value pairs to clean up (may be NULL)
 * @param count Number of pairs in the array
 */
void cleanup_vertex_pairs(GraphserverKeyPair* pairs, size_t count) {
    if (!pairs) return;
    for (size_t i = 0; i < count; i++) {
        gs_value_destroy((GraphserverValue*)&pairs[i].value);
    }
    free(pairs);
}

/**
 * Clean up an array of GraphserverVertex pointers.
 * 
 * @param vertices Array of vertex pointers to clean up (may be NULL)
 * @param count Number of vertices in the array
 */
void cleanup_vertex_array(GraphserverVertex** vertices, size_t count) {
    if (!vertices) return;
    for (size_t i = 0; i < count; i++) {
        if (vertices[i]) gs_vertex_destroy(vertices[i]);
    }
    free(vertices);
}