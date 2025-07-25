#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "../../../core/include/graphserver.h"

/**
 * @file _graphserver.c
 * @brief Python C extension for Graphserver Planning Engine
 * 
 * This module provides the C extension interface that allows Python code
 * to interact with the high-performance Graphserver core library.
 */

// Forward declarations for module functions
static PyObject* py_create_engine(PyObject* self, PyObject* args, PyObject* kwargs);
static PyObject* py_register_provider(PyObject* self, PyObject* args);
static PyObject* py_plan(PyObject* self, PyObject* args, PyObject* kwargs);
static PyObject* py_get_engine_stats(PyObject* self, PyObject* args);
static PyObject* py_precache_subgraph(PyObject* self, PyObject* args, PyObject* kwargs);

// Utility functions for data conversion (implemented in Phase 2)
static PyObject* vertex_to_python_dict(const GraphserverVertex* vertex);
static PyObject* safe_vertex_to_python_dict(const GraphserverVertex* vertex);
static PyObject* vertex_to_python_vertex_object(const GraphserverVertex* vertex);
static GraphserverVertex* python_dict_to_vertex(PyObject* dict);
static GraphserverVertex* python_vertex_object_to_vertex(PyObject* vertex_obj);
static PyObject* path_to_python_list(const GraphserverPath* path);
static int python_edges_to_c_edges(PyObject* edge_list, GraphserverEdgeList* out_edges);
static int python_vertex_edge_pairs_to_c_edges(PyObject* pair_list, GraphserverEdgeList* out_edges);

// Provider wrapper for calling Python functions from C
static int python_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data);

// Goal predicate for identity-aware vertex equality checking
static bool identity_aware_goal_predicate(
    const GraphserverVertex* vertex,
    void* user_data);

// Data structure for Python provider information
typedef struct {
    PyObject* python_function;
    char* provider_name;
} PythonProviderData;

// Data structure for goal predicate wrapper
typedef struct {
    GraphserverVertex* goal_vertex;
} GoalPredicateData;

// PyCapsule destructor for engine cleanup
static void engine_capsule_destructor(PyObject* capsule) {
    GraphserverEngine* engine = (GraphserverEngine*)PyCapsule_GetPointer(capsule, "GraphserverEngine");
    if (engine) {
        gs_engine_destroy(engine);
    }
}

// Module function implementations

static PyObject* py_create_engine(PyObject* self, PyObject* args, PyObject* kwargs) {
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

static PyObject* py_register_provider(PyObject* self, PyObject* args) {
    (void)self;  // Unused parameter
    
    PyObject* engine_capsule;
    const char* provider_name;
    PyObject* provider_function;
    
    if (!PyArg_ParseTuple(args, "O!sO", &PyCapsule_Type, &engine_capsule, 
                         &provider_name, &provider_function)) {
        return NULL;
    }
    
    if (!PyCallable_Check(provider_function)) {
        PyErr_SetString(PyExc_TypeError, "Provider must be callable");
        return NULL;
    }
    
    GraphserverEngine* engine = (GraphserverEngine*)
        PyCapsule_GetPointer(engine_capsule, "GraphserverEngine");
    if (!engine) {
        return NULL;
    }
    
    // Create provider data with proper reference counting
    PythonProviderData* provider_data = malloc(sizeof(PythonProviderData));
    if (!provider_data) {
        PyErr_NoMemory();
        return NULL;
    }
    
    provider_data->python_function = provider_function;
    Py_INCREF(provider_function);  // Keep reference alive
    provider_data->provider_name = strdup(provider_name);
    
    // Register with C engine
    int result = gs_engine_register_provider(engine, provider_name, 
                                           python_provider_wrapper, provider_data);
    if (result != 0) {
        free(provider_data->provider_name);
        free(provider_data);
        Py_DECREF(provider_function);
        PyErr_SetString(PyExc_RuntimeError, "Failed to register provider");
        return NULL;
    }
    
    Py_RETURN_NONE;
}

static PyObject* py_plan(PyObject* self, PyObject* args, PyObject* kwargs) {
    (void)self;  // Unused parameter
    
    static char* kwlist[] = {"engine", "start", "goal", "planner", NULL};
    PyObject* engine_capsule;
    PyObject* start_dict;
    PyObject* goal_dict;
    const char* planner_name = "dijkstra";
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O!O!O!|s", kwlist,
                                    &PyCapsule_Type, &engine_capsule,
                                    &PyDict_Type, &start_dict,
                                    &PyDict_Type, &goal_dict,
                                    &planner_name)) {
        return NULL;
    }
    
    GraphserverEngine* engine = (GraphserverEngine*)
        PyCapsule_GetPointer(engine_capsule, "GraphserverEngine");
    if (!engine) {
        return NULL;
    }
    
    // Convert Python dicts to C vertices
    GraphserverVertex* start_vertex = python_dict_to_vertex(start_dict);
    if (!start_vertex) {
        return NULL; // Error already set
    }
    
    GraphserverVertex* goal_vertex = python_dict_to_vertex(goal_dict);
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
    
    // Create a simplified path conversion that doesn't access vertex data
    size_t num_edges = gs_path_get_num_edges(path);
    PyObject* python_path = PyList_New(num_edges);
    if (!python_path) {
        gs_path_destroy(path);
        gs_vertex_destroy(start_vertex);
        gs_vertex_destroy(goal_vertex);
        return NULL;
    }
    
    // Create simplified edge representations without accessing vertex data
    for (size_t i = 0; i < num_edges; i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        if (!edge) {
            Py_DECREF(python_path);
            gs_path_destroy(path);
            gs_vertex_destroy(start_vertex);
            gs_vertex_destroy(goal_vertex);
            PyErr_Format(PyExc_RuntimeError, "Failed to get edge at index %zu", i);
            return NULL;
        }
        
        PyObject* edge_dict = PyDict_New();
        if (!edge_dict) {
            Py_DECREF(python_path);
            gs_path_destroy(path);
            gs_vertex_destroy(start_vertex);
            gs_vertex_destroy(goal_vertex);
            return NULL;
        }
        
        // Get cost information (this should be safe)
        const double* distance_vector = gs_edge_get_distance_vector(edge);
        size_t distance_vector_size = gs_edge_get_distance_vector_size(edge);
        
        PyObject* cost_obj;
        if (distance_vector_size == 1) {
            cost_obj = PyFloat_FromDouble(distance_vector[0]);
        } else {
            cost_obj = PyList_New(distance_vector_size);
            if (cost_obj) {
                for (size_t j = 0; j < distance_vector_size; j++) {
                    PyObject* cost_item = PyFloat_FromDouble(distance_vector[j]);
                    if (!cost_item) {
                        Py_DECREF(cost_obj);
                        cost_obj = NULL;
                        break;
                    }
                    PyList_SetItem(cost_obj, j, cost_item);
                }
            }
        }
        
        if (!cost_obj) {
            Py_DECREF(edge_dict);
            Py_DECREF(python_path);
            gs_path_destroy(path);
            gs_vertex_destroy(start_vertex);
            gs_vertex_destroy(goal_vertex);
            return NULL;
        }
        
        PyDict_SetItemString(edge_dict, "cost", cost_obj);
        Py_DECREF(cost_obj);
        
        // Get target vertex data - now safe due to vertex cloning in C library
        const GraphserverVertex* target_vertex = gs_edge_get_target_vertex(edge);
        PyObject* target_dict = vertex_to_python_dict(target_vertex);
        if (!target_dict) {
            Py_DECREF(edge_dict);
            Py_DECREF(python_path);
            gs_path_destroy(path);
            gs_vertex_destroy(start_vertex);
            gs_vertex_destroy(goal_vertex);
            return NULL;
        }
        
        PyDict_SetItemString(edge_dict, "target", target_dict);
        Py_DECREF(target_dict);
        
        PyList_SetItem(python_path, i, edge_dict);
    }
    
    // Clean up C path AFTER conversion
    gs_path_destroy(path);
    
    // Clean up input vertices
    gs_vertex_destroy(start_vertex);
    gs_vertex_destroy(goal_vertex);
    
    return python_path;
}

// Provider wrapper function that calls Python functions from C
static int python_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    if (!current_vertex || !out_edges || !user_data) {
        return -1;
    }
    
    PythonProviderData* provider_data = (PythonProviderData*)user_data;
    PyObject* python_function = provider_data->python_function;
    
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

// Identity-aware goal predicate that uses _id_hash when available
static bool identity_aware_goal_predicate(
    const GraphserverVertex* vertex,
    void* user_data) {
    
    if (!vertex || !user_data) {
        return false;
    }
    
    GoalPredicateData* goal_data = (GoalPredicateData*)user_data;
    
    // First try identity hash comparison if available on both vertices
    GraphserverValue id_hash_val;
    GraphserverValue goal_id_hash_val;
    
    bool has_id = gs_vertex_get_value(vertex, "_id_hash", &id_hash_val) == GS_SUCCESS;
    bool goal_has_id = gs_vertex_get_value(goal_data->goal_vertex, "_id_hash", &goal_id_hash_val) == GS_SUCCESS;
    
    if (has_id && goal_has_id) {
        // Compare identity hashes - this allows coordinate matching with tolerance
        return gs_value_equals(&id_hash_val, &goal_id_hash_val);
    }
    
    // Fall back to full vertex equality for vertices without identity hashes
    return gs_vertex_equals(vertex, goal_data->goal_vertex);
}

// Placeholder data conversion functions (Phase 2 implementation)
static PyObject* vertex_to_python_dict(const GraphserverVertex* vertex) {
    if (!vertex) {
        PyErr_SetString(PyExc_ValueError, "Vertex cannot be NULL");
        return NULL;
    }
    
    PyObject* dict = PyDict_New();
    if (!dict) {
        return NULL; // PyDict_New sets error on failure
    }
    
    // Get key count first
    size_t key_count = gs_vertex_get_key_count(vertex);
    if (key_count == 0) {
        return dict; // Empty vertex, return empty dict
    }
    
    // Convert each key-value pair using index-based access
    for (size_t i = 0; i < key_count; i++) {
        const char* key;
        GraphserverResult result = gs_vertex_get_key_at_index(vertex, i, &key);
        if (result != GS_SUCCESS) {
            Py_DECREF(dict);
            PyErr_Format(PyExc_RuntimeError, "Failed to get key at index %zu", i);
            return NULL;
        }
        
        GraphserverValue gs_value;
        result = gs_vertex_get_value(vertex, key, &gs_value);
        if (result != GS_SUCCESS) {
            Py_DECREF(dict);
            PyErr_Format(PyExc_RuntimeError, "Failed to get value for key '%s'", key);
            return NULL;
        }
        
        PyObject* py_value = NULL;
        
        // Convert GraphserverValue to Python object based on type
        switch (gs_value.type) {
            case GS_VALUE_INT:
                py_value = PyLong_FromLongLong(gs_value.as.i_val);
                break;
                
            case GS_VALUE_FLOAT:
                py_value = PyFloat_FromDouble(gs_value.as.f_val);
                break;
                
            case GS_VALUE_STRING:
                py_value = PyUnicode_FromString(gs_value.as.s_val);
                break;
                
            case GS_VALUE_BOOL:
                py_value = PyBool_FromLong(gs_value.as.b_val ? 1 : 0);
                break;
                
            case GS_VALUE_INT_ARRAY:
            case GS_VALUE_FLOAT_ARRAY:
            case GS_VALUE_STRING_ARRAY:
            case GS_VALUE_BOOL_ARRAY:
                // Skip array handling for now - just create a placeholder string
                py_value = PyUnicode_FromString("[array]");
                break;
            
            default:
                PyErr_Format(PyExc_RuntimeError, "Unsupported value type %d for key '%s'", 
                           gs_value.type, key);
                Py_DECREF(dict);
                return NULL;
        }
        
        if (!py_value) {
            Py_DECREF(dict);
            return NULL; // Error already set
        }
        
        // Add to dictionary
        if (PyDict_SetItemString(dict, key, py_value) < 0) {
            Py_DECREF(py_value);
            Py_DECREF(dict);
            return NULL;
        }
        
        Py_DECREF(py_value); // PyDict_SetItemString increments reference
    }
    
    return dict;
}

// Safe vertex conversion that handles potentially invalid vertex pointers
static PyObject* safe_vertex_to_python_dict(const GraphserverVertex* vertex) {
    if (!vertex) {
        // Return empty dict for null vertex
        return PyDict_New();
    }
    
    // Try to access vertex data safely
    // The risk is that the vertex memory might have been freed by the planning algorithm
    // We'll attempt to read the key count first as a basic validity check
    size_t key_count;
    
    // Attempt to get key count - this will segfault if vertex is freed
    // For now, we'll assume the vertex is valid during path conversion
    // TODO: Add more sophisticated memory validation if needed
    key_count = gs_vertex_get_key_count(vertex);
    
    // If we get here, vertex appears to be accessible
    // Use the standard conversion function
    return vertex_to_python_dict(vertex);
}

static GraphserverVertex* python_dict_to_vertex(PyObject* dict) {
    if (!PyDict_Check(dict)) {
        PyErr_SetString(PyExc_TypeError, "Expected dict object");
        return NULL;
    }
    
    GraphserverVertex* vertex = gs_vertex_create();
    if (!vertex) {
        PyErr_SetString(PyExc_MemoryError, "Failed to create vertex");
        return NULL;
    }
    
    PyObject* key;
    PyObject* value;
    Py_ssize_t pos = 0;
    
    // Iterate through all key-value pairs in the dictionary
    while (PyDict_Next(dict, &pos, &key, &value)) {
        // Key must be a string
        if (!PyUnicode_Check(key)) {
            PyErr_SetString(PyExc_TypeError, "Dictionary keys must be strings");
            gs_vertex_destroy(vertex);
            return NULL;
        }
        
        const char* key_str = PyUnicode_AsUTF8(key);
        if (!key_str) {
            gs_vertex_destroy(vertex);
            return NULL;
        }
        
        GraphserverValue gs_value;
        
        // Convert Python value to GraphserverValue based on type
        if (PyLong_Check(value)) {
            // Python int -> GraphserverValue int
            long long int_val = PyLong_AsLongLong(value);
            if (int_val == -1 && PyErr_Occurred()) {
                gs_vertex_destroy(vertex);
                return NULL;
            }
            gs_value = gs_value_create_int((int64_t)int_val);
            
        } else if (PyFloat_Check(value)) {
            // Python float -> GraphserverValue float
            double float_val = PyFloat_AsDouble(value);
            if (float_val == -1.0 && PyErr_Occurred()) {
                gs_vertex_destroy(vertex);
                return NULL;
            }
            gs_value = gs_value_create_float(float_val);
            
        } else if (PyUnicode_Check(value)) {
            // Python str -> GraphserverValue string
            const char* str_val = PyUnicode_AsUTF8(value);
            if (!str_val) {
                gs_vertex_destroy(vertex);
                return NULL;
            }
            gs_value = gs_value_create_string(str_val);
            
        } else if (PyBool_Check(value)) {
            // Python bool -> GraphserverValue bool
            bool bool_val = PyObject_IsTrue(value);
            gs_value = gs_value_create_bool(bool_val);
            
        } else if (PyList_Check(value)) {
            // For now, skip complex array handling to debug the segfault
            // Convert list to a simple string representation
            PyObject* str_repr = PyObject_Str(value);
            if (!str_repr) {
                gs_vertex_destroy(vertex);
                return NULL;
            }
            const char* str_val = PyUnicode_AsUTF8(str_repr);
            if (!str_val) {
                Py_DECREF(str_repr);
                gs_vertex_destroy(vertex);
                return NULL;
            }
            gs_value = gs_value_create_string(str_val);
            Py_DECREF(str_repr);
            
        } else {
            PyErr_Format(PyExc_TypeError, "Unsupported value type for key '%s'", key_str);
            gs_vertex_destroy(vertex);
            return NULL;
        }
        
        // Set the key-value pair in the vertex
        GraphserverResult result = gs_vertex_set_kv(vertex, key_str, gs_value);
        if (result != GS_SUCCESS) {
            PyErr_SetString(PyExc_RuntimeError, "Failed to set vertex key-value pair");
            gs_vertex_destroy(vertex);
            return NULL;
        }
    }
    
    return vertex;
}

static PyObject* path_to_python_list(const GraphserverPath* path) {
    if (!path) {
        PyErr_SetString(PyExc_ValueError, "Path cannot be NULL");
        return NULL;
    }
    
    size_t num_edges = gs_path_get_num_edges(path);
    PyObject* edge_list = PyList_New(num_edges);
    if (!edge_list) {
        return NULL; // PyList_New sets error on failure
    }
    
    // Convert each edge in the path to a Python dictionary
    for (size_t i = 0; i < num_edges; i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        if (!edge) {
            Py_DECREF(edge_list);
            PyErr_Format(PyExc_RuntimeError, "Failed to get edge at index %zu", i);
            return NULL;
        }
        
        PyObject* edge_dict = PyDict_New();
        if (!edge_dict) {
            Py_DECREF(edge_list);
            return NULL;
        }
        
        // Convert target vertex
        GraphserverVertex* target_vertex = gs_edge_get_target_vertex(edge);
        PyObject* target_dict = vertex_to_python_dict(target_vertex);
        if (!target_dict) {
            Py_DECREF(edge_dict);
            Py_DECREF(edge_list);
            return NULL;
        }
        
        if (PyDict_SetItemString(edge_dict, "target", target_dict) < 0) {
            Py_DECREF(target_dict);
            Py_DECREF(edge_dict);
            Py_DECREF(edge_list);
            return NULL;
        }
        Py_DECREF(target_dict);
        
        // Convert cost vector
        const double* distance_vector = gs_edge_get_distance_vector(edge);
        size_t distance_vector_size = gs_edge_get_distance_vector_size(edge);
        
        PyObject* cost_obj;
        if (distance_vector_size == 1) {
            // Single cost - use a float
            cost_obj = PyFloat_FromDouble(distance_vector[0]);
        } else {
            // Multi-objective cost - use a list
            cost_obj = PyList_New(distance_vector_size);
            if (cost_obj) {
                for (size_t j = 0; j < distance_vector_size; j++) {
                    PyObject* cost_item = PyFloat_FromDouble(distance_vector[j]);
                    if (!cost_item) {
                        Py_DECREF(cost_obj);
                        cost_obj = NULL;
                        break;
                    }
                    PyList_SetItem(cost_obj, j, cost_item);
                }
            }
        }
        
        if (!cost_obj) {
            Py_DECREF(edge_dict);
            Py_DECREF(edge_list);
            return NULL;
        }
        
        if (PyDict_SetItemString(edge_dict, "cost", cost_obj) < 0) {
            Py_DECREF(cost_obj);
            Py_DECREF(edge_dict);
            Py_DECREF(edge_list);
            return NULL;
        }
        Py_DECREF(cost_obj);
        
        // Convert metadata if present
        size_t metadata_count = gs_edge_get_metadata_count(edge);
        if (metadata_count > 0) {
            PyObject* metadata_dict = PyDict_New();
            if (!metadata_dict) {
                Py_DECREF(edge_dict);
                Py_DECREF(edge_list);
                return NULL;
            }
            
            // Note: The C API doesn't provide direct iteration over metadata
            // For now, we'll create an empty metadata dict
            // This can be enhanced later if the C API adds metadata iteration
            
            if (PyDict_SetItemString(edge_dict, "metadata", metadata_dict) < 0) {
                Py_DECREF(metadata_dict);
                Py_DECREF(edge_dict);
                Py_DECREF(edge_list);
                return NULL;
            }
            Py_DECREF(metadata_dict);
        }
        
        // Add edge dictionary to the list
        PyList_SetItem(edge_list, i, edge_dict);
    }
    
    return edge_list;
}

static int python_edges_to_c_edges(PyObject* edge_list, GraphserverEdgeList* out_edges) {
    if (!PyList_Check(edge_list)) {
        PyErr_SetString(PyExc_TypeError, "Expected list of edge dictionaries");
        return -1;
    }
    
    Py_ssize_t list_size = PyList_Size(edge_list);
    if (list_size == 0) {
        // Empty list is valid - nothing to add
        return 0;
    }
    
    // Process each edge in the list
    for (Py_ssize_t i = 0; i < list_size; i++) {
        PyObject* edge_dict = PyList_GetItem(edge_list, i);
        if (!PyDict_Check(edge_dict)) {
            PyErr_Format(PyExc_TypeError, "Edge at index %zd is not a dictionary", i);
            return -1;
        }
        
        // Extract required fields: target, cost
        PyObject* target_obj = PyDict_GetItemString(edge_dict, "target");
        PyObject* cost_obj = PyDict_GetItemString(edge_dict, "cost");
        
        if (!target_obj) {
            PyErr_Format(PyExc_ValueError, "Edge at index %zd missing required 'target' field", i);
            return -1;
        }
        
        if (!cost_obj) {
            PyErr_Format(PyExc_ValueError, "Edge at index %zd missing required 'cost' field", i);
            return -1;
        }
        
        // Convert target to vertex
        GraphserverVertex* original_target = python_dict_to_vertex(target_obj);
        if (!original_target) {
            return -1; // Error already set by python_dict_to_vertex
        }
        
        // Clone the vertex to ensure proper ownership semantics
        GraphserverVertex* target_vertex = gs_vertex_clone(original_target);
        gs_vertex_destroy(original_target); // Clean up the original
        if (!target_vertex) {
            PyErr_SetString(PyExc_RuntimeError, "Failed to clone target vertex");
            return -1;
        }
        
        // Convert cost - support both single cost and cost array
        double* distance_vector = NULL;
        size_t distance_vector_size = 0;
        
        if (PyFloat_Check(cost_obj) || PyLong_Check(cost_obj)) {
            // Single cost value
            double cost = PyFloat_AsDouble(cost_obj);
            if (cost == -1.0 && PyErr_Occurred()) {
                gs_vertex_destroy(target_vertex);
                return -1;
            }
            
            distance_vector = malloc(sizeof(double));
            if (!distance_vector) {
                gs_vertex_destroy(target_vertex);
                PyErr_NoMemory();
                return -1;
            }
            distance_vector[0] = cost;
            distance_vector_size = 1;
            
        } else if (PyList_Check(cost_obj)) {
            // Multi-objective cost vector
            Py_ssize_t cost_list_size = PyList_Size(cost_obj);
            if (cost_list_size <= 0) {
                gs_vertex_destroy(target_vertex);
                PyErr_Format(PyExc_ValueError, "Cost vector cannot be empty for edge at index %zd", i);
                return -1;
            }
            
            distance_vector = malloc(cost_list_size * sizeof(double));
            if (!distance_vector) {
                gs_vertex_destroy(target_vertex);
                PyErr_NoMemory();
                return -1;
            }
            
            for (Py_ssize_t j = 0; j < cost_list_size; j++) {
                PyObject* cost_item = PyList_GetItem(cost_obj, j);
                if (!PyFloat_Check(cost_item) && !PyLong_Check(cost_item)) {
                    free(distance_vector);
                    gs_vertex_destroy(target_vertex);
                    PyErr_Format(PyExc_TypeError, "Cost vector item %zd is not a number", j);
                    return -1;
                }
                distance_vector[j] = PyFloat_AsDouble(cost_item);
            }
            distance_vector_size = cost_list_size;
            
        } else {
            gs_vertex_destroy(target_vertex);
            PyErr_Format(PyExc_TypeError, "Cost must be a number or list of numbers for edge at index %zd", i);
            return -1;
        }
        
        // Create the edge
        GraphserverEdge* edge = gs_edge_create(target_vertex, distance_vector, distance_vector_size);
        free(distance_vector); // gs_edge_create copies the vector
        
        if (!edge) {
            gs_vertex_destroy(target_vertex);
            PyErr_SetString(PyExc_RuntimeError, "Failed to create edge");
            return -1;
        }
        
        // Handle optional metadata
        PyObject* metadata_obj = PyDict_GetItemString(edge_dict, "metadata");
        if (metadata_obj && PyDict_Check(metadata_obj)) {
            PyObject* meta_key;
            PyObject* meta_value;
            Py_ssize_t meta_pos = 0;
            
            while (PyDict_Next(metadata_obj, &meta_pos, &meta_key, &meta_value)) {
                if (!PyUnicode_Check(meta_key)) {
                    gs_edge_destroy(edge);
                    PyErr_SetString(PyExc_TypeError, "Metadata keys must be strings");
                    return -1;
                }
                
                const char* meta_key_str = PyUnicode_AsUTF8(meta_key);
                if (!meta_key_str) {
                    gs_edge_destroy(edge);
                    return -1;
                }
                
                // Convert metadata value to GraphserverValue
                GraphserverValue meta_gs_value;
                if (PyLong_Check(meta_value)) {
                    long long val = PyLong_AsLongLong(meta_value);
                    if (val == -1 && PyErr_Occurred()) {
                        gs_edge_destroy(edge);
                        return -1;
                    }
                    meta_gs_value = gs_value_create_int((int64_t)val);
                } else if (PyFloat_Check(meta_value)) {
                    double val = PyFloat_AsDouble(meta_value);
                    if (val == -1.0 && PyErr_Occurred()) {
                        gs_edge_destroy(edge);
                        return -1;
                    }
                    meta_gs_value = gs_value_create_float(val);
                } else if (PyUnicode_Check(meta_value)) {
                    const char* val = PyUnicode_AsUTF8(meta_value);
                    if (!val) {
                        gs_edge_destroy(edge);
                        return -1;
                    }
                    meta_gs_value = gs_value_create_string(val);
                } else if (PyBool_Check(meta_value)) {
                    bool val = PyObject_IsTrue(meta_value);
                    meta_gs_value = gs_value_create_bool(val);
                } else {
                    gs_edge_destroy(edge);
                    PyErr_Format(PyExc_TypeError, "Unsupported metadata value type for key '%s'", meta_key_str);
                    return -1;
                }
                
                GraphserverResult result = gs_edge_set_metadata(edge, meta_key_str, meta_gs_value);
                if (result != GS_SUCCESS) {
                    gs_edge_destroy(edge);
                    PyErr_Format(PyExc_RuntimeError, "Failed to set metadata for key '%s'", meta_key_str);
                    return -1;
                }
            }
        }
        
        // Add edge to the list
        GraphserverResult result = gs_edge_list_add_edge(out_edges, edge);
        if (result != GS_SUCCESS) {
            gs_edge_destroy(edge);
            PyErr_SetString(PyExc_RuntimeError, "Failed to add edge to list");
            return -1;
        }
    }
    
    return 0; // Success
}

// Helper function to convert C vertex to Python Vertex object
static PyObject* vertex_to_python_vertex_object(const GraphserverVertex* vertex) {
    if (!vertex) {
        PyErr_SetString(PyExc_ValueError, "Vertex cannot be NULL");
        return NULL;
    }
    
    // First convert to dictionary
    PyObject* dict = vertex_to_python_dict(vertex);
    if (!dict) {
        return NULL;
    }
    
    // Import Vertex class from graphserver module
    PyObject* graphserver_module = PyImport_ImportModule("graphserver");
    if (!graphserver_module) {
        Py_DECREF(dict);
        return NULL;
    }
    
    PyObject* vertex_class = PyObject_GetAttrString(graphserver_module, "Vertex");
    Py_DECREF(graphserver_module);
    if (!vertex_class) {
        Py_DECREF(dict);
        return NULL;
    }
    
    // Create Vertex object: Vertex(data)
    PyObject* vertex_obj = PyObject_CallFunctionObjArgs(vertex_class, dict, NULL);
    Py_DECREF(vertex_class);
    Py_DECREF(dict);
    
    return vertex_obj;
}

// Helper function to convert Python Vertex object to C vertex
static GraphserverVertex* python_vertex_object_to_vertex(PyObject* vertex_obj) {
    if (!vertex_obj) {
        PyErr_SetString(PyExc_ValueError, "Vertex object cannot be NULL");
        return NULL;
    }
    
    // Call to_dict() method on Vertex object
    PyObject* to_dict_method = PyObject_GetAttrString(vertex_obj, "to_dict");
    if (!to_dict_method) {
        PyErr_SetString(PyExc_TypeError, "Object is not a Vertex (missing to_dict method)");
        return NULL;
    }
    
    PyObject* dict = PyObject_CallObject(to_dict_method, NULL);
    Py_DECREF(to_dict_method);
    if (!dict) {
        return NULL;
    }
    
    // Convert dictionary to C vertex
    GraphserverVertex* vertex = python_dict_to_vertex(dict);
    Py_DECREF(dict);
    
    return vertex;
}

// Helper function to convert Python (Vertex, Edge) pairs to C edges
static int python_vertex_edge_pairs_to_c_edges(PyObject* pair_list, GraphserverEdgeList* out_edges) {
    if (!PyList_Check(pair_list)) {
        PyErr_SetString(PyExc_TypeError, "Expected list of (Vertex, Edge) tuples");
        return -1;
    }
    
    Py_ssize_t list_size = PyList_Size(pair_list);
    if (list_size == 0) {
        // Empty list is valid - nothing to add
        return 0;
    }
    
    // Process each (vertex, edge) pair in the list
    for (Py_ssize_t i = 0; i < list_size; i++) {
        PyObject* pair = PyList_GetItem(pair_list, i);
        if (!PyTuple_Check(pair) || PyTuple_Size(pair) != 2) {
            PyErr_Format(PyExc_TypeError, "Item at index %zd is not a (Vertex, Edge) tuple", i);
            return -1;
        }
        
        PyObject* vertex_obj = PyTuple_GetItem(pair, 0);
        PyObject* edge_obj = PyTuple_GetItem(pair, 1);
        
        // Convert Vertex object to C vertex
        GraphserverVertex* target_vertex = python_vertex_object_to_vertex(vertex_obj);
        if (!target_vertex) {
            return -1; // Error already set
        }
        
        // Extract cost from Edge object
        PyObject* cost_attr = PyObject_GetAttrString(edge_obj, "cost");
        if (!cost_attr) {
            gs_vertex_destroy(target_vertex);
            PyErr_Format(PyExc_TypeError, "Edge at index %zd missing cost attribute", i);
            return -1;
        }
        
        double* distance_vector = NULL;
        size_t distance_vector_size = 0;
        
        if (PyFloat_Check(cost_attr) || PyLong_Check(cost_attr)) {
            // Single cost value
            double cost = PyFloat_AsDouble(cost_attr);
            if (cost == -1.0 && PyErr_Occurred()) {
                Py_DECREF(cost_attr);
                gs_vertex_destroy(target_vertex);
                return -1;
            }
            
            distance_vector = malloc(sizeof(double));
            if (!distance_vector) {
                Py_DECREF(cost_attr);
                gs_vertex_destroy(target_vertex);
                PyErr_NoMemory();
                return -1;
            }
            distance_vector[0] = cost;
            distance_vector_size = 1;
            
        } else if (PyList_Check(cost_attr)) {
            // Multi-objective cost vector
            Py_ssize_t cost_list_size = PyList_Size(cost_attr);
            if (cost_list_size <= 0) {
                Py_DECREF(cost_attr);
                gs_vertex_destroy(target_vertex);
                PyErr_Format(PyExc_ValueError, "Cost vector cannot be empty for edge at index %zd", i);
                return -1;
            }
            
            distance_vector = malloc(cost_list_size * sizeof(double));
            if (!distance_vector) {
                Py_DECREF(cost_attr);
                gs_vertex_destroy(target_vertex);
                PyErr_NoMemory();
                return -1;
            }
            
            for (Py_ssize_t j = 0; j < cost_list_size; j++) {
                PyObject* cost_item = PyList_GetItem(cost_attr, j);
                if (!PyFloat_Check(cost_item) && !PyLong_Check(cost_item)) {
                    free(distance_vector);
                    Py_DECREF(cost_attr);
                    gs_vertex_destroy(target_vertex);
                    PyErr_Format(PyExc_TypeError, "Cost vector item %zd is not a number", j);
                    return -1;
                }
                distance_vector[j] = PyFloat_AsDouble(cost_item);
            }
            distance_vector_size = cost_list_size;
            
        } else {
            Py_DECREF(cost_attr);
            gs_vertex_destroy(target_vertex);
            PyErr_Format(PyExc_TypeError, "Cost must be a number or list of numbers for edge at index %zd", i);
            return -1;
        }
        
        Py_DECREF(cost_attr);
        
        // Create the edge
        GraphserverEdge* edge = gs_edge_create(target_vertex, distance_vector, distance_vector_size);
        free(distance_vector); // gs_edge_create copies the vector
        
        if (!edge) {
            gs_vertex_destroy(target_vertex);
            PyErr_SetString(PyExc_RuntimeError, "Failed to create edge");
            return -1;
        }
        
        // Set the edge to own the target vertex
        gs_edge_set_owns_target_vertex(edge, true);
        
        // Handle optional metadata from Edge object
        PyObject* metadata_attr = PyObject_GetAttrString(edge_obj, "metadata");
        if (metadata_attr && PyDict_Check(metadata_attr)) {
            PyObject* meta_key;
            PyObject* meta_value;
            Py_ssize_t meta_pos = 0;
            
            while (PyDict_Next(metadata_attr, &meta_pos, &meta_key, &meta_value)) {
                if (!PyUnicode_Check(meta_key)) {
                    Py_DECREF(metadata_attr);
                    gs_edge_destroy(edge);
                    PyErr_SetString(PyExc_TypeError, "Metadata keys must be strings");
                    return -1;
                }
                
                const char* meta_key_str = PyUnicode_AsUTF8(meta_key);
                if (!meta_key_str) {
                    Py_DECREF(metadata_attr);
                    gs_edge_destroy(edge);
                    return -1;
                }
                
                // Convert metadata value to GraphserverValue
                GraphserverValue meta_gs_value;
                if (PyLong_Check(meta_value)) {
                    long long val = PyLong_AsLongLong(meta_value);
                    if (val == -1 && PyErr_Occurred()) {
                        Py_DECREF(metadata_attr);
                        gs_edge_destroy(edge);
                        return -1;
                    }
                    meta_gs_value = gs_value_create_int((int64_t)val);
                } else if (PyFloat_Check(meta_value)) {
                    double val = PyFloat_AsDouble(meta_value);
                    if (val == -1.0 && PyErr_Occurred()) {
                        Py_DECREF(metadata_attr);
                        gs_edge_destroy(edge);
                        return -1;
                    }
                    meta_gs_value = gs_value_create_float(val);
                } else if (PyUnicode_Check(meta_value)) {
                    const char* val = PyUnicode_AsUTF8(meta_value);
                    if (!val) {
                        Py_DECREF(metadata_attr);
                        gs_edge_destroy(edge);
                        return -1;
                    }
                    meta_gs_value = gs_value_create_string(val);
                } else if (PyBool_Check(meta_value)) {
                    bool val = PyObject_IsTrue(meta_value);
                    meta_gs_value = gs_value_create_bool(val);
                } else {
                    Py_DECREF(metadata_attr);
                    gs_edge_destroy(edge);
                    PyErr_Format(PyExc_TypeError, "Unsupported metadata value type for key '%s'", meta_key_str);
                    return -1;
                }
                
                GraphserverResult result = gs_edge_set_metadata(edge, meta_key_str, meta_gs_value);
                if (result != GS_SUCCESS) {
                    Py_DECREF(metadata_attr);
                    gs_edge_destroy(edge);
                    PyErr_Format(PyExc_RuntimeError, "Failed to set metadata for key '%s'", meta_key_str);
                    return -1;
                }
            }
        }
        if (metadata_attr) {
            Py_DECREF(metadata_attr);
        }
        
        // Add edge to the list
        GraphserverResult result = gs_edge_list_add_edge(out_edges, edge);
        if (result != GS_SUCCESS) {
            gs_edge_destroy(edge);
            PyErr_SetString(PyExc_RuntimeError, "Failed to add edge to list");
            return -1;
        }
    }
    
    return 0; // Success
}

static PyObject* py_get_engine_stats(PyObject* self, PyObject* args) {
    (void)self;  // Unused parameter
    
    PyObject* engine_capsule;
    
    if (!PyArg_ParseTuple(args, "O!", &PyCapsule_Type, &engine_capsule)) {
        return NULL;
    }
    
    GraphserverEngine* engine = (GraphserverEngine*)
        PyCapsule_GetPointer(engine_capsule, "GraphserverEngine");
    if (!engine) {
        return NULL;
    }
    
    // Get statistics from the engine
    GraphserverPlanStats stats;
    GraphserverResult result = gs_engine_get_stats(engine, &stats);
    if (result != GS_SUCCESS) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to get engine statistics");
        return NULL;
    }
    
    // Convert to Python dictionary
    PyObject* stats_dict = PyDict_New();
    if (!stats_dict) {
        return NULL;
    }
    
    // Add all statistics fields
    PyDict_SetItemString(stats_dict, "vertices_expanded", PyLong_FromUnsignedLongLong(stats.vertices_expanded));
    PyDict_SetItemString(stats_dict, "edges_generated", PyLong_FromUnsignedLongLong(stats.edges_generated));
    PyDict_SetItemString(stats_dict, "providers_called", PyLong_FromUnsignedLongLong(stats.providers_called));
    PyDict_SetItemString(stats_dict, "peak_memory_usage", PyLong_FromSize_t(stats.peak_memory_usage));
    
    // Add cache-specific statistics
    PyDict_SetItemString(stats_dict, "cache_hits", PyLong_FromUnsignedLongLong(stats.cache_hits));
    PyDict_SetItemString(stats_dict, "cache_misses", PyLong_FromUnsignedLongLong(stats.cache_misses));
    PyDict_SetItemString(stats_dict, "cache_puts", PyLong_FromUnsignedLongLong(stats.cache_puts));
    
    return stats_dict;
}

static PyObject* py_precache_subgraph(PyObject* self, PyObject* args, PyObject* kwargs) {
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
    GraphserverEngine* engine = (GraphserverEngine*)
        PyCapsule_GetPointer(engine_capsule, "GraphserverEngine");
    if (!engine) {
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
            for (Py_ssize_t j = 0; j < i; j++) {
                if (c_vertices[j]) {
                    gs_vertex_destroy(c_vertices[j]);
                }
            }
            free(c_vertices);
            return NULL;
        }
        
        // Check if it's a dictionary (legacy format) or Vertex object
        if (PyDict_Check(vertex_obj)) {
            c_vertices[i] = python_dict_to_vertex(vertex_obj);
        } else {
            // Assume it's a Vertex object with to_dict() method
            PyObject* dict_repr = PyObject_CallMethod(vertex_obj, "to_dict", NULL);
            if (!dict_repr) {
                // Cleanup and return error
                for (Py_ssize_t j = 0; j < i; j++) {
                    if (c_vertices[j]) {
                        gs_vertex_destroy(c_vertices[j]);
                    }
                }
                free(c_vertices);
                return NULL;
            }
            
            c_vertices[i] = python_dict_to_vertex(dict_repr);
            Py_DECREF(dict_repr);
        }
        
        if (!c_vertices[i]) {
            // Cleanup and return error
            for (Py_ssize_t j = 0; j < i; j++) {
                if (c_vertices[j]) {
                    gs_vertex_destroy(c_vertices[j]);
                }
            }
            free(c_vertices);
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
    for (Py_ssize_t i = 0; i < num_seeds; i++) {
        if (c_vertices[i]) {
            gs_vertex_destroy(c_vertices[i]);
        }
    }
    free(c_vertices);
    
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

// Method definitions with modern argument parsing
static PyMethodDef GraphserverMethods[] = {
    {"create_engine", (PyCFunction)(void(*)(void))py_create_engine, METH_VARARGS | METH_KEYWORDS, 
     "Create a new planning engine with optional configuration"},
    {"register_provider", py_register_provider, METH_VARARGS, 
     "Register a Python function as an edge provider"},
    {"plan", (PyCFunction)(void(*)(void))py_plan, METH_VARARGS | METH_KEYWORDS, 
     "Execute pathfinding from start to goal"},
    {"get_engine_stats", py_get_engine_stats, METH_VARARGS, 
     "Get engine statistics including cache performance metrics"},
    {"precache_subgraph", (PyCFunction)(void(*)(void))py_precache_subgraph, METH_VARARGS | METH_KEYWORDS,
     "Pre-cache a subgraph using breadth-first discovery"},
    {NULL, NULL, 0, NULL}
};

// Module definition with modern features
static struct PyModuleDef graphserver_module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "_graphserver",
    .m_doc = "Graphserver Planning Engine C Extension",
    .m_size = -1,
    .m_methods = GraphserverMethods,
    .m_slots = NULL,
    .m_traverse = NULL,
    .m_clear = NULL,
    .m_free = NULL
};

// Module initialization with error handling
PyMODINIT_FUNC PyInit__graphserver(void) {
    PyObject* module = PyModule_Create(&graphserver_module);
    if (module == NULL) {
        return NULL;
    }
    
    // Add module-level constants
    if (PyModule_AddStringConstant(module, "__version__", "2.0.0") < 0) {
        Py_DECREF(module);
        return NULL;
    }
    
    return module;
}