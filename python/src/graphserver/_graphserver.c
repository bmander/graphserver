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
static PyObject* py_create_engine(PyObject* self, PyObject* args);
static PyObject* py_register_provider(PyObject* self, PyObject* args);
static PyObject* py_plan(PyObject* self, PyObject* args, PyObject* kwargs);

// Utility functions for data conversion (implemented in Phase 2)
static PyObject* vertex_to_python_dict(const GraphserverVertex* vertex);
static GraphserverVertex* python_dict_to_vertex(PyObject* dict);
static PyObject* path_to_python_list(const GraphserverPath* path);
static int python_edges_to_c_edges(PyObject* edge_list, GraphserverEdgeList* out_edges);

// Provider wrapper for calling Python functions from C
static int python_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data);

// Data structure for Python provider information
typedef struct {
    PyObject* python_function;
    char* provider_name;
} PythonProviderData;

// PyCapsule destructor for engine cleanup
static void engine_capsule_destructor(PyObject* capsule) {
    GraphserverEngine* engine = (GraphserverEngine*)PyCapsule_GetPointer(capsule, "GraphserverEngine");
    if (engine) {
        gs_engine_destroy(engine);
    }
}

// Module function implementations

static PyObject* py_create_engine(PyObject* self, PyObject* args) {
    (void)self;  // Unused parameter
    (void)args;  // No arguments expected
    
    GraphserverEngine* engine = gs_engine_create();  // Default config
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
    
    // Phase 1: Placeholder implementation
    // Phase 2 will add real data conversion and planning
    PyErr_SetString(PyExc_NotImplementedError, 
                   "Path planning implementation coming in Phase 2");
    return NULL;
}

// Provider wrapper function (placeholder for Phase 2)
static int python_provider_wrapper(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    (void)current_vertex;  // Phase 2 implementation
    (void)out_edges;       // Phase 2 implementation
    (void)user_data;       // Phase 2 implementation
    
    // Phase 1: Return empty edge list
    out_edges->edges = NULL;
    out_edges->num_edges = 0;
    return 0;
}

// Placeholder data conversion functions (Phase 2 implementation)
static PyObject* vertex_to_python_dict(const GraphserverVertex* vertex) {
    (void)vertex;
    return PyDict_New();  // Empty dict for now
}

static GraphserverVertex* python_dict_to_vertex(PyObject* dict) {
    (void)dict;
    return gs_vertex_create();  // Empty vertex for now
}

static PyObject* path_to_python_list(const GraphserverPath* path) {
    (void)path;
    return PyList_New(0);  // Empty list for now
}

static int python_edges_to_c_edges(PyObject* edge_list, GraphserverEdgeList* out_edges) {
    (void)edge_list;
    out_edges->edges = NULL;
    out_edges->num_edges = 0;
    return 0;
}

// Method definitions with modern argument parsing
static PyMethodDef GraphserverMethods[] = {
    {"create_engine", py_create_engine, METH_NOARGS, 
     "Create a new planning engine"},
    {"register_provider", py_register_provider, METH_VARARGS, 
     "Register a Python function as an edge provider"},
    {"plan", (PyCFunction)(void(*)(void))py_plan, METH_VARARGS | METH_KEYWORDS, 
     "Execute pathfinding from start to goal"},
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