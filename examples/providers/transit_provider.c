#include "../include/example_providers.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/**
 * @file transit_provider.c
 * @brief Implementation of transit provider with schedule simulation
 * 
 * This provider simulates public transit networks with realistic schedules,
 * waiting times, and transfer penalties. It demonstrates multi-modal routing
 * capabilities for integration testing.
 */

// Example transit network data for NYC-style system
static TransitRoute example_routes[] = {
    {1, "Red Line", "subway", 3.0, 6.0, 2.75},
    {2, "Blue Line", "subway", 4.0, 8.0, 2.75},
    {3, "Green Line", "subway", 5.0, 10.0, 2.75},
    {4, "M15 Bus", "bus", 8.0, 15.0, 2.90},
    {5, "M14 Bus", "bus", 10.0, 20.0, 2.90},
    {6, "Express A", "subway", 2.5, 5.0, 2.75}
};

static TransitStop example_stops[] = {
    // Financial District area
    {101, "Wall St Station", 40.7074, -74.0113, example_routes, 1}, // Red Line
    {102, "Fulton St Station", 40.7101, -74.0070, example_routes, 1}, // Red Line
    {103, "Broadway-Nassau", 40.7107, -74.0102, &example_routes[1], 1}, // Blue Line
    
    // Brooklyn Bridge area  
    {201, "Brooklyn Bridge", 40.7061, -73.9969, &example_routes[2], 1}, // Green Line
    {202, "High St", 40.6995, -73.9904, &example_routes[2], 1}, // Green Line
    
    // Midtown area
    {301, "Times Square", 40.7580, -73.9855, example_routes, 1}, // Red Line
    {302, "Herald Square", 40.7505, -73.9884, &example_routes[1], 1}, // Blue Line
    
    // Bus stops
    {401, "14th St & 1st Ave", 40.7311, -73.9811, &example_routes[4], 1}, // M14 Bus
    {402, "Houston St & 2nd Ave", 40.7251, -73.9897, &example_routes[3], 1}, // M15 Bus
};

// Constants for transit simulation
#define WALKING_SPEED_MPS 1.3 // ~3 mph walking speed
#define MAX_WALKING_TO_STOP 400.0 // 400 meters max walk to stop
#define AVERAGE_WAIT_MINUTES 5.0 // Average wait time
#define TRANSFER_PENALTY_MINUTES 3.0 // Transfer penalty
#define PEAK_HOURS_START 7 // 7 AM
#define PEAK_HOURS_END 19 // 7 PM

TransitNetwork* transit_network_create_example(void) {
    TransitNetwork* network = malloc(sizeof(TransitNetwork));
    if (!network) return NULL;
    
    // Copy route data
    network->route_count = sizeof(example_routes) / sizeof(example_routes[0]);
    network->routes = malloc(sizeof(TransitRoute) * network->route_count);
    if (!network->routes) {
        free(network);
        return NULL;
    }
    memcpy(network->routes, example_routes, sizeof(TransitRoute) * network->route_count);
    
    // Copy stop data
    network->stop_count = sizeof(example_stops) / sizeof(example_stops[0]);
    network->stops = malloc(sizeof(TransitStop) * network->stop_count);
    if (!network->stops) {
        free(network->routes);
        free(network);
        return NULL;
    }
    memcpy(network->stops, example_stops, sizeof(TransitStop) * network->stop_count);
    
    // Set network parameters
    network->max_walking_distance_to_stop = MAX_WALKING_TO_STOP;
    network->walking_speed_mps = WALKING_SPEED_MPS;
    network->average_wait_time_minutes = AVERAGE_WAIT_MINUTES;
    network->transfer_penalty_minutes = TRANSFER_PENALTY_MINUTES;
    
    return network;
}

void transit_network_destroy(TransitNetwork* network) {
    if (!network) return;
    
    free(network->routes);
    free(network->stops);
    free(network);
}

// Helper function to check if current time is peak hours
static bool is_peak_hours(time_t current_time) {
    struct tm* time_info = localtime(&current_time);
    int hour = time_info->tm_hour;
    return (hour >= PEAK_HOURS_START && hour <= PEAK_HOURS_END);
}

// Helper function to get frequency for a route at current time
static double get_route_frequency(const TransitRoute* route, time_t current_time) {
    if (is_peak_hours(current_time)) {
        return route->frequency_minutes;
    } else {
        return route->off_peak_frequency_minutes;
    }
}

// Create a transit edge from current location to a stop
static GraphserverEdge* create_walk_to_stop_edge(
    const TransitStop* stop,
    double current_lat,
    double current_lon,
    time_t current_time) {
    
    double distance = calculate_distance_meters(current_lat, current_lon, stop->lat, stop->lon);
    double walk_time_minutes = (distance / WALKING_SPEED_MPS) / 60.0;
    
    // Create target vertex at the stop
    GraphserverVertex* stop_vertex = create_location_vertex(stop->lat, stop->lon, current_time + (time_t)(walk_time_minutes * 60));
    if (!stop_vertex) return NULL;
    
    // Add stop information
    GraphserverValue stop_id = gs_value_create_int(stop->stop_id);
    GraphserverValue stop_name = gs_value_create_string(stop->stop_name);
    GraphserverValue mode = gs_value_create_string("walking");
    
    gs_vertex_set_kv(stop_vertex, "stop_id", stop_id);
    gs_vertex_set_kv(stop_vertex, "stop_name", stop_name);
    gs_vertex_set_kv(stop_vertex, "mode", mode);
    
    // Create edge with walk time as cost
    double cost = walk_time_minutes;
    GraphserverEdge* edge = gs_edge_create(stop_vertex, &cost, 1);
    if (!edge) {
        gs_vertex_destroy(stop_vertex);
        return NULL;
    }
    
    // Set edge to own the target vertex since we created it specifically for this edge
    gs_edge_set_owns_target_vertex(edge, true);
    
    // Add metadata to edge
    GraphserverValue edge_mode = gs_value_create_string("walking");
    GraphserverValue edge_distance = gs_value_create_float(distance);
    gs_edge_set_metadata(edge, "mode", edge_mode);
    gs_edge_set_metadata(edge, "distance_meters", edge_distance);
    
    return edge;
}

// Create a transit edge from a stop to next stops on the route
static GraphserverEdge* create_transit_edge(
    const TransitStop* from_stop,
    const TransitStop* to_stop,
    const TransitRoute* route,
    time_t current_time) {
    
    double distance = calculate_distance_meters(from_stop->lat, from_stop->lon, to_stop->lat, to_stop->lon);
    
    // Estimate travel time based on route type and distance
    double travel_speed_kmh;
    if (strcmp(route->route_type, "subway") == 0) {
        travel_speed_kmh = 35.0; // Average subway speed
    } else if (strcmp(route->route_type, "bus") == 0) {
        travel_speed_kmh = 15.0; // Average bus speed with stops
    } else {
        travel_speed_kmh = 25.0; // Light rail
    }
    
    double travel_time_minutes = (distance / 1000.0) / travel_speed_kmh * 60.0;
    double frequency = get_route_frequency(route, current_time);
    double wait_time = frequency / 2.0; // Average wait time is half the frequency
    
    double total_time = wait_time + travel_time_minutes;
    
    // Create target vertex
    time_t arrival_time = current_time + (time_t)(total_time * 60);
    GraphserverVertex* target_vertex = create_location_vertex(to_stop->lat, to_stop->lon, arrival_time);
    if (!target_vertex) return NULL;
    
    // Add stop and route information
    GraphserverValue stop_id = gs_value_create_int(to_stop->stop_id);
    GraphserverValue stop_name = gs_value_create_string(to_stop->stop_name);
    GraphserverValue mode = gs_value_create_string(route->route_type);
    GraphserverValue route_name = gs_value_create_string(route->route_name);
    
    gs_vertex_set_kv(target_vertex, "stop_id", stop_id);
    gs_vertex_set_kv(target_vertex, "stop_name", stop_name);
    gs_vertex_set_kv(target_vertex, "mode", mode);
    gs_vertex_set_kv(target_vertex, "route_name", route_name);
    
    // Create edge with multi-objective cost: [time, fare]
    double costs[2] = {total_time, route->fare_cost};
    GraphserverEdge* edge = gs_edge_create(target_vertex, costs, 2);
    if (!edge) {
        gs_vertex_destroy(target_vertex);
        return NULL;
    }
    
    // Set edge to own the target vertex since we created it specifically for this edge
    gs_edge_set_owns_target_vertex(edge, true);
    
    // Add metadata
    GraphserverValue edge_mode = gs_value_create_string(route->route_type);
    GraphserverValue edge_route = gs_value_create_string(route->route_name);
    GraphserverValue edge_distance = gs_value_create_float(distance);
    GraphserverValue edge_wait = gs_value_create_float(wait_time);
    
    gs_edge_set_metadata(edge, "mode", edge_mode);
    gs_edge_set_metadata(edge, "route_name", edge_route);
    gs_edge_set_metadata(edge, "distance_meters", edge_distance);
    gs_edge_set_metadata(edge, "wait_time_minutes", edge_wait);
    
    return edge;
}

int transit_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    if (!current_vertex || !out_edges || !user_data) return -1;
    
    TransitNetwork* network = (TransitNetwork*)user_data;
    
    // Extract current location and time
    double current_lat, current_lon;
    time_t current_time;
    if (!extract_location_from_vertex(current_vertex, &current_lat, &current_lon, &current_time)) {
        return -1; // No location data
    }
    
    // If no time is set, use current time
    if (current_time == 0) {
        current_time = time(NULL);
    }
    
    // Check if we're already at a transit stop
    GraphserverValue stop_id_val;
    bool at_stop = (gs_vertex_get_value(current_vertex, "stop_id", &stop_id_val) == GS_SUCCESS);
    
    if (at_stop) {
        // Generate transit edges from this stop
        int stop_id = (int)stop_id_val.as.i_val;
        
        // Find the stop in our network
        TransitStop* current_stop = NULL;
        for (size_t i = 0; i < network->stop_count; i++) {
            if (network->stops[i].stop_id == stop_id) {
                current_stop = &network->stops[i];
                break;
            }
        }
        
        if (!current_stop) return -1;
        
        // Generate edges for each route serving this stop
        for (size_t r = 0; r < current_stop->route_count; r++) {
            TransitRoute* route = &current_stop->routes[r];
            
            // Find other stops on this route
            for (size_t s = 0; s < network->stop_count; s++) {
                TransitStop* other_stop = &network->stops[s];
                if (other_stop->stop_id == stop_id) continue; // Skip same stop
                
                // Check if this stop is served by the same route
                bool same_route = false;
                for (size_t or = 0; or < other_stop->route_count; or++) {
                    if (other_stop->routes[or].route_id == route->route_id) {
                        same_route = true;
                        break;
                    }
                }
                
                if (same_route) {
                    GraphserverEdge* edge = create_transit_edge(current_stop, other_stop, route, current_time);
                    if (edge) {
                        gs_edge_list_add_edge(out_edges, edge);
                    }
                }
            }
        }
        
        // Also allow walking away from the stop
        GraphserverVertex* walk_vertex = create_location_vertex(current_lat, current_lon, current_time);
        if (walk_vertex) {
            GraphserverValue mode = gs_value_create_string("walking");
            gs_vertex_set_kv(walk_vertex, "mode", mode);
            
            double cost = 0.0; // No cost to start walking
            GraphserverEdge* walk_edge = gs_edge_create(walk_vertex, &cost, 1);
            if (walk_edge) {
                GraphserverValue edge_mode = gs_value_create_string("walking");
                gs_edge_set_metadata(walk_edge, "mode", edge_mode);
                gs_edge_list_add_edge(out_edges, walk_edge);
            }
        }
        
    } else {
        // Generate walking edges to nearby transit stops
        for (size_t i = 0; i < network->stop_count; i++) {
            TransitStop* stop = &network->stops[i];
            double distance = calculate_distance_meters(current_lat, current_lon, stop->lat, stop->lon);
            
            if (distance <= network->max_walking_distance_to_stop) {
                GraphserverEdge* edge = create_walk_to_stop_edge(stop, current_lat, current_lon, current_time);
                if (edge) {
                    gs_edge_list_add_edge(out_edges, edge);
                }
            }
        }
    }
    
    return 0;
}