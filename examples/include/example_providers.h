#ifndef EXAMPLE_PROVIDERS_H
#define EXAMPLE_PROVIDERS_H

/**
 * @file example_providers.h
 * @brief Example edge providers for integration testing and demonstrations
 * 
 * This header provides various example edge providers that demonstrate
 * real-world usage patterns of the Graphserver Planning Engine. These
 * providers are used for integration testing and serve as examples for
 * building custom providers.
 */

#include "../../core/include/graphserver.h"
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @defgroup transit_provider Transit Provider
 * @brief Public transit simulation with schedules and transfers
 * @{
 */

// Transit route information
typedef struct {
    int route_id;
    const char* route_name;
    const char* route_type; // "bus", "subway", "light_rail"
    double frequency_minutes; // Average frequency during peak hours
    double off_peak_frequency_minutes; // Frequency during off-peak
    double fare_cost;
} TransitRoute;

// Transit stop information
typedef struct {
    int stop_id;
    const char* stop_name;
    double lat;
    double lon;
    TransitRoute* routes; // Array of routes serving this stop
    size_t route_count;
} TransitStop;

// Transit network configuration
typedef struct {
    TransitStop* stops;
    size_t stop_count;
    TransitRoute* routes;
    size_t route_count;
    
    // Network parameters
    double max_walking_distance_to_stop; // meters
    double walking_speed_mps; // meters per second
    double average_wait_time_minutes; // Average waiting time
    double transfer_penalty_minutes; // Extra time penalty for transfers
} TransitNetwork;

/**
 * Create a transit network with example data
 * @return Transit network instance, or NULL on failure
 */
TransitNetwork* transit_network_create_example(void);

/**
 * Destroy transit network and free memory
 * @param network Transit network to destroy
 */
void transit_network_destroy(TransitNetwork* network);

/**
 * Transit provider function for Graphserver engine
 * @param current_vertex Current vertex (should have lat/lon/time)
 * @param out_edges Output edge list
 * @param user_data TransitNetwork pointer
 * @return 0 on success, -1 on failure
 */
int transit_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data
);

/** @} */

/**
 * @defgroup walking_provider Walking Provider
 * @brief Pedestrian navigation with realistic constraints
 * @{
 */

// Walking network configuration
typedef struct {
    double walking_speed_mps; // Normal walking speed in m/s
    double max_walking_distance; // Maximum walking distance in meters
    double elevation_penalty_factor; // Penalty factor for elevation gain
    bool allow_stairs; // Whether stairs are allowed
    bool accessibility_mode; // Accessibility-friendly routing
} WalkingConfig;

/**
 * Create default walking configuration
 * @return Walking configuration with reasonable defaults
 */
WalkingConfig walking_config_default(void);

/**
 * Walking provider function for Graphserver engine
 * @param current_vertex Current vertex (should have lat/lon)
 * @param out_edges Output edge list
 * @param user_data WalkingConfig pointer
 * @return 0 on success, -1 on failure
 */
int walking_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data
);

/** @} */

/**
 * @defgroup road_network_provider Road Network Provider
 * @brief Vehicle routing with traffic simulation
 * @{
 */

// Road segment information
typedef struct {
    int segment_id;
    double start_lat, start_lon;
    double end_lat, end_lon;
    const char* road_type; // "highway", "arterial", "local", "residential"
    double speed_limit_kmh;
    double length_meters;
    bool one_way;
    double current_traffic_factor; // 1.0 = normal, >1.0 = congested
} RoadSegment;

// Road network configuration
typedef struct {
    RoadSegment* segments;
    size_t segment_count;
    
    // Vehicle parameters
    const char* vehicle_type; // "car", "bicycle", "motorcycle"
    double max_speed_kmh;
    bool avoid_highways;
    double traffic_preference; // 0.0 = avoid traffic, 1.0 = ignore traffic
} RoadNetwork;

/**
 * Create road network with example data
 * @param vehicle_type Type of vehicle ("car", "bicycle", etc.)
 * @return Road network instance, or NULL on failure
 */
RoadNetwork* road_network_create_example(const char* vehicle_type);

/**
 * Destroy road network and free memory
 * @param network Road network to destroy
 */
void road_network_destroy(RoadNetwork* network);

/**
 * Road network provider function for Graphserver engine
 * @param current_vertex Current vertex (should have lat/lon)
 * @param out_edges Output edge list
 * @param user_data RoadNetwork pointer
 * @return 0 on success, -1 on failure
 */
int road_network_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data
);

/** @} */

/**
 * @defgroup utility_functions Utility Functions
 * @brief Helper functions for example providers
 * @{
 */

/**
 * Calculate great circle distance between two lat/lon points
 * @param lat1 Latitude of first point (degrees)
 * @param lon1 Longitude of first point (degrees)
 * @param lat2 Latitude of second point (degrees)
 * @param lon2 Longitude of second point (degrees)
 * @return Distance in meters
 */
double calculate_distance_meters(double lat1, double lon1, double lat2, double lon2);

/**
 * Create a location vertex with lat/lon coordinates
 * @param lat Latitude in degrees
 * @param lon Longitude in degrees
 * @param time_seconds Optional time in seconds since epoch (0 for no time)
 * @return Vertex with location data, or NULL on failure
 */
GraphserverVertex* create_location_vertex(double lat, double lon, time_t time_seconds);

/**
 * Extract location from vertex
 * @param vertex Vertex to extract from
 * @param out_lat Output latitude
 * @param out_lon Output longitude
 * @param out_time Output time (may be 0 if no time set)
 * @return true if location extracted successfully
 */
bool extract_location_from_vertex(
    const GraphserverVertex* vertex,
    double* out_lat,
    double* out_lon,
    time_t* out_time
);

/**
 * Create goal predicate for location within radius
 * @param target_lat Target latitude
 * @param target_lon Target longitude
 * @param radius_meters Radius in meters
 * @return Goal predicate function data structure
 */
typedef struct {
    double target_lat;
    double target_lon;
    double radius_meters;
} LocationGoal;

/**
 * Goal predicate function for location-based goals
 * @param vertex Vertex to test
 * @param user_data LocationGoal pointer
 * @return true if vertex is within radius of target
 */
bool location_goal_predicate(const GraphserverVertex* vertex, void* user_data);

/** @} */

#ifdef __cplusplus
}
#endif

#endif // EXAMPLE_PROVIDERS_H