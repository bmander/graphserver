#ifndef GS_COMMON_KEYS_H
#define GS_COMMON_KEYS_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file gs_common_keys.h
 * @brief Common key definitions for the Graphserver engine
 * 
 * This module defines commonly used keys throughout the Graphserver engine.
 * These keys are registered with the string dictionary at initialization time
 * and provide convenient constants for frequently used metadata keys.
 * 
 * The keys are organized by category for better maintainability.
 */

/**
 * @defgroup common_keys Common Keys
 * @{
 */

// Core location and time keys
extern uint16_t GS_KEY_LAT;           // "lat" - latitude coordinate
extern uint16_t GS_KEY_LON;           // "lon" - longitude coordinate  
extern uint16_t GS_KEY_TIME;          // "time" - timestamp
extern uint16_t GS_KEY_X;             // "x" - x coordinate
extern uint16_t GS_KEY_Y;             // "y" - y coordinate

// Transportation mode and type keys
extern uint16_t GS_KEY_MODE;          // "mode" - transportation mode (walking, transit, etc.)
extern uint16_t GS_KEY_ROAD_TYPE;     // "road_type" - type of road (highway, arterial, etc.)
extern uint16_t GS_KEY_ROUTE_NAME;    // "route_name" - name of transit route
extern uint16_t GS_KEY_VEHICLE_TYPE;  // "vehicle_type" - type of vehicle

// Distance and cost keys  
extern uint16_t GS_KEY_DISTANCE;      // "distance" - distance value
extern uint16_t GS_KEY_COST;          // "cost" - cost value
extern uint16_t GS_KEY_SPEED;         // "speed" - speed value
extern uint16_t GS_KEY_SPEED_KMH;     // "speed_kmh" - speed in km/h

// Identification keys
extern uint16_t GS_KEY_ID;            // "id" - generic identifier
extern uint16_t GS_KEY_SEGMENT_ID;    // "segment_id" - road segment identifier
extern uint16_t GS_KEY_OSM_NODE_ID;   // "osm_node_id" - OpenStreetMap node ID
extern uint16_t GS_KEY_STOP_ID;       // "stop_id" - transit stop identifier

// Navigation and routing keys
extern uint16_t GS_KEY_BEARING;       // "bearing" - direction/bearing
extern uint16_t GS_KEY_DIRECTION;     // "direction" - movement direction
extern uint16_t GS_KEY_TRAFFIC;       // "traffic" - traffic conditions
extern uint16_t GS_KEY_WAIT_TIME;     // "wait_time" - waiting time

// Descriptive keys
extern uint16_t GS_KEY_NAME;          // "name" - generic name
extern uint16_t GS_KEY_DESTINATION;   // "destination" - destination name
extern uint16_t GS_KEY_DESCRIPTION;   // "description" - description text
extern uint16_t GS_KEY_STATUS;        // "status" - status information

// System and metadata keys
extern uint16_t GS_KEY_HASH;          // "_hash" - hash value
extern uint16_t GS_KEY_TYPE;          // "type" - generic type field
extern uint16_t GS_KEY_PRIORITY;      // "priority" - priority value
extern uint16_t GS_KEY_METADATA;      // "metadata" - generic metadata

// Transit-specific keys
extern uint16_t GS_KEY_TRANSIT;       // "transit" - transit mode
extern uint16_t GS_KEY_SUBWAY;        // "subway" - subway/metro mode
extern uint16_t GS_KEY_BUS;           // "bus" - bus mode
extern uint16_t GS_KEY_TRAIN;         // "train" - train mode

// Walking-specific keys
extern uint16_t GS_KEY_WALKING;       // "walking" - walking mode
extern uint16_t GS_KEY_PEDESTRIAN;    // "pedestrian" - pedestrian mode

// Road-specific keys
extern uint16_t GS_KEY_HIGHWAY;       // "highway" - highway road type
extern uint16_t GS_KEY_ARTERIAL;      // "arterial" - arterial road type
extern uint16_t GS_KEY_RESIDENTIAL;   // "residential" - residential road type

// Grid and coordinate system keys (for testing/examples)
extern uint16_t GS_KEY_GRID;          // "grid" - grid identifier
extern uint16_t GS_KEY_ROW;           // "row" - grid row
extern uint16_t GS_KEY_COL;           // "col" - grid column

/**
 * Initialize all common keys by registering them with the string dictionary.
 * This function must be called after gs_string_dict_init() and should be
 * called once at program startup.
 * 
 * Thread-safe: Yes (but should only be called once during initialization)
 * 
 * @return true if all keys were successfully registered, false otherwise
 */
bool gs_common_keys_init(void);

/**
 * Check if common keys have been initialized.
 * 
 * @return true if initialized, false otherwise
 */
bool gs_common_keys_is_initialized(void);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // GS_COMMON_KEYS_H