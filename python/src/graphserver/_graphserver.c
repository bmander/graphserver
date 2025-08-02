/**
 * @file _graphserver.c
 * @brief Main Python C extension module for Graphserver Planning Engine
 * 
 * This is the main module file that defines the Python extension module structure
 * and exports all the functions. The actual implementation is split across multiple
 * files for better maintainability.
 */

#include "extension/extension.h"

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