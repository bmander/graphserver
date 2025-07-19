#ifndef GS_TYPES_H
#define GS_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Forward declarations
typedef struct GraphserverValue GraphserverValue;
typedef struct GraphserverKeyPair GraphserverKeyPair;
typedef struct GraphserverVertex GraphserverVertex;
typedef struct GraphserverEdge GraphserverEdge;
typedef struct GraphserverEdgeList GraphserverEdgeList;
typedef struct GraphserverEngine GraphserverEngine;
typedef struct GraphserverPath GraphserverPath;
typedef struct GraphserverPathList GraphserverPathList;

// Value type enumeration
typedef enum {
    GS_VALUE_INT = 0,
    GS_VALUE_FLOAT,
    GS_VALUE_STRING,
    GS_VALUE_BOOL,
    GS_VALUE_INT_ARRAY,
    GS_VALUE_FLOAT_ARRAY,
    GS_VALUE_STRING_ARRAY,
    GS_VALUE_BOOL_ARRAY
} GraphserverValueType;

// Array structure for value arrays
typedef struct {
    size_t size;
    void* data;
} GraphserverArray;

// Value structure supporting multiple types
struct GraphserverValue {
    GraphserverValueType type;
    union {
        int64_t i_val;
        double f_val;
        const char* s_val;
        bool b_val;
        GraphserverArray array_val;
    } as;
};

// Key-value pair structure
struct GraphserverKeyPair {
    const char* key;
    GraphserverValue value;
};

// Edge structure with multi-objective support
struct GraphserverEdge {
    GraphserverVertex* target_vertex;
    double* distance_vector;
    size_t distance_vector_size;
    GraphserverKeyPair* metadata;
    size_t metadata_count;
};

// List of edges returned by providers
struct GraphserverEdgeList {
    size_t num_edges;
    GraphserverEdge** edges;
    size_t capacity;
};

// Function pointer types for edge providers and goal predicates
typedef int (*gs_generate_edges_fn)(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data
);

typedef bool (*gs_goal_predicate_fn)(
    const GraphserverVertex* vertex,
    void* user_data
);

typedef void (*gs_heuristic_fn)(
    const GraphserverVertex* vertex,
    double* out_distance_vector,
    void* user_data
);

// Planning options structure
typedef struct {
    const char* planner_name;
    const GraphserverVertex* start_vertex;
    gs_goal_predicate_fn is_goal_fn;
    void* is_goal_user_data;
    
    gs_heuristic_fn heuristic_fn;
    void* heuristic_user_data;
    
    const double* distance_weights;
    size_t distance_vector_size;
    
    uint32_t max_path_alternatives;
    double timeout_seconds;
} GraphserverPlanOptions;

// Return codes
typedef enum {
    GS_SUCCESS = 0,
    GS_ERROR_NULL_POINTER,
    GS_ERROR_INVALID_ARGUMENT,
    GS_ERROR_OUT_OF_MEMORY,
    GS_ERROR_KEY_NOT_FOUND,
    GS_ERROR_TYPE_MISMATCH,
    GS_ERROR_TIMEOUT,
    GS_ERROR_NO_PATH_FOUND
} GraphserverResult;

#ifdef __cplusplus
}
#endif

#endif // GS_TYPES_H