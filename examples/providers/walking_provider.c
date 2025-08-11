#include "../include/example_providers.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "../../core/include/gs_string_dict.h"
#include "../../core/include/gs_common_keys.h"

// Custom keys for walking provider metadata
static uint16_t KEY_DISTANCE_METERS = 0;
static uint16_t KEY_BEARING_DEGREES = 0;
static uint16_t KEY_WALKING_SPEED_MPS = 0;
static uint16_t KEY_ELEVATION_PENALTY = 0;
static uint16_t KEY_DESTINATION_NAME = 0;
static uint16_t KEY_POI_NAME = 0;
static uint16_t KEY_POI_TYPE = 0;

// Initialize custom keys (call once at startup)
void walking_provider_init_keys(void) {
    if (KEY_DISTANCE_METERS == 0) {
        KEY_DISTANCE_METERS = gs_string_dict_register("distance_meters");
        KEY_BEARING_DEGREES = gs_string_dict_register("bearing_degrees");
        KEY_WALKING_SPEED_MPS = gs_string_dict_register("walking_speed_mps");
        KEY_ELEVATION_PENALTY = gs_string_dict_register("elevation_penalty");
        KEY_DESTINATION_NAME = gs_string_dict_register("destination_name");
        KEY_POI_NAME = gs_string_dict_register("poi_name");
        KEY_POI_TYPE = gs_string_dict_register("poi_type");
    }
}

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/**
 * @file walking_provider.c
 * @brief Implementation of walking provider with realistic constraints
 * 
 * This provider generates walking edges between nearby locations with
 * realistic walking speeds, distance limits, and accessibility considerations.
 */

// Default walking parameters
#define DEFAULT_WALKING_SPEED_MPS 1.3  // ~3 mph
#define DEFAULT_MAX_WALKING_DISTANCE 800.0  // 800 meters (~0.5 miles)
#define DEFAULT_ELEVATION_PENALTY 1.5  // 50% penalty for elevation gain
#define GRID_RESOLUTION 100.0  // Generate walking options every 100 meters

WalkingConfig walking_config_default(void) {
    WalkingConfig config;
    config.walking_speed_mps = DEFAULT_WALKING_SPEED_MPS;
    config.max_walking_distance = DEFAULT_MAX_WALKING_DISTANCE;
    config.elevation_penalty_factor = DEFAULT_ELEVATION_PENALTY;
    config.allow_stairs = true;
    config.accessibility_mode = false;
    
    return config;
}

// Generate walking edges in cardinal and diagonal directions with optimized counts
static void generate_walking_edges_grid(
    double current_lat,
    double current_lon,
    time_t current_time,
    const WalkingConfig* config,
    GraphserverEdgeList* out_edges) {
    
    // Generate walking options at 2 distances only (reduced from original)
    double distances[] = {50.0, 150.0}; // Shorter distances for faster search
    size_t num_distances = sizeof(distances) / sizeof(distances[0]);
    
    // 4 cardinal directions only (reduced from 6 or 8) 
    double bearings[] = {0.0, 90.0, 180.0, 270.0}; // N, E, S, W only
    size_t num_bearings = sizeof(bearings) / sizeof(bearings[0]);
    
    for (size_t d = 0; d < num_distances; d++) {
        double distance = distances[d];
        
        if (distance > config->max_walking_distance) continue;
        
        for (size_t b = 0; b < num_bearings; b++) {
            double bearing_deg = bearings[b];
            double bearing_rad = bearing_deg * M_PI / 180.0;
            
            // Calculate destination coordinates using simple approximation
            // (accurate enough for short distances)
            double lat_offset = (distance * cos(bearing_rad)) / 111320.0; // ~111.32 km per degree lat
            double lon_offset = (distance * sin(bearing_rad)) / (111320.0 * cos(current_lat * M_PI / 180.0));
            
            double dest_lat = current_lat + lat_offset;
            double dest_lon = current_lon + lon_offset;
            
            // Calculate walking time
            double base_time_seconds = distance / config->walking_speed_mps;
            
            // Add elevation penalty (simulated based on direction)
            double elevation_factor = 1.0;
            if (bearing_deg >= 315.0 || bearing_deg <= 45.0) { // Northbound - uphill
                elevation_factor = config->elevation_penalty_factor;
            }
            
            double walk_time_seconds = base_time_seconds * elevation_factor;
            
            // Accessibility adjustments
            if (config->accessibility_mode) {
                walk_time_seconds *= 1.3; // 30% longer for accessibility
                if (distance > 200.0) continue; // Shorter max distance
            }
            
            // Create destination vertex with mode
            time_t arrival_time = current_time + (time_t)walk_time_seconds;
            
            GraphserverKeyPair pairs[] = {
                {GS_KEY_LAT, gs_value_create_float(dest_lat)},
                {GS_KEY_LON, gs_value_create_float(dest_lon)},
                {GS_KEY_TIME, gs_value_create_int((int64_t)arrival_time)},
                {GS_KEY_MODE, gs_value_create_string("walking")}
            };
            GraphserverVertex* dest_vertex = gs_vertex_create(pairs, 4, NULL);
            
            // Clean up the values since vertex makes copies
            gs_value_destroy(&pairs[3].value); // mode
            
            if (!dest_vertex) continue;
            
            // Create edge with walking time as cost
            double cost_minutes = walk_time_seconds / 60.0;
            GraphserverEdge* edge = gs_edge_create(dest_vertex, &cost_minutes, 1);
            if (!edge) {
                gs_vertex_destroy(dest_vertex);
                continue;
            }
            
            // Set edge to own the target vertex since we created it specifically for this edge
            gs_edge_set_owns_target_vertex(edge, true);
            
            // Add metadata
            GraphserverValue edge_mode = gs_value_create_string("walking");
            GraphserverValue edge_distance = gs_value_create_float(distance);
            GraphserverValue edge_bearing = gs_value_create_float(bearing_deg);
            GraphserverValue edge_speed = gs_value_create_float(config->walking_speed_mps);
            
            gs_edge_set_metadata(edge, GS_KEY_MODE, edge_mode);
            gs_edge_set_metadata(edge, KEY_DISTANCE_METERS, edge_distance);
            gs_edge_set_metadata(edge, KEY_BEARING_DEGREES, edge_bearing);
            gs_edge_set_metadata(edge, KEY_WALKING_SPEED_MPS, edge_speed);
            
            if (elevation_factor > 1.0) {
                GraphserverValue elevation_penalty = gs_value_create_float(elevation_factor);
                gs_edge_set_metadata(edge, KEY_ELEVATION_PENALTY, elevation_penalty);
            }
            
            gs_edge_list_add_edge(out_edges, edge);
        }
    }
}

// Generate walking edges to specific nearby points of interest
static void generate_walking_edges_poi(
    double current_lat,
    double current_lon,
    time_t current_time,
    const WalkingConfig* config,
    GraphserverEdgeList* out_edges) {
    
    // Example points of interest (in a real implementation, these would come from a database)
    struct {
        double lat;
        double lon;
        const char* name;
        const char* type;
    } pois[] = {
        {40.7074, -74.0113, "Wall Street", "financial"},
        {40.7101, -74.0070, "South Street Seaport", "attraction"},
        {40.7061, -73.9969, "Brooklyn Bridge", "landmark"},
        {40.7505, -73.9884, "Herald Square", "shopping"},
        {40.7580, -73.9855, "Times Square", "attraction"},
        {40.7311, -73.9811, "Stuyvesant Square", "park"},
    };
    
    size_t num_pois = sizeof(pois) / sizeof(pois[0]);
    
    for (size_t i = 0; i < num_pois; i++) {
        double distance = calculate_distance_meters(current_lat, current_lon, pois[i].lat, pois[i].lon);
        
        if (distance > config->max_walking_distance) continue;
        if (distance < 50.0) continue; // Too close, skip
        
        // Calculate walking time
        double base_time_seconds = distance / config->walking_speed_mps;
        
        // Add some randomness for realistic variation
        double time_variation = 1.0 + (rand() % 20 - 10) / 100.0; // ±10%
        double walk_time_seconds = base_time_seconds * time_variation;
        
        if (config->accessibility_mode) {
            walk_time_seconds *= 1.3;
        }
        
        // Create destination vertex with POI information
        time_t arrival_time = current_time + (time_t)walk_time_seconds;
        
        GraphserverKeyPair pairs[] = {
            {GS_KEY_LAT, gs_value_create_float(pois[i].lat)},
            {GS_KEY_LON, gs_value_create_float(pois[i].lon)},
            {GS_KEY_TIME, gs_value_create_int((int64_t)arrival_time)},
            {GS_KEY_MODE, gs_value_create_string("walking")},
            {KEY_POI_NAME, gs_value_create_string(pois[i].name)},
            {KEY_POI_TYPE, gs_value_create_string(pois[i].type)}
        };
        GraphserverVertex* dest_vertex = gs_vertex_create(pairs, 6, NULL);
        
        // Clean up the string values since vertex makes copies
        gs_value_destroy(&pairs[3].value); // mode
        gs_value_destroy(&pairs[4].value); // poi_name
        gs_value_destroy(&pairs[5].value); // poi_type
        
        if (!dest_vertex) continue;
        
        // Create edge
        double cost_minutes = walk_time_seconds / 60.0;
        GraphserverEdge* edge = gs_edge_create(dest_vertex, &cost_minutes, 1);
        if (!edge) {
            gs_vertex_destroy(dest_vertex);
            continue;
        }
        
        // Set edge to own the target vertex since we created it specifically for this edge
        gs_edge_set_owns_target_vertex(edge, true);
        
        // Add metadata
        GraphserverValue edge_mode = gs_value_create_string("walking");
        GraphserverValue edge_distance = gs_value_create_float(distance);
        GraphserverValue edge_poi_name = gs_value_create_string(pois[i].name);
        
        gs_edge_set_metadata(edge, GS_KEY_MODE, edge_mode);
        gs_edge_set_metadata(edge, KEY_DISTANCE_METERS, edge_distance);
        gs_edge_set_metadata(edge, KEY_DESTINATION_NAME, edge_poi_name);
        
        gs_edge_list_add_edge(out_edges, edge);
    }
}

int walking_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    if (!current_vertex || !out_edges || !user_data) return -1;
    
    // Initialize custom keys on first call
    walking_provider_init_keys();
    
    WalkingConfig* config = (WalkingConfig*)user_data;
    
    // Extract current location and time
    double current_lat, current_lon;
    time_t current_time;
    if (!extract_location_from_vertex(current_vertex, &current_lat, &current_lon, &current_time)) {
        return -1;
    }
    
    // If no time is set, use current time
    if (current_time == 0) {
        current_time = time(NULL);
    }
    
    // Check if we're in a mode that allows walking
    GraphserverValue mode_val;
    bool in_transit = false;
    if (gs_vertex_get_value(current_vertex, GS_KEY_MODE, &mode_val) == GS_SUCCESS) {
        if (mode_val.type == GS_VALUE_STRING) {
            const char* mode = mode_val.as.s_val;
            // Don't generate walking edges if we're currently on transit
            if (strcmp(mode, "subway") == 0 || strcmp(mode, "bus") == 0) {
                in_transit = true;
            }
        }
        gs_value_destroy(&mode_val);
    }
    
    if (in_transit) {
        return 0; // No walking edges while on transit
    }
    
    // Generate grid-based walking edges
    generate_walking_edges_grid(current_lat, current_lon, current_time, config, out_edges);
    
    // Generate POI-based walking edges
    generate_walking_edges_poi(current_lat, current_lon, current_time, config, out_edges);
    
    return 0;
}