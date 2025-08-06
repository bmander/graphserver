/**
 * @file providers.c
 * @brief Provider registration and planning functions for Graphserver Python extension
 * 
 * This module handles provider registration, path planning, and provider wrapper functions
 * that enable calling Python provider functions from C code.
 */

#include "extension.h"

PyObject* py_register_provider(PyObject* self, PyObject* args) {
    (void)self;  // Unused parameter
    
    PyObject* engine_capsule;
    const char* provider_name;
    PyObject* provider_object;
    
    if (!PyArg_ParseTuple(args, "O!sO", &PyCapsule_Type, &engine_capsule, 
                         &provider_name, &provider_object)) {
        return NULL;
    }
    
    // Extract out_edges and in_edges methods from provider object
    PyObject* out_edges_method = PyObject_GetAttrString(provider_object, "out_edges");
    if (!out_edges_method) {
        PyErr_SetString(PyExc_TypeError, "Provider must have out_edges method");
        return NULL;
    }
    
    if (!PyCallable_Check(out_edges_method)) {
        Py_DECREF(out_edges_method);
        PyErr_SetString(PyExc_TypeError, "Provider out_edges must be callable");
        return NULL;
    }
    
    PyObject* in_edges_method = PyObject_GetAttrString(provider_object, "in_edges");
    if (!in_edges_method) {
        Py_DECREF(out_edges_method);
        PyErr_SetString(PyExc_TypeError, "Provider must have in_edges method");
        return NULL;
    }
    
    if (!PyCallable_Check(in_edges_method)) {
        Py_DECREF(out_edges_method);
        Py_DECREF(in_edges_method);
        PyErr_SetString(PyExc_TypeError, "Provider in_edges must be callable");
        return NULL;
    }
    
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) < 0) {
        Py_DECREF(out_edges_method);
        Py_DECREF(in_edges_method);
        return NULL;
    }
    
    // Create provider data with proper reference counting
    PythonProviderData* provider_data = malloc(sizeof(PythonProviderData));
    if (!provider_data) {
        Py_DECREF(out_edges_method);
        Py_DECREF(in_edges_method);
        PyErr_NoMemory();
        return NULL;
    }
    
    provider_data->out_edges_function = out_edges_method;
    provider_data->in_edges_function = in_edges_method;
    Py_INCREF(out_edges_method);  // Keep reference alive
    Py_INCREF(in_edges_method);   // Keep reference alive
    provider_data->provider_name = strdup(provider_name);
    
    // Determine which wrapper functions to use based on available methods
    gs_generate_edges_fn outgoing_wrapper = out_edges_method ? python_provider_wrapper : NULL;
    gs_generate_incoming_edges_fn incoming_wrapper = in_edges_method ? python_incoming_provider_wrapper : NULL;
    
    // Register with C engine using bidirectional API
    int result = gs_engine_register_bidirectional_provider(
        engine, 
        provider_name, 
        outgoing_wrapper,
        incoming_wrapper,
        provider_data
    );
    
    if (result != 0) {
        free(provider_data->provider_name);
        free(provider_data);
        Py_DECREF(out_edges_method);
        Py_DECREF(in_edges_method);
        PyErr_SetString(PyExc_RuntimeError, "Failed to register provider");
        return NULL;
    }
    
    // Clean up local references (provider_data holds its own references)
    Py_DECREF(out_edges_method);
    Py_DECREF(in_edges_method);
    
    Py_RETURN_NONE;
}

PyObject* py_plan(PyObject* self, PyObject* args, PyObject* kwargs) {
    (void)self;  // Unused parameter
    
    static char* kwlist[] = {"engine", "start", "goal", "planner", NULL};
    PyObject* engine_capsule;
    PyObject* start_vertex_obj;
    PyObject* goal_vertex_obj;
    const char* planner_name = "dijkstra";
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O!OO|s", kwlist,
                                    &PyCapsule_Type, &engine_capsule,
                                    &start_vertex_obj,
                                    &goal_vertex_obj,
                                    &planner_name)) {
        return NULL;
    }
    
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) < 0) {
        return NULL;
    }
    
    // Convert Python Vertex objects to C vertices
    GraphserverVertex* start_vertex = python_vertex_to_vertex(start_vertex_obj);
    if (!start_vertex) {
        return NULL; // Error already set
    }
    
    GraphserverVertex* goal_vertex = python_vertex_to_vertex(goal_vertex_obj);
    if (!goal_vertex) {
        gs_vertex_destroy(start_vertex);
        return NULL; // Error already set
    }
    
    // Set up goal predicate data
    GoalPredicateData goal_data;
    goal_data.goal_vertex = goal_vertex;
    
    // Run planning using the identity-aware planner interface
    GraphserverPath* path = gs_plan_simple(
        engine,
        start_vertex,
        identity_aware_goal_predicate,
        &goal_data,
        NULL // No stats for now
    );
    
    if (!path) {
        // Clean up input vertices
        gs_vertex_destroy(start_vertex);
        gs_vertex_destroy(goal_vertex);
        PyErr_SetString(PyExc_RuntimeError, "Path planning failed - no path found");
        return NULL;
    }
    
    // Convert path to (Edge|None, Vertex) pairs
    PyObject* python_path = convert_path_to_edge_vertex_pairs(path, start_vertex);
    if (!python_path) {
        cleanup_plan_resources(NULL, path, start_vertex, goal_vertex);
        return NULL;
    }
    
    // Clean up C path AFTER conversion
    gs_path_destroy(path);
    
    // Clean up input vertices
    gs_vertex_destroy(start_vertex);
    gs_vertex_destroy(goal_vertex);
    
    return python_path;
}

int python_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    if (!current_vertex || !out_edges || !user_data) {
        return -1;
    }
    
    PythonProviderData* provider_data = (PythonProviderData*)user_data;
    PyObject* python_function = provider_data->out_edges_function;
    
    // Ensure we're in a thread that can call Python (GIL)
    PyGILState_STATE gstate = PyGILState_Ensure();
    
    int result = -1; // Default to error
    
    // Convert C vertex to Python Vertex object
    PyObject* vertex_obj = vertex_to_python_vertex_object(current_vertex);
    if (!vertex_obj) {
        PyErr_Print(); // Print the error for debugging
        PyGILState_Release(gstate);
        return -1;
    }
    
    // Call the Python provider function
    PyObject* py_result = PyObject_CallFunctionObjArgs(python_function, vertex_obj, NULL);
    Py_DECREF(vertex_obj);
    
    if (!py_result) {
        // Python function raised an exception
        PyErr_Print(); // Print the error for debugging
        PyGILState_Release(gstate);
        return -1;
    }
    
    // Convert Python (Vertex, Edge) pairs back to C structures
    if (python_vertex_edge_pairs_to_c_edges(py_result, out_edges) == 0) {
        result = 0; // Success
    } else {
        // Conversion failed
        PyErr_Print(); // Print the error for debugging
    }
    
    Py_DECREF(py_result);
    PyGILState_Release(gstate);
    
    return result;
}

int python_incoming_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* in_edges,
    void* user_data) {
    
    if (!current_vertex || !in_edges || !user_data) {
        return -1;
    }
    
    PythonProviderData* provider_data = (PythonProviderData*)user_data;
    PyObject* python_function = provider_data->in_edges_function;
    
    // If no incoming edge function is provided, return empty result
    if (!python_function) {
        return 0; // Success with no edges
    }
    
    // Ensure we're in a thread that can call Python (GIL)
    PyGILState_STATE gstate = PyGILState_Ensure();
    
    int result = -1; // Default to error
    
    // Convert C vertex to Python Vertex object
    PyObject* vertex_obj = vertex_to_python_vertex_object(current_vertex);
    if (!vertex_obj) {
        PyErr_Print(); // Print the error for debugging
        PyGILState_Release(gstate);
        return -1;
    }
    
    // Call the Python provider function
    PyObject* py_result = PyObject_CallFunctionObjArgs(python_function, vertex_obj, NULL);
    Py_DECREF(vertex_obj);
    
    if (!py_result) {
        // Python function raised an exception
        PyErr_Print(); // Print the error for debugging
        PyGILState_Release(gstate);
        return -1;
    }
    
    // Convert Python (Vertex, Edge) pairs back to C structures
    if (python_vertex_edge_pairs_to_c_edges(py_result, in_edges) == 0) {
        result = 0; // Success
    } else {
        // Conversion failed
        PyErr_Print(); // Print the error for debugging
    }
    
    Py_DECREF(py_result);
    PyGILState_Release(gstate);
    
    return result;
}

bool identity_aware_goal_predicate(
    const GraphserverVertex* vertex,
    void* user_data) {
    
    if (!vertex || !user_data) {
        printf("[GOAL_PREDICATE] NULL vertex or user_data\n");
        return false;
    }
    
    GoalPredicateData* goal_data = (GoalPredicateData*)user_data;
    
    // First try identity hash comparison if available on both vertices
    GraphserverValue id_hash_val;
    GraphserverValue goal_id_hash_val;
    
    bool has_id = gs_vertex_get_value(vertex, "_id_hash", &id_hash_val) == GS_SUCCESS;
    bool goal_has_id = gs_vertex_get_value(goal_data->goal_vertex, "_id_hash", &goal_id_hash_val) == GS_SUCCESS;
    
    // Debug logging
    char* vertex_str = gs_vertex_to_string(vertex);
    char* goal_vertex_str = gs_vertex_to_string(goal_data->goal_vertex);
    
    printf("[GOAL_PREDICATE] Comparing vertex: %s\n", vertex_str ? vertex_str : "<null>");
    printf("[GOAL_PREDICATE] With goal vertex: %s\n", goal_vertex_str ? goal_vertex_str : "<null>");
    printf("[GOAL_PREDICATE] Current has_id: %s, Goal has_id: %s\n", 
           has_id ? "true" : "false", goal_has_id ? "true" : "false");
    
    if (has_id && goal_has_id) {
        // Extract hash values for logging
        uint64_t current_hash = 0, goal_hash = 0;
        if (id_hash_val.type == GS_VALUE_INT) {
            current_hash = (uint64_t)id_hash_val.as.i_val;
        }
        if (goal_id_hash_val.type == GS_VALUE_INT) {
            goal_hash = (uint64_t)goal_id_hash_val.as.i_val;
        }
        
        printf("[GOAL_PREDICATE] Current hash: %llu, Goal hash: %llu\n", 
               (unsigned long long)current_hash, (unsigned long long)goal_hash);
        
        bool hash_match = gs_value_equals(&id_hash_val, &goal_id_hash_val);
        printf("[GOAL_PREDICATE] Hash match: %s\n", hash_match ? "true" : "false");
        
        // Clean up strings
        if (vertex_str) free(vertex_str);
        if (goal_vertex_str) free(goal_vertex_str);
        
        return hash_match;
    }
    
    // Fall back to full vertex equality for vertices without identity hashes
    bool vertex_match = gs_vertex_equals(vertex, goal_data->goal_vertex);
    printf("[GOAL_PREDICATE] Vertex equality match: %s\n", vertex_match ? "true" : "false");
    
    // Clean up strings
    if (vertex_str) free(vertex_str);
    if (goal_vertex_str) free(goal_vertex_str);
    
    return vertex_match;
}