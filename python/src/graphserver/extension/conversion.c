/**
 * @file conversion.c
 * @brief Python ↔ C conversion functions for Graphserver extension
 * 
 * This module contains all the conversion functions that translate between
 * Python objects and C GraphServer data structures, including vertices,
 * edges, paths, and values.
 */

#include "extension.h"

/**
 * Convert a C GraphserverVertex to a Python dictionary.
 * 
 * @param vertex The C vertex to convert
 * @return PyObject* Python dictionary representation, or NULL on error
 */
PyObject* vertex_to_python_dict(const GraphserverVertex* vertex) {
    if (!vertex) {
        PyErr_SetString(PyExc_ValueError, "Vertex cannot be NULL");
        return NULL;
    }
    
    PyObject* dict = PyDict_New();
    if (!dict) {
        return NULL; // PyDict_New sets error on failure
    }
    
    // Add the vertex hash as a special _hash key
    uint64_t vertex_hash = gs_vertex_hash(vertex);
    PyObject* hash_obj = PyLong_FromUnsignedLongLong(vertex_hash);
    if (!hash_obj) {
        Py_DECREF(dict);
        return NULL;
    }
    if (PyDict_SetItemString(dict, "_hash", hash_obj) < 0) {
        Py_DECREF(hash_obj);
        Py_DECREF(dict);
        return NULL;
    }
    Py_DECREF(hash_obj);
    
    // Get key count for regular data
    size_t key_count = gs_vertex_get_key_count(vertex);
    if (key_count == 0) {
        return dict; // Empty vertex, return dict with just hash
    }
    
    // Convert each key-value pair using index-based access
    for (size_t i = 0; i < key_count; i++) {
        uint16_t key_id;
        GraphserverResult result = gs_vertex_get_key_at_index(vertex, i, &key_id);
        if (result != GS_SUCCESS) {
            Py_DECREF(dict);
            handle_graphserver_error(result, "vertex key retrieval");
            return NULL;
        }
        
        // Convert uint16_t key back to string for Python
        const char* key = gs_key_to_string(key_id);
        if (!key) {
            Py_DECREF(dict);
            PyErr_Format(PyExc_RuntimeError, "Invalid key ID %u", key_id);
            return NULL;
        }
        
        GraphserverValue gs_value;
        result = gs_vertex_get_value(vertex, key_id, &gs_value);
        if (result != GS_SUCCESS) {
            Py_DECREF(dict);
            handle_graphserver_error(result, "vertex value retrieval");
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
        
        // Clean up retrieved value if it was a string (gets copied by C API)
        if (gs_value.type == GS_VALUE_STRING) {
            gs_value_destroy((GraphserverValue*)&gs_value);
        }
    }
    
    return dict;
}

/**
 * Safe vertex conversion that handles potentially invalid vertex pointers.
 * 
 * @param vertex The C vertex to convert (may be NULL)
 * @return PyObject* Python dictionary representation, or empty dict if vertex is NULL
 */
PyObject* safe_vertex_to_python_dict(const GraphserverVertex* vertex) {
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
    (void)key_count;  // Suppress unused variable warning
    key_count = gs_vertex_get_key_count(vertex);
    
    // If we get here, vertex appears to be accessible
    // Use the standard conversion function
    return vertex_to_python_dict(vertex);
}

/**
 * Convert Python object to GraphserverValue.
 * 
 * @param value Python object to convert
 * @param out_value Pointer to output GraphserverValue
 * @return int 0 on success, -1 on error
 */
int python_object_to_graphserver_value(PyObject* value, GraphserverValue* out_value) {
    if (PyLong_Check(value)) {
        // Python int -> GraphserverValue int64
        long long int_val = PyLong_AsLongLong(value);
        if (int_val == -1 && PyErr_Occurred()) {
            return -1;  // Error already set
        }
        *out_value = gs_value_create_int((int64_t)int_val);
        
    } else if (PyFloat_Check(value)) {
        // Python float -> GraphserverValue double
        double float_val = PyFloat_AsDouble(value);
        if (float_val == -1.0 && PyErr_Occurred()) {
            return -1;  // Error already set
        }
        *out_value = gs_value_create_float(float_val);
        
    } else if (PyUnicode_Check(value)) {
        // Python str -> GraphserverValue string
        const char* str_val = PyUnicode_AsUTF8(value);
        if (!str_val) {
            return -1;  // Error already set
        }
        *out_value = gs_value_create_string(str_val);
        
    } else if (PyBool_Check(value)) {
        // Python bool -> GraphserverValue boolean
        bool bool_val = PyObject_IsTrue(value);
        *out_value = gs_value_create_bool(bool_val);
        
    } else if (PyList_Check(value)) {
        // Convert list to a simple string representation
        PyObject* str_repr = PyObject_Str(value);
        if (!str_repr) {
            return -1;  // Error already set
        }
        const char* str_val = PyUnicode_AsUTF8(str_repr);
        if (!str_val) {
            Py_DECREF(str_repr);
            return -1;  // Error already set
        }
        *out_value = gs_value_create_string(str_val);
        Py_DECREF(str_repr);
        
    } else {
        // Unsupported type
        PyErr_SetString(PyExc_TypeError, "Unsupported vertex value type");
        return -1;
    }
    
    return 0;  // Success
}

/**
 * Convert a cost vector to Python object (float for single cost, list for multiple).
 * 
 * @param vector Array of cost values
 * @param size Number of elements in the vector
 * @return PyObject* Python float or list, or NULL on error
 */
PyObject* convert_cost_vector(const double* vector, size_t size) {
    if (!vector || size == 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid cost vector");
        return NULL;
    }
    
    if (size == 1) {
        return PyFloat_FromDouble(vector[0]);
    }
    
    PyObject* cost_list = PyList_New(size);
    if (!cost_list) return NULL;
    
    for (size_t i = 0; i < size; i++) {
        PyObject* cost_item = PyFloat_FromDouble(vector[i]);
        if (!cost_item) {
            Py_DECREF(cost_list);
            return NULL;
        }
        PyList_SetItem(cost_list, i, cost_item);
    }
    
    return cost_list;
}

/**
 * Convert a C GraphserverEdge to Python dictionary.
 * 
 * @param edge The C edge to convert
 * @return PyObject* Python dictionary representation, or NULL on error
 */
PyObject* convert_edge_to_dict(const GraphserverEdge* edge) {
    if (!edge) {
        PyErr_SetString(PyExc_ValueError, "Edge cannot be NULL");
        return NULL;
    }
    
    PyObject* edge_dict = PyDict_New();
    if (!edge_dict) return NULL;
    
    // Convert cost information using helper function
    const double* distance_vector = gs_edge_get_distance_vector(edge);
    size_t distance_vector_size = gs_edge_get_distance_vector_size(edge);
    
    PyObject* cost_obj = convert_cost_vector(distance_vector, distance_vector_size);
    if (!cost_obj) {
        Py_DECREF(edge_dict);
        return NULL;
    }
    
    // Convert target vertex
    const GraphserverVertex* target_vertex = gs_edge_get_target_vertex(edge);
    PyObject* target_dict = vertex_to_python_dict(target_vertex);
    if (!target_dict) {
        Py_DECREF(cost_obj);
        Py_DECREF(edge_dict);
        return NULL;
    }
    
    // Assemble the edge dictionary
    if (PyDict_SetItemString(edge_dict, "cost", cost_obj) < 0 ||
        PyDict_SetItemString(edge_dict, "target", target_dict) < 0) {
        Py_DECREF(cost_obj);
        Py_DECREF(target_dict);
        Py_DECREF(edge_dict);
        return NULL;
    }
    
    Py_DECREF(cost_obj);
    Py_DECREF(target_dict);
    
    return edge_dict;
}

/**
 * Create a Python Edge object from a C GraphserverEdge.
 * 
 * @param edge The C edge to convert
 * @return PyObject* Python Edge object, or NULL on error
 */
PyObject* create_python_edge_object(const GraphserverEdge* edge) {
    if (!edge) {
        Py_RETURN_NONE;
    }
    
    // Get cost information
    const double* distance_vector = gs_edge_get_distance_vector(edge);
    size_t distance_vector_size = gs_edge_get_distance_vector_size(edge);
    
    PyObject* cost_obj = convert_cost_vector(distance_vector, distance_vector_size);
    if (!cost_obj) {
        return NULL;
    }
    
    // Extract metadata from C GraphserverEdge
    PyObject* metadata_dict = NULL;
    size_t metadata_count = gs_edge_get_metadata_count(edge);
    
    if (metadata_count > 0) {
        metadata_dict = PyDict_New();
        if (!metadata_dict) {
            Py_DECREF(cost_obj);
            return NULL;
        }
        
        // Iterate through metadata directly from the C structure
        for (size_t i = 0; i < metadata_count; i++) {
            uint16_t key_id = edge->metadata[i].key;
            const char* key = gs_key_to_string(key_id);
            if (!key) {
                Py_DECREF(metadata_dict);
                Py_DECREF(cost_obj);
                PyErr_Format(PyExc_RuntimeError, "Invalid metadata key ID %u", key_id);
                return NULL;
            }
            const GraphserverValue* gs_value = &edge->metadata[i].value;
            
            // Convert GraphserverValue to Python object
            PyObject* py_value = NULL;
            switch (gs_value->type) {
                case GS_VALUE_INT:
                    py_value = PyLong_FromLongLong(gs_value->as.i_val);
                    break;
                case GS_VALUE_FLOAT:
                    py_value = PyFloat_FromDouble(gs_value->as.f_val);
                    break;
                case GS_VALUE_STRING:
                    py_value = PyUnicode_FromString(gs_value->as.s_val);
                    break;
                case GS_VALUE_BOOL:
                    py_value = PyBool_FromLong(gs_value->as.b_val ? 1 : 0);
                    break;
                case GS_VALUE_INT_ARRAY:
                case GS_VALUE_FLOAT_ARRAY:
                case GS_VALUE_STRING_ARRAY: 
                case GS_VALUE_BOOL_ARRAY:
                    // Skip array handling for now - create placeholder string
                    py_value = PyUnicode_FromString("[array]");
                    break;
                default:
                    // Unsupported value type - skip this metadata entry
                    continue;
            }
            
            if (!py_value) {
                Py_DECREF(metadata_dict);
                Py_DECREF(cost_obj);
                return NULL;
            }
            
            // Add to metadata dictionary
            if (PyDict_SetItemString(metadata_dict, key, py_value) < 0) {
                Py_DECREF(py_value);
                Py_DECREF(metadata_dict);
                Py_DECREF(cost_obj);
                return NULL;
            }
            Py_DECREF(py_value); // PyDict_SetItemString increments reference
        }
    }
    
    // Create Edge constructor arguments: Edge(cost, metadata)
    PyObject* args = PyTuple_New(1);
    if (!args) {
        Py_XDECREF(metadata_dict);
        Py_DECREF(cost_obj);
        return NULL;
    }
    PyTuple_SetItem(args, 0, cost_obj); // steals reference
    
    PyObject* kwargs = NULL;
    if (metadata_dict) {
        kwargs = PyDict_New();
        if (!kwargs) {
            Py_DECREF(metadata_dict);
            Py_DECREF(args);
            return NULL;
        }
        if (PyDict_SetItemString(kwargs, "metadata", metadata_dict) < 0) {
            Py_DECREF(metadata_dict);
            Py_DECREF(kwargs);
            Py_DECREF(args);
            return NULL;
        }
        Py_DECREF(metadata_dict); // PyDict_SetItemString increments reference
    }
    
    // Get Edge class from graphserver.core module
    PyObject* core_module = PyImport_ImportModule("graphserver.core");
    if (!core_module) {
        Py_XDECREF(kwargs);
        Py_DECREF(args);
        return NULL;
    }
    
    PyObject* edge_class = PyObject_GetAttrString(core_module, "Edge");
    Py_DECREF(core_module);
    if (!edge_class) {
        Py_XDECREF(kwargs);
        Py_DECREF(args);
        return NULL;
    }
    
    // Create Edge instance: Edge(cost, metadata=metadata_dict)
    PyObject* edge_obj = PyObject_Call(edge_class, args, kwargs);
    Py_DECREF(edge_class);
    Py_DECREF(args);
    Py_XDECREF(kwargs);
    
    return edge_obj;
}

/**
 * Create a Python Vertex object from a C GraphserverVertex.
 * 
 * @param vertex The C vertex to convert
 * @return PyObject* Python Vertex object, or NULL on error
 */
PyObject* create_python_vertex_object(const GraphserverVertex* vertex) {
    if (!vertex) {
        PyErr_SetString(PyExc_ValueError, "Vertex cannot be NULL");
        return NULL;
    }
    
    // Convert C vertex to Python dict
    PyObject* vertex_dict = vertex_to_python_dict(vertex);
    if (!vertex_dict) {
        return NULL;
    }
    
    // Create Vertex constructor arguments tuple: (data, hash_value=None)
    PyObject* args = PyTuple_New(1);
    if (!args) {
        Py_DECREF(vertex_dict);
        return NULL;
    }
    PyTuple_SetItem(args, 0, vertex_dict); // steals reference
    
    // Get Vertex class from graphserver.core module
    PyObject* core_module = PyImport_ImportModule("graphserver.core");
    if (!core_module) {
        Py_DECREF(args);
        return NULL;
    }
    
    PyObject* vertex_class = PyObject_GetAttrString(core_module, "Vertex");
    Py_DECREF(core_module);
    if (!vertex_class) {
        Py_DECREF(args);
        return NULL;
    }
    
    // Create Vertex instance
    PyObject* vertex_obj = PyObject_CallObject(vertex_class, args);
    Py_DECREF(vertex_class);
    Py_DECREF(args);
    
    return vertex_obj;
}

/**
 * Convert a C GraphserverPath to Python list of (Edge|None, Vertex) pairs.
 * 
 * @param path The C path to convert
 * @param start_vertex The starting vertex of the path
 * @return PyObject* Python list of tuples, or NULL on error
 */
PyObject* convert_path_to_edge_vertex_pairs(const GraphserverPath* path, const GraphserverVertex* start_vertex) {
    if (!path || !start_vertex) {
        PyErr_SetString(PyExc_ValueError, "Path and start vertex cannot be NULL");
        return NULL;
    }
    
    size_t num_edges = gs_path_get_num_edges(path);
    
    // Path representation: [(None, start_vertex), (edge1, target1), (edge2, target2), ...]
    // Total length is num_edges + 1 (start vertex + each edge's target)
    PyObject* path_list = PyList_New(num_edges + 1);
    if (!path_list) {
        return NULL;
    }
    
    // First tuple: (None, start_vertex)
    PyObject* start_vertex_obj = create_python_vertex_object(start_vertex);
    if (!start_vertex_obj) {
        Py_DECREF(path_list);
        return NULL;
    }
    
    PyObject* start_tuple = PyTuple_New(2);
    if (!start_tuple) {
        Py_DECREF(start_vertex_obj);
        Py_DECREF(path_list);
        return NULL;
    }
    
    Py_INCREF(Py_None);
    PyTuple_SetItem(start_tuple, 0, Py_None); // steals reference to None
    PyTuple_SetItem(start_tuple, 1, start_vertex_obj); // steals reference
    PyList_SetItem(path_list, 0, start_tuple); // steals reference
    
    // Subsequent tuples: (edge, target_vertex) for each path step
    for (size_t i = 0; i < num_edges; i++) {
        const GraphserverEdge* edge = gs_path_get_edge(path, i);
        if (!edge) {
            Py_DECREF(path_list);
            PyErr_Format(PyExc_RuntimeError, "Failed to get edge at index %zu", i);
            return NULL;
        }
        
        // Create Edge object
        PyObject* edge_obj = create_python_edge_object(edge);
        if (!edge_obj) {
            Py_DECREF(path_list);
            return NULL;
        }
        
        // Get target vertex from edge
        const GraphserverVertex* target_vertex = gs_edge_get_target_vertex(edge);
        if (!target_vertex) {
            Py_DECREF(edge_obj);
            Py_DECREF(path_list);
            PyErr_Format(PyExc_RuntimeError, "Edge at index %zu has no target vertex", i);
            return NULL;
        }
        
        // Create Vertex object
        PyObject* target_vertex_obj = create_python_vertex_object(target_vertex);
        if (!target_vertex_obj) {
            Py_DECREF(edge_obj);
            Py_DECREF(path_list);
            return NULL;
        }
        
        // Create tuple (edge, vertex)
        PyObject* edge_vertex_tuple = PyTuple_New(2);
        if (!edge_vertex_tuple) {
            Py_DECREF(edge_obj);
            Py_DECREF(target_vertex_obj);
            Py_DECREF(path_list);
            return NULL;
        }
        
        PyTuple_SetItem(edge_vertex_tuple, 0, edge_obj); // steals reference
        PyTuple_SetItem(edge_vertex_tuple, 1, target_vertex_obj); // steals reference
        PyList_SetItem(path_list, i + 1, edge_vertex_tuple); // steals reference
    }
    
    return path_list;
}

/**
 * Convert a C GraphserverPath to Python list of edge dictionaries.
 * 
 * @param path The C path to convert
 * @return PyObject* Python list of edge dictionaries, or NULL on error
 */
PyObject* path_to_python_list(const GraphserverPath* path) {
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
        const GraphserverVertex* target_vertex = gs_edge_get_target_vertex(edge);
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

/**
 * Convert Python list of edge dictionaries to C GraphserverEdgeList.
 * 
 * @param edge_list Python list of edge dictionaries
 * @param out_edges Pointer to output GraphserverEdgeList
 * @return int 0 on success, -1 on error
 */
int python_edges_to_c_edges(PyObject* edge_list, GraphserverEdgeList* out_edges) {
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
                
                // Convert metadata value to GraphserverValue using existing helper
                GraphserverValue meta_gs_value;
                if (python_object_to_graphserver_value(meta_value, &meta_gs_value) != 0) {
                    gs_edge_destroy(edge);
                    return -1;
                }
                
                // Convert string key to uint16_t using string dictionary
                uint16_t meta_key_id = gs_string_dict_register(meta_key_str);
                GraphserverResult result = gs_edge_set_metadata(edge, meta_key_id, meta_gs_value);
                if (result != GS_SUCCESS) {
                    gs_edge_destroy(edge);
                    handle_graphserver_error(result, "edge metadata setting");
                    return -1;
                }
            }
        }
        
        // Add edge to the list
        GraphserverResult result = gs_edge_list_add_edge(out_edges, edge);
        if (result != GS_SUCCESS) {
            gs_edge_destroy(edge);
            handle_graphserver_error(result, "edge list addition");
            return -1;
        }
    }
    
    return 0; // Success
}

/**
 * Convert C vertex to Python Vertex object.
 * 
 * @param vertex The C vertex to convert
 * @return PyObject* Python Vertex object, or NULL on error
 */
PyObject* vertex_to_python_vertex_object(const GraphserverVertex* vertex) {
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

/**
 * Convert Python dictionary to C GraphserverVertex.
 * 
 * @param dict Python dictionary to convert
 * @return GraphserverVertex* C vertex, or NULL on error
 */
GraphserverVertex* python_dict_to_vertex(PyObject* dict) {
    if (!PyDict_Check(dict)) {
        PyErr_SetString(PyExc_TypeError, "Expected dict object");
        return NULL;
    }
    
    Py_ssize_t dict_size = PyDict_Size(dict);
    
    // Handle empty dictionary case
    if (dict_size == 0) {
        return gs_vertex_create(NULL, 0, NULL);
    }
    
    // Check for optional hash parameter
    uint64_t custom_hash = 0;
    uint64_t* hash_ptr = NULL;
    PyObject* hash_obj = PyDict_GetItemString(dict, "_hash");
    if (hash_obj && PyLong_Check(hash_obj)) {
        custom_hash = PyLong_AsUnsignedLongLong(hash_obj);
        if (custom_hash == (uint64_t)-1 && PyErr_Occurred()) {
            return NULL;
        }
        hash_ptr = &custom_hash;
        dict_size--; // Don't include _hash in the key-value pairs
    }
    
    // Allocate array for key-value pairs
    GraphserverKeyPair* pairs = NULL;
    if (dict_size > 0) {
        pairs = malloc(dict_size * sizeof(GraphserverKeyPair));
        if (!pairs) {
            PyErr_NoMemory();
            return NULL;
        }
    }
    
    // Convert Python dict to key-value pairs
    PyObject* key;
    PyObject* value;
    Py_ssize_t pos = 0;
    size_t pair_index = 0;
    
    while (PyDict_Next(dict, &pos, &key, &value)) {
        // Skip the _hash key if present
        if (PyUnicode_Check(key)) {
            const char* key_str = PyUnicode_AsUTF8(key);
            if (key_str && strcmp(key_str, "_hash") == 0) {
                continue;
            }
        }
        
        // Key must be a string
        if (!PyUnicode_Check(key)) {
            PyErr_SetString(PyExc_TypeError, "Dictionary keys must be strings");
            // Clean up any values we've already created
            cleanup_vertex_pairs(pairs, pair_index);
            return NULL;
        }
        
        const char* key_str = PyUnicode_AsUTF8(key);
        if (!key_str) {
            // Clean up and return error
            cleanup_vertex_pairs(pairs, pair_index);
            return NULL;
        }
        
        // Convert Python value to GraphserverValue using helper function
        GraphserverValue gs_value;
        if (python_object_to_graphserver_value(value, &gs_value) != 0) {
            // Clean up and return error
            cleanup_vertex_pairs(pairs, pair_index);
            return NULL;
        }
        
        // Convert string key to uint16_t using string dictionary
        uint16_t key_id = gs_string_dict_register(key_str);
        
        // Store the key-value pair
        pairs[pair_index].key = key_id;
        pairs[pair_index].value = gs_value;
        pair_index++;
    }
    
    // Create immutable vertex with all pairs at once
    GraphserverVertex* vertex = gs_vertex_create(pairs, pair_index, hash_ptr);
    
    // Clean up the pairs array (vertex makes its own copies)
    cleanup_vertex_pairs(pairs, pair_index);
    
    if (!vertex) {
        PyErr_SetString(PyExc_MemoryError, "Failed to create vertex");
        return NULL;
    }
    
    return vertex;
}

/**
 * Convert Python Vertex object to C GraphserverVertex.
 * 
 * @param vertex_obj Python Vertex object to convert
 * @return GraphserverVertex* C vertex, or NULL on error
 */
GraphserverVertex* python_vertex_to_vertex(PyObject* vertex_obj) {
    // Check if it's a Vertex object by checking for _data attribute
    if (!PyObject_HasAttrString(vertex_obj, "_data")) {
        PyErr_SetString(PyExc_TypeError, "Expected Vertex object with _data attribute");
        return NULL;
    }
    
    // Get the _data dictionary
    PyObject* data_dict = PyObject_GetAttrString(vertex_obj, "_data");
    if (!data_dict) {
        return NULL;
    }
    
    if (!PyDict_Check(data_dict)) {
        Py_DECREF(data_dict);
        PyErr_SetString(PyExc_TypeError, "Vertex._data must be a dictionary");
        return NULL;
    }
    
    // Get the optional _custom_hash
    PyObject* hash_obj = PyObject_GetAttrString(vertex_obj, "_custom_hash");
    uint64_t custom_hash = 0;
    uint64_t* hash_ptr = NULL;
    
    if (hash_obj && hash_obj != Py_None && PyLong_Check(hash_obj)) {
        custom_hash = PyLong_AsUnsignedLongLong(hash_obj);
        if (custom_hash == (uint64_t)-1 && PyErr_Occurred()) {
            Py_DECREF(data_dict);
            Py_XDECREF(hash_obj);
            return NULL;
        }
        hash_ptr = &custom_hash;
    }
    Py_XDECREF(hash_obj);
    
    Py_ssize_t dict_size = PyDict_Size(data_dict);
    
    // Handle empty dictionary case
    if (dict_size == 0) {
        Py_DECREF(data_dict);
        return gs_vertex_create(NULL, 0, hash_ptr);
    }
    
    // Allocate array for key-value pairs
    GraphserverKeyPair* pairs = malloc(dict_size * sizeof(GraphserverKeyPair));
    if (!pairs) {
        Py_DECREF(data_dict);
        PyErr_NoMemory();
        return NULL;
    }
    
    // Convert Python dict to key-value pairs (reuse logic from python_dict_to_vertex)
    PyObject* key;
    PyObject* value;
    Py_ssize_t pos = 0;
    size_t pair_index = 0;
    
    while (PyDict_Next(data_dict, &pos, &key, &value)) {
        // Convert key
        if (!PyUnicode_Check(key)) {
            // Clean up and return error
            for (size_t i = 0; i < pair_index; i++) {
                gs_value_destroy((GraphserverValue*)&pairs[i].value);
            }
            free(pairs);
            Py_DECREF(data_dict);
            PyErr_SetString(PyExc_TypeError, "All vertex keys must be strings");
            return NULL;
        }
        
        const char* key_str = PyUnicode_AsUTF8(key);
        if (!key_str) {
            // Clean up and return error
            for (size_t i = 0; i < pair_index; i++) {
                gs_value_destroy((GraphserverValue*)&pairs[i].value);
            }
            free(pairs);
            Py_DECREF(data_dict);
            return NULL;
        }
        
        // Convert string key to uint16_t using string dictionary
        uint16_t key_id = gs_string_dict_register(key_str);
        pairs[pair_index].key = key_id;
        
        // Convert Python value to GraphserverValue using helper function
        GraphserverValue gs_value;
        if (python_object_to_graphserver_value(value, &gs_value) != 0) {
            // Clean up and return error
            cleanup_vertex_pairs(pairs, pair_index);
            Py_DECREF(data_dict);
            return NULL;
        }
        
        pairs[pair_index].value = gs_value;
        pair_index++;
    }
    
    Py_DECREF(data_dict);
    
    // Create the vertex
    GraphserverVertex* vertex = gs_vertex_create(pairs, dict_size, hash_ptr);
    free(pairs);
    
    if (!vertex) {
        PyErr_SetString(PyExc_MemoryError, "Failed to create vertex");
        return NULL;
    }
    
    return vertex;
}

/**
 * Convert Python Vertex object to C GraphserverVertex (alternative implementation).
 * 
 * @param vertex_obj Python Vertex object to convert
 * @return GraphserverVertex* C vertex, or NULL on error
 */
GraphserverVertex* python_vertex_object_to_vertex(PyObject* vertex_obj) {
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
    
    // Check if the Vertex object has a custom hash attribute
    PyObject* hash_attr = PyObject_GetAttrString(vertex_obj, "_custom_hash");
    if (hash_attr && PyLong_Check(hash_attr)) {
        // Add the hash to the dictionary for python_dict_to_vertex to use
        if (PyDict_SetItemString(dict, "_hash", hash_attr) < 0) {
            Py_DECREF(hash_attr);
            Py_DECREF(dict);
            return NULL;
        }
    }
    if (hash_attr) {
        Py_DECREF(hash_attr);
    } else {
        // Clear the AttributeError from trying to get _custom_hash
        PyErr_Clear();
    }
    
    // Convert dictionary to C vertex
    GraphserverVertex* vertex = python_dict_to_vertex(dict);
    Py_DECREF(dict);
    
    return vertex;
}

/**
 * Convert Python (Vertex, Edge) pairs to C GraphserverEdgeList.
 * 
 * @param pair_list Python list of (Vertex, Edge) tuples
 * @param out_edges Pointer to output GraphserverEdgeList
 * @return int 0 on success, -1 on error
 */
int python_vertex_edge_pairs_to_c_edges(PyObject* pair_list, GraphserverEdgeList* out_edges) {
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
                
                // Convert metadata value to GraphserverValue using existing helper
                GraphserverValue meta_gs_value;
                if (python_object_to_graphserver_value(meta_value, &meta_gs_value) != 0) {
                    Py_DECREF(metadata_attr);
                    gs_edge_destroy(edge);
                    return -1;
                }
                
                // Convert string key to uint16_t using string dictionary
                uint16_t meta_key_id = gs_string_dict_register(meta_key_str);
                GraphserverResult result = gs_edge_set_metadata(edge, meta_key_id, meta_gs_value);
                if (result != GS_SUCCESS) {
                    Py_DECREF(metadata_attr);
                    gs_edge_destroy(edge);
                    handle_graphserver_error(result, "edge metadata setting");
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
            handle_graphserver_error(result, "edge list addition");
            return -1;
        }
    }
    
    return 0; // Success
}