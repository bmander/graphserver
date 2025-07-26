#ifndef TEST_UTILS_H
#define TEST_UTILS_H

#include <time.h>
#include "../include/gs_vertex.h"

/**
 * @brief Safe vertex creation helper that properly manages memory
 * 
 * This function creates a vertex from key-value pairs and automatically
 * cleans up the temporary values to prevent memory leaks.
 * 
 * @param pairs Array of key-value pairs
 * @param num_pairs Number of pairs in the array
 * @param optional_hash Optional hash value, or NULL to auto-calculate
 * @return Created vertex or NULL on failure
 */
static inline GraphserverVertex* create_vertex_safe(GraphserverKeyPair* pairs, size_t num_pairs, const uint64_t* optional_hash) {
    // Create the vertex (which makes copies of all values)
    GraphserverVertex* vertex = gs_vertex_create(pairs, num_pairs, optional_hash);
    
    // Always clean up the original values since gs_vertex_create makes copies
    for (size_t i = 0; i < num_pairs; i++) {
        gs_value_destroy(&pairs[i].value);
    }
    
    return vertex;
}

/**
 * @brief Create a simple test vertex with name, lat, lon
 */
static inline GraphserverVertex* create_test_vertex_safe(const char* name, double lat, double lon) {
    GraphserverKeyPair pairs[] = {
        {"name", gs_value_create_string(name)},
        {"lat", gs_value_create_float(lat)},
        {"lon", gs_value_create_float(lon)}
    };
    
    return create_vertex_safe(pairs, 3, NULL);
}

/**
 * @brief Create a simple test vertex with just a name
 */
static inline GraphserverVertex* create_named_vertex_safe(const char* name) {
    GraphserverKeyPair pairs[] = {
        {"name", gs_value_create_string(name)}
    };
    
    return create_vertex_safe(pairs, 1, NULL);
}

/**
 * @brief Create a coordinate vertex with x, y values
 */
static inline GraphserverVertex* create_coordinate_vertex_safe(int x, int y) {
    GraphserverKeyPair pairs[] = {
        {"x", gs_value_create_int(x)},
        {"y", gs_value_create_int(y)}
    };
    
    return create_vertex_safe(pairs, 2, NULL);
}

/**
 * @brief Create a location vertex with lat, lon, and optional time
 */
static inline GraphserverVertex* create_location_vertex_safe(double lat, double lon, time_t time_seconds) {
    GraphserverKeyPair pairs[3];
    size_t pair_count = 2;
    
    pairs[0] = (GraphserverKeyPair){"lat", gs_value_create_float(lat)};
    pairs[1] = (GraphserverKeyPair){"lon", gs_value_create_float(lon)};
    
    // Add time if provided
    if (time_seconds > 0) {
        pairs[2] = (GraphserverKeyPair){"time", gs_value_create_int((int64_t)time_seconds)};
        pair_count = 3;
    }
    
    return create_vertex_safe(pairs, pair_count, NULL);
}

#endif // TEST_UTILS_H