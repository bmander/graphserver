/**
 * @file validation.c
 * @brief Validation and error handling functions for Graphserver extension
 * 
 * This module contains utility functions for validating Python objects,
 * handling GraphServer errors, and converting error conditions to appropriate
 * Python exceptions.
 */

#include "extension.h"

/**
 * Handle GraphServer error codes by setting appropriate Python exceptions.
 * 
 * @param result The GraphServer result code
 * @param operation Description of the operation that failed
 * @return PyObject* Always returns NULL (for use in error return paths)
 */
PyObject* handle_graphserver_error(GraphserverResult result, const char* operation) {
    switch (result) {
        case GS_SUCCESS:
            Py_RETURN_NONE;
        case GS_ERROR_NULL_POINTER:
            PyErr_SetString(PyExc_ValueError, "Invalid null pointer argument");
            break;
        case GS_ERROR_KEY_NOT_FOUND:
            PyErr_Format(PyExc_ValueError, "Resource not found during %s", operation);
            break;
        case GS_ERROR_INVALID_ARGUMENT:
            PyErr_Format(PyExc_ValueError, "Invalid argument for %s", operation);
            break;
        case GS_ERROR_OUT_OF_MEMORY:
            PyErr_NoMemory();
            break;
        case GS_ERROR_TYPE_MISMATCH:
            PyErr_Format(PyExc_TypeError, "Type mismatch during %s", operation);
            break;
        case GS_ERROR_TIMEOUT:
            PyErr_Format(PyExc_TimeoutError, "Timeout occurred during %s", operation);
            break;
        case GS_ERROR_NO_PATH_FOUND:
            PyErr_Format(PyExc_ValueError, "No path found during %s", operation);
            break;
        default:
            PyErr_Format(PyExc_RuntimeError, "%s failed with error code %d", operation, result);
            break;
    }
    return NULL;
}

/**
 * Validate that a Python object is an engine capsule and extract the engine.
 * 
 * @param capsule Python capsule object to validate
 * @param out_engine Pointer to store the extracted GraphserverEngine
 * @return int 0 on success, -1 on error (with Python exception set)
 */
int validate_engine_capsule(PyObject* capsule, GraphserverEngine** out_engine) {
    if (!PyCapsule_CheckExact(capsule)) {
        PyErr_SetString(PyExc_TypeError, "Expected engine capsule");
        return -1;
    }
    
    *out_engine = (GraphserverEngine*)PyCapsule_GetPointer(capsule, "GraphserverEngine");
    if (!*out_engine) {
        return -1; // Error already set by PyCapsule_GetPointer
    }
    
    return 0;
}

/**
 * Validate that a Python object is callable.
 * 
 * @param obj Python object to validate
 * @param name Description of the object for error messages
 * @return int 0 on success, -1 on error (with Python exception set)
 */
int validate_callable(PyObject* obj, const char* name) {
    if (!PyCallable_Check(obj)) {
        PyErr_Format(PyExc_TypeError, "%s must be callable", name);
        return -1;
    }
    return 0;
}