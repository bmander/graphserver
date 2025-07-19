#include "../include/example_providers.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/**
 * @file utility_functions.c
 * @brief Utility functions shared by all example providers
 */

// Earth radius in meters
#define EARTH_RADIUS_M 6371000.0

double calculate_distance_meters(double lat1, double lon1, double lat2, double lon2) {
    // Convert degrees to radians
    double lat1_rad = lat1 * M_PI / 180.0;
    double lon1_rad = lon1 * M_PI / 180.0;
    double lat2_rad = lat2 * M_PI / 180.0;
    double lon2_rad = lon2 * M_PI / 180.0;
    
    // Haversine formula
    double dlat = lat2_rad - lat1_rad;
    double dlon = lon2_rad - lon1_rad;
    
    double a = sin(dlat/2) * sin(dlat/2) + 
               cos(lat1_rad) * cos(lat2_rad) * 
               sin(dlon/2) * sin(dlon/2);
    double c = 2 * atan2(sqrt(a), sqrt(1-a));
    
    return EARTH_RADIUS_M * c;
}

GraphserverVertex* create_location_vertex(double lat, double lon, time_t time_seconds) {
    GraphserverVertex* vertex = gs_vertex_create();
    if (!vertex) return NULL;
    
    // Add latitude and longitude
    GraphserverValue lat_val = gs_value_create_float(lat);
    GraphserverValue lon_val = gs_value_create_float(lon);
    
    GraphserverResult lat_result = gs_vertex_set_kv(vertex, "lat", lat_val);
    GraphserverResult lon_result = gs_vertex_set_kv(vertex, "lon", lon_val);
    
    if (lat_result != GS_SUCCESS || lon_result != GS_SUCCESS) {
        gs_vertex_destroy(vertex);
        return NULL;
    }
    
    // Add time if provided
    if (time_seconds > 0) {
        GraphserverValue time_val = gs_value_create_int((int64_t)time_seconds);
        GraphserverResult time_result = gs_vertex_set_kv(vertex, "time", time_val);
        
        if (time_result != GS_SUCCESS) {
            gs_vertex_destroy(vertex);
            return NULL;
        }
    }
    
    return vertex;
}

bool extract_location_from_vertex(
    const GraphserverVertex* vertex,
    double* out_lat,
    double* out_lon,
    time_t* out_time) {
    
    if (!vertex || !out_lat || !out_lon) return false;
    
    GraphserverValue lat_val, lon_val;
    
    // Extract latitude and longitude
    if (gs_vertex_get_value(vertex, "lat", &lat_val) != GS_SUCCESS ||
        gs_vertex_get_value(vertex, "lon", &lon_val) != GS_SUCCESS) {
        return false;
    }
    
    // Check value types
    if (lat_val.type != GS_VALUE_FLOAT || lon_val.type != GS_VALUE_FLOAT) {
        return false;
    }
    
    *out_lat = lat_val.as.f_val;
    *out_lon = lon_val.as.f_val;
    
    // Extract time if available and requested
    if (out_time) {
        GraphserverValue time_val;
        if (gs_vertex_get_value(vertex, "time", &time_val) == GS_SUCCESS &&
            time_val.type == GS_VALUE_INT) {
            *out_time = (time_t)time_val.as.i_val;
        } else {
            *out_time = 0; // No time available
        }
    }
    
    return true;
}

bool location_goal_predicate(const GraphserverVertex* vertex, void* user_data) {
    if (!vertex || !user_data) return false;
    
    LocationGoal* goal = (LocationGoal*)user_data;
    
    double lat, lon;
    if (!extract_location_from_vertex(vertex, &lat, &lon, NULL)) {
        return false;
    }
    
    double distance = calculate_distance_meters(lat, lon, goal->target_lat, goal->target_lon);
    return distance <= goal->radius_meters;
}