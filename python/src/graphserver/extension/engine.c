/**
 * @file engine.c
 * @brief Engine management functions for Graphserver Python extension
 * 
 * This module handles engine creation, statistics retrieval, and subgraph precaching.
 */

#include "extension.h"

void engine_capsule_destructor(PyObject* capsule) {
    GraphserverEngine* engine = (GraphserverEngine*)PyCapsule_GetPointer(capsule, "GraphserverEngine");
    if (engine) {
        gs_engine_destroy(engine);
    }
}

PyObject* py_create_engine(PyObject* self, PyObject* args, PyObject* kwargs) {
    (void)self;  // Unused parameter
    
    // Parse optional keyword arguments
    static char* kwlist[] = {"enable_edge_caching", NULL};
    int enable_edge_caching = 0;  // Default to false
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|p", kwlist, &enable_edge_caching)) {
        return NULL;
    }
    
    GraphserverEngine* engine;
    
    if (enable_edge_caching) {
        // Create engine with caching enabled
        GraphserverEngineConfig config = gs_engine_get_default_config();
        config.enable_edge_caching = true;
        engine = gs_engine_create_with_config(&config);
    } else {
        // Use default config (caching disabled)
        engine = gs_engine_create();
    }
    
    if (!engine) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to create planning engine");
        return NULL;
    }
    
    // Wrap in PyCapsule for safe passing between Python and C
    return PyCapsule_New(engine, "GraphserverEngine", engine_capsule_destructor);
}

PyObject* py_get_engine_stats(PyObject* self, PyObject* args) {
    (void)self;  // Unused parameter
    
    PyObject* engine_capsule;
    
    if (!PyArg_ParseTuple(args, "O!", &PyCapsule_Type, &engine_capsule)) {
        return NULL;
    }
    
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) < 0) {
        return NULL;
    }
    
    // Get statistics from the engine
    GraphserverPlanStats stats;
    GraphserverResult result = gs_engine_get_stats(engine, &stats);
    if (result != GS_SUCCESS) {
        return handle_graphserver_error(result, "engine statistics retrieval");
    }
    
    // Create EngineStats instance
    PyObject* vertices_expanded = PyLong_FromUnsignedLongLong(stats.vertices_expanded);
    PyObject* edges_generated = PyLong_FromUnsignedLongLong(stats.edges_generated);
    PyObject* providers_called = PyLong_FromUnsignedLongLong(stats.providers_called);
    PyObject* peak_memory_usage = PyLong_FromSize_t(stats.peak_memory_usage);
    PyObject* cache_hits = PyLong_FromUnsignedLongLong(stats.cache_hits);
    PyObject* cache_misses = PyLong_FromUnsignedLongLong(stats.cache_misses);
    PyObject* cache_puts = PyLong_FromUnsignedLongLong(stats.cache_puts);
    
    if (!vertices_expanded || !edges_generated || !providers_called || !peak_memory_usage ||
        !cache_hits || !cache_misses || !cache_puts) {
        Py_XDECREF(vertices_expanded);
        Py_XDECREF(edges_generated);
        Py_XDECREF(providers_called);
        Py_XDECREF(peak_memory_usage);
        Py_XDECREF(cache_hits);
        Py_XDECREF(cache_misses);
        Py_XDECREF(cache_puts);
        return NULL;
    }
    
    // Create arguments tuple for EngineStats constructor
    PyObject* constructor_args = PyTuple_New(7);
    if (!constructor_args) {
        Py_DECREF(vertices_expanded);
        Py_DECREF(edges_generated);
        Py_DECREF(providers_called);
        Py_DECREF(peak_memory_usage);
        Py_DECREF(cache_hits);
        Py_DECREF(cache_misses);
        Py_DECREF(cache_puts);
        return NULL;
    }
    
    PyTuple_SetItem(constructor_args, 0, vertices_expanded); // steals reference
    PyTuple_SetItem(constructor_args, 1, edges_generated);
    PyTuple_SetItem(constructor_args, 2, providers_called);
    PyTuple_SetItem(constructor_args, 3, peak_memory_usage);
    PyTuple_SetItem(constructor_args, 4, cache_hits);
    PyTuple_SetItem(constructor_args, 5, cache_misses);
    PyTuple_SetItem(constructor_args, 6, cache_puts);
    
    // Get EngineStats class from graphserver.core module
    PyObject* core_module = PyImport_ImportModule("graphserver.core");
    if (!core_module) {
        Py_DECREF(constructor_args);
        return NULL;
    }
    
    PyObject* engine_stats_class = PyObject_GetAttrString(core_module, "EngineStats");
    Py_DECREF(core_module);
    if (!engine_stats_class) {
        Py_DECREF(constructor_args);
        return NULL;
    }
    
    // Create EngineStats instance
    PyObject* engine_stats = PyObject_CallObject(engine_stats_class, constructor_args);
    Py_DECREF(engine_stats_class);
    Py_DECREF(constructor_args);
    
    return engine_stats;
}

PyObject* py_precache_subgraph(PyObject* self, PyObject* args, PyObject* kwargs) {
    (void)self;  // Unused parameter
    
    PyObject* engine_capsule;
    const char* provider_name;
    PyObject* seed_vertices_list;
    unsigned long max_depth = 0;    // Default: unlimited depth
    unsigned long max_vertices = 0; // Default: unlimited vertices
    
    // Parse arguments with optional parameters
    static char* kwlist[] = {"engine", "provider_name", "seed_vertices", "max_depth", "max_vertices", NULL};
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O!sO!|kk", kwlist,
                                     &PyCapsule_Type, &engine_capsule,
                                     &provider_name,
                                     &PyList_Type, &seed_vertices_list,
                                     &max_depth,
                                     &max_vertices)) {
        return NULL;
    }
    
    // Get engine from capsule
    GraphserverEngine* engine;
    if (validate_engine_capsule(engine_capsule, &engine) < 0) {
        return NULL;
    }
    
    // Validate seed vertices list
    Py_ssize_t num_seeds = PyList_Size(seed_vertices_list);
    if (num_seeds == 0) {
        PyErr_SetString(PyExc_ValueError, "At least one seed vertex is required");
        return NULL;
    }
    
    // Convert Python vertex objects to C vertices
    GraphserverVertex** c_vertices = malloc(num_seeds * sizeof(GraphserverVertex*));
    if (!c_vertices) {
        PyErr_NoMemory();
        return NULL;
    }
    
    // Initialize to NULL for cleanup
    for (Py_ssize_t i = 0; i < num_seeds; i++) {
        c_vertices[i] = NULL;
    }
    
    // Convert each vertex
    for (Py_ssize_t i = 0; i < num_seeds; i++) {
        PyObject* vertex_obj = PyList_GetItem(seed_vertices_list, i);
        if (!vertex_obj) {
            // Cleanup and return error
            cleanup_vertex_array(c_vertices, i);
            return NULL;
        }
        
        // Convert Vertex object directly
        c_vertices[i] = python_vertex_to_vertex(vertex_obj);
        
        if (!c_vertices[i]) {
            // Cleanup and return error
            cleanup_vertex_array(c_vertices, i);
            return NULL;
        }
    }
    
    // Call the C precaching function
    GraphserverResult result = gs_engine_precache_subgraph(
        engine,
        provider_name,
        c_vertices,
        (size_t)num_seeds,
        (size_t)max_depth,
        (size_t)max_vertices
    );
    
    // Cleanup C vertices
    cleanup_vertex_array(c_vertices, num_seeds);
    
    // Handle result
    if (result != GS_SUCCESS) {
        switch (result) {
            case GS_ERROR_NULL_POINTER:
                PyErr_SetString(PyExc_ValueError, "Invalid null pointer argument");
                break;
            case GS_ERROR_KEY_NOT_FOUND:
                PyErr_Format(PyExc_ValueError, "Provider '%s' not found", provider_name);
                break;
            case GS_ERROR_INVALID_ARGUMENT:
                PyErr_SetString(PyExc_ValueError, "Edge caching is disabled or provider is disabled");
                break;
            case GS_ERROR_OUT_OF_MEMORY:
                PyErr_NoMemory();
                break;
            default:
                PyErr_Format(PyExc_RuntimeError, "Precaching failed with error code %d", result);
                break;
        }
        return NULL;
    }
    
    // Success - return None
    Py_RETURN_NONE;
}