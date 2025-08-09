#include "../include/gs_common_keys.h"
#include "../include/gs_string_dict.h"
#include <stdbool.h>

/**
 * @file common_keys.c
 * @brief Implementation of common key registration and management
 */

// Core location and time keys
uint16_t GS_KEY_LAT = 0;
uint16_t GS_KEY_LON = 0;
uint16_t GS_KEY_TIME = 0;
uint16_t GS_KEY_X = 0;
uint16_t GS_KEY_Y = 0;

// Transportation mode and type keys
uint16_t GS_KEY_MODE = 0;
uint16_t GS_KEY_ROAD_TYPE = 0;
uint16_t GS_KEY_ROUTE_NAME = 0;
uint16_t GS_KEY_VEHICLE_TYPE = 0;

// Distance and cost keys
uint16_t GS_KEY_DISTANCE = 0;
uint16_t GS_KEY_COST = 0;
uint16_t GS_KEY_SPEED = 0;
uint16_t GS_KEY_SPEED_KMH = 0;

// Identification keys
uint16_t GS_KEY_ID = 0;
uint16_t GS_KEY_SEGMENT_ID = 0;
uint16_t GS_KEY_OSM_NODE_ID = 0;
uint16_t GS_KEY_STOP_ID = 0;

// Navigation and routing keys
uint16_t GS_KEY_BEARING = 0;
uint16_t GS_KEY_DIRECTION = 0;
uint16_t GS_KEY_TRAFFIC = 0;
uint16_t GS_KEY_WAIT_TIME = 0;

// Descriptive keys
uint16_t GS_KEY_NAME = 0;
uint16_t GS_KEY_DESTINATION = 0;
uint16_t GS_KEY_DESCRIPTION = 0;
uint16_t GS_KEY_STATUS = 0;

// System and metadata keys
uint16_t GS_KEY_HASH = 0;
uint16_t GS_KEY_TYPE = 0;
uint16_t GS_KEY_PRIORITY = 0;
uint16_t GS_KEY_METADATA = 0;

// Transit-specific keys
uint16_t GS_KEY_TRANSIT = 0;
uint16_t GS_KEY_SUBWAY = 0;
uint16_t GS_KEY_BUS = 0;
uint16_t GS_KEY_TRAIN = 0;

// Walking-specific keys
uint16_t GS_KEY_WALKING = 0;
uint16_t GS_KEY_PEDESTRIAN = 0;

// Road-specific keys
uint16_t GS_KEY_HIGHWAY = 0;
uint16_t GS_KEY_ARTERIAL = 0;
uint16_t GS_KEY_RESIDENTIAL = 0;

// Grid and coordinate system keys
uint16_t GS_KEY_GRID = 0;
uint16_t GS_KEY_ROW = 0;
uint16_t GS_KEY_COL = 0;

// Initialization flag
static bool g_common_keys_initialized = false;

bool gs_common_keys_init(void) {
    if (g_common_keys_initialized) {
        return true;  // Already initialized
    }
    
    // Check if string dictionary is initialized
    if (!gs_string_dict_is_initialized()) {
        return false;
    }
    
    // Define all the strings to register
    const char* key_strings[] = {
        // Core location and time keys
        "lat", "lon", "time", "x", "y",
        
        // Transportation mode and type keys
        "mode", "road_type", "route_name", "vehicle_type",
        
        // Distance and cost keys
        "distance", "cost", "speed", "speed_kmh",
        
        // Identification keys
        "id", "segment_id", "osm_node_id", "stop_id",
        
        // Navigation and routing keys
        "bearing", "direction", "traffic", "wait_time",
        
        // Descriptive keys
        "name", "destination", "description", "status",
        
        // System and metadata keys
        "_hash", "type", "priority", "metadata",
        
        // Transit-specific keys
        "transit", "subway", "bus", "train",
        
        // Walking-specific keys
        "walking", "pedestrian",
        
        // Road-specific keys
        "highway", "arterial", "residential",
        
        // Grid and coordinate system keys
        "grid", "row", "col"
    };
    
    // Array to hold the resulting IDs
    uint16_t key_ids[sizeof(key_strings) / sizeof(key_strings[0])];
    
    // Register all keys in batch
    size_t num_keys = sizeof(key_strings) / sizeof(key_strings[0]);
    gs_string_dict_register_batch(key_strings, key_ids, num_keys);
    
    // Assign IDs to global variables in the same order
    size_t idx = 0;
    
    // Core location and time keys
    GS_KEY_LAT = key_ids[idx++];
    GS_KEY_LON = key_ids[idx++];
    GS_KEY_TIME = key_ids[idx++];
    GS_KEY_X = key_ids[idx++];
    GS_KEY_Y = key_ids[idx++];
    
    // Transportation mode and type keys
    GS_KEY_MODE = key_ids[idx++];
    GS_KEY_ROAD_TYPE = key_ids[idx++];
    GS_KEY_ROUTE_NAME = key_ids[idx++];
    GS_KEY_VEHICLE_TYPE = key_ids[idx++];
    
    // Distance and cost keys
    GS_KEY_DISTANCE = key_ids[idx++];
    GS_KEY_COST = key_ids[idx++];
    GS_KEY_SPEED = key_ids[idx++];
    GS_KEY_SPEED_KMH = key_ids[idx++];
    
    // Identification keys
    GS_KEY_ID = key_ids[idx++];
    GS_KEY_SEGMENT_ID = key_ids[idx++];
    GS_KEY_OSM_NODE_ID = key_ids[idx++];
    GS_KEY_STOP_ID = key_ids[idx++];
    
    // Navigation and routing keys
    GS_KEY_BEARING = key_ids[idx++];
    GS_KEY_DIRECTION = key_ids[idx++];
    GS_KEY_TRAFFIC = key_ids[idx++];
    GS_KEY_WAIT_TIME = key_ids[idx++];
    
    // Descriptive keys
    GS_KEY_NAME = key_ids[idx++];
    GS_KEY_DESTINATION = key_ids[idx++];
    GS_KEY_DESCRIPTION = key_ids[idx++];
    GS_KEY_STATUS = key_ids[idx++];
    
    // System and metadata keys
    GS_KEY_HASH = key_ids[idx++];
    GS_KEY_TYPE = key_ids[idx++];
    GS_KEY_PRIORITY = key_ids[idx++];
    GS_KEY_METADATA = key_ids[idx++];
    
    // Transit-specific keys
    GS_KEY_TRANSIT = key_ids[idx++];
    GS_KEY_SUBWAY = key_ids[idx++];
    GS_KEY_BUS = key_ids[idx++];
    GS_KEY_TRAIN = key_ids[idx++];
    
    // Walking-specific keys
    GS_KEY_WALKING = key_ids[idx++];
    GS_KEY_PEDESTRIAN = key_ids[idx++];
    
    // Road-specific keys
    GS_KEY_HIGHWAY = key_ids[idx++];
    GS_KEY_ARTERIAL = key_ids[idx++];
    GS_KEY_RESIDENTIAL = key_ids[idx++];
    
    // Grid and coordinate system keys
    GS_KEY_GRID = key_ids[idx++];
    GS_KEY_ROW = key_ids[idx++];
    GS_KEY_COL = key_ids[idx++];
    
    // Verify all keys were successfully registered
    bool all_registered = true;
    for (size_t i = 0; i < num_keys; i++) {
        if (key_ids[i] == 0) {  // GS_INVALID_KEY_ID
            all_registered = false;
            break;
        }
    }
    
    if (all_registered) {
        g_common_keys_initialized = true;
    }
    
    return all_registered;
}

bool gs_common_keys_is_initialized(void) {
    return g_common_keys_initialized;
}