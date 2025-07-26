#include "../include/example_providers.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#ifndef _GNU_SOURCE
#define _GNU_SOURCE  // For strdup
#endif

/**
 * @file road_network_provider.c
 * @brief Implementation of road network provider with traffic simulation
 * 
 * This provider simulates vehicle routing on road networks with different
 * road types, traffic conditions, and vehicle-specific constraints.
 */

// Example road network data (simplified Manhattan-style grid)
static RoadSegment example_segments[] = {
    // East-West streets (numbered streets)
    {1001, 40.7074, -74.0113, 40.7074, -74.0070, "arterial", 35.0, 400.0, false, 1.2},
    {1002, 40.7101, -74.0113, 40.7101, -74.0070, "arterial", 35.0, 400.0, false, 1.1},
    {1003, 40.7128, -74.0113, 40.7128, -74.0070, "local", 25.0, 400.0, false, 1.0},
    
    // North-South avenues
    {2001, 40.7074, -74.0113, 40.7128, -74.0113, "arterial", 45.0, 600.0, false, 1.3},
    {2002, 40.7074, -74.0090, 40.7128, -74.0090, "local", 35.0, 600.0, false, 1.1},
    {2003, 40.7074, -74.0070, 40.7128, -74.0070, "arterial", 45.0, 600.0, false, 1.4},
    
    // Highway segments
    {3001, 40.7050, -74.0200, 40.7150, -74.0100, "highway", 80.0, 1500.0, false, 1.8},
    {3002, 40.7000, -74.0150, 40.7100, -74.0050, "highway", 80.0, 1400.0, false, 1.6},
    
    // Residential streets
    {4001, 40.7080, -74.0100, 40.7080, -74.0080, "residential", 20.0, 200.0, false, 1.0},
    {4002, 40.7090, -74.0100, 40.7090, -74.0080, "residential", 20.0, 200.0, false, 1.0},
    {4003, 40.7110, -74.0105, 40.7110, -74.0085, "residential", 20.0, 200.0, false, 1.0},
    
    // One-way streets
    {5001, 40.7105, -74.0113, 40.7105, -74.0070, "local", 30.0, 400.0, true, 1.2},
    {5002, 40.7120, -74.0070, 40.7120, -74.0113, "local", 30.0, 400.0, true, 1.1},
};

RoadNetwork* road_network_create_example(const char* vehicle_type) {
    RoadNetwork* network = malloc(sizeof(RoadNetwork));
    if (!network) return NULL;
    
    // Copy segment data
    network->segment_count = sizeof(example_segments) / sizeof(example_segments[0]);
    network->segments = malloc(sizeof(RoadSegment) * network->segment_count);
    if (!network->segments) {
        free(network);
        return NULL;
    }
    memcpy(network->segments, example_segments, sizeof(RoadSegment) * network->segment_count);
    
    // Set vehicle-specific parameters
    size_t len = strlen(vehicle_type) + 1;
    char* type_copy = malloc(len);
    if (!type_copy) {
        free(network->segments);
        free(network);
        return NULL;
    }
    strcpy(type_copy, vehicle_type);
    network->vehicle_type = type_copy;
    
    if (strcmp(vehicle_type, "car") == 0) {
        network->max_speed_kmh = 120.0;
        network->avoid_highways = false;
        network->traffic_preference = 0.3; // Moderate traffic avoidance
    } else if (strcmp(vehicle_type, "bicycle") == 0) {
        network->max_speed_kmh = 25.0;
        network->avoid_highways = true; // Bikes not allowed on highways
        network->traffic_preference = 0.0; // Traffic doesn't affect bikes much
    } else if (strcmp(vehicle_type, "motorcycle") == 0) {
        network->max_speed_kmh = 140.0;
        network->avoid_highways = false;
        network->traffic_preference = 0.1; // Can navigate through traffic
    } else {
        // Default to car
        network->max_speed_kmh = 120.0;
        network->avoid_highways = false;
        network->traffic_preference = 0.3;
    }
    
    return network;
}

void road_network_destroy(RoadNetwork* network) {
    if (!network) return;
    
    free((char*)network->vehicle_type);
    free(network->segments);
    free(network);
}

// Calculate effective speed considering traffic and vehicle type
static double calculate_effective_speed(
    const RoadSegment* segment,
    const RoadNetwork* network,
    time_t current_time) {
    
    double base_speed = fmin(segment->speed_limit_kmh, network->max_speed_kmh);
    
    // Apply traffic factor
    double traffic_adjusted_speed = base_speed / segment->current_traffic_factor;
    
    // Apply traffic preference (how much the vehicle tries to avoid traffic)
    double traffic_penalty = (segment->current_traffic_factor - 1.0) * network->traffic_preference;
    double final_speed = traffic_adjusted_speed * (1.0 - traffic_penalty);
    
    // Vehicle-specific adjustments
    if (strcmp(network->vehicle_type, "bicycle") == 0) {
        // Bicycles are slower on arterials due to traffic mixing
        if (strcmp(segment->road_type, "arterial") == 0) {
            final_speed *= 0.7;
        }
        // Bicycles benefit from bike lanes (simulated as residential streets)
        if (strcmp(segment->road_type, "residential") == 0) {
            final_speed *= 1.2;
        }
    }
    
    // Time-of-day adjustments (rush hour vs off-peak)
    struct tm* time_info = localtime(&current_time);
    int hour = time_info->tm_hour;
    bool rush_hour = (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19);
    
    if (rush_hour) {
        if (strcmp(segment->road_type, "highway") == 0) {
            final_speed *= 0.6; // Heavy highway congestion
        } else if (strcmp(segment->road_type, "arterial") == 0) {
            final_speed *= 0.8; // Moderate arterial congestion
        }
    }
    
    return fmax(final_speed, 5.0); // Minimum 5 km/h (walking speed)
}

// Find road segments connected to current location
static void generate_road_edges(
    double current_lat,
    double current_lon,
    time_t current_time,
    const RoadNetwork* network,
    GraphserverEdgeList* out_edges) {
    
    const double CONNECTION_THRESHOLD = 50.0; // meters
    
    for (size_t i = 0; i < network->segment_count; i++) {
        const RoadSegment* segment = &network->segments[i];
        
        // Skip highways if vehicle type doesn't allow them
        if (network->avoid_highways && strcmp(segment->road_type, "highway") == 0) {
            continue;
        }
        
        // Check if current location is near the start of this segment
        double start_distance = calculate_distance_meters(
            current_lat, current_lon, segment->start_lat, segment->start_lon);
        
        if (start_distance <= CONNECTION_THRESHOLD) {
            // Generate edge to end of segment
            double effective_speed = calculate_effective_speed(segment, network, current_time);
            double travel_time_hours = segment->length_meters / 1000.0 / effective_speed;
            double travel_time_minutes = travel_time_hours * 60.0;
            
            // Create destination vertex with all information
            time_t arrival_time = current_time + (time_t)(travel_time_minutes * 60);
            GraphserverKeyPair pairs[] = {
                {"lat", gs_value_create_float(segment->end_lat)},
                {"lon", gs_value_create_float(segment->end_lon)},
                {"time", gs_value_create_int((int64_t)arrival_time)},
                {"mode", gs_value_create_string(network->vehicle_type)},
                {"road_type", gs_value_create_string(segment->road_type)},
                {"segment_id", gs_value_create_int(segment->segment_id)}
            };
            GraphserverVertex* dest_vertex = gs_vertex_create(pairs, 6, NULL);
            if (!dest_vertex) continue;
            
            // Create edge with travel time and fuel cost
            double fuel_cost = segment->length_meters / 1000.0 * 0.15; // $0.15 per km
            double costs[2] = {travel_time_minutes, fuel_cost};
            
            GraphserverEdge* edge = gs_edge_create(dest_vertex, costs, 2);
            if (!edge) {
                gs_vertex_destroy(dest_vertex);
                continue;
            }
            
            // Set edge to own the target vertex since we created it specifically for this edge
            gs_edge_set_owns_target_vertex(edge, true);
            
            // Add metadata
            GraphserverValue edge_mode = gs_value_create_string(network->vehicle_type);
            GraphserverValue edge_road_type = gs_value_create_string(segment->road_type);
            GraphserverValue edge_distance = gs_value_create_float(segment->length_meters);
            GraphserverValue edge_speed = gs_value_create_float(effective_speed);
            GraphserverValue edge_traffic = gs_value_create_float(segment->current_traffic_factor);
            
            gs_edge_set_metadata(edge, "mode", edge_mode);
            gs_edge_set_metadata(edge, "road_type", edge_road_type);
            gs_edge_set_metadata(edge, "distance_meters", edge_distance);
            gs_edge_set_metadata(edge, "speed_kmh", edge_speed);
            gs_edge_set_metadata(edge, "traffic_factor", edge_traffic);
            
            gs_edge_list_add_edge(out_edges, edge);
        }
        
        // Also check reverse direction for two-way roads
        if (!segment->one_way) {
            double end_distance = calculate_distance_meters(
                current_lat, current_lon, segment->end_lat, segment->end_lon);
            
            if (end_distance <= CONNECTION_THRESHOLD) {
                // Generate edge from end to start
                double effective_speed = calculate_effective_speed(segment, network, current_time);
                double travel_time_hours = segment->length_meters / 1000.0 / effective_speed;
                double travel_time_minutes = travel_time_hours * 60.0;
                
                time_t arrival_time = current_time + (time_t)(travel_time_minutes * 60);
                GraphserverKeyPair pairs[] = {
                    {"lat", gs_value_create_float(segment->start_lat)},
                    {"lon", gs_value_create_float(segment->start_lon)},
                    {"time", gs_value_create_int((int64_t)arrival_time)},
                    {"mode", gs_value_create_string(network->vehicle_type)},
                    {"road_type", gs_value_create_string(segment->road_type)},
                    {"segment_id", gs_value_create_int(segment->segment_id)}
                };
                GraphserverVertex* dest_vertex = gs_vertex_create(pairs, 6, NULL);
                if (!dest_vertex) continue;
                
                // Create edge
                double fuel_cost = segment->length_meters / 1000.0 * 0.15;
                double costs[2] = {travel_time_minutes, fuel_cost};
                
                GraphserverEdge* edge = gs_edge_create(dest_vertex, costs, 2);
                if (!edge) {
                    gs_vertex_destroy(dest_vertex);
                    continue;
                }
                
                // Set edge to own the target vertex since we created it specifically for this edge
                gs_edge_set_owns_target_vertex(edge, true);
                
                // Add metadata
                GraphserverValue edge_mode = gs_value_create_string(network->vehicle_type);
                GraphserverValue edge_road_type = gs_value_create_string(segment->road_type);
                GraphserverValue edge_distance = gs_value_create_float(segment->length_meters);
                GraphserverValue edge_speed = gs_value_create_float(effective_speed);
                GraphserverValue edge_traffic = gs_value_create_float(segment->current_traffic_factor);
                
                gs_edge_set_metadata(edge, "mode", edge_mode);
                gs_edge_set_metadata(edge, "road_type", edge_road_type);
                gs_edge_set_metadata(edge, "distance_meters", edge_distance);
                gs_edge_set_metadata(edge, "speed_kmh", edge_speed);
                gs_edge_set_metadata(edge, "traffic_factor", edge_traffic);
                
                gs_edge_list_add_edge(out_edges, edge);
            }
        }
    }
}

int road_network_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    if (!current_vertex || !out_edges || !user_data) return -1;
    
    RoadNetwork* network = (RoadNetwork*)user_data;
    
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
    
    // Check if we're in the correct mode for this vehicle type
    GraphserverValue mode_val;
    if (gs_vertex_get_value(current_vertex, "mode", &mode_val) == GS_SUCCESS) {
        if (mode_val.type == GS_VALUE_STRING) {
            const char* mode = mode_val.as.s_val;
            // Only generate road edges if we're in the right vehicle mode or walking
            if (strcmp(mode, network->vehicle_type) != 0 && strcmp(mode, "walking") != 0) {
                return 0; // Wrong mode, no edges
            }
        }
    }
    
    // Generate road network edges
    generate_road_edges(current_lat, current_lon, current_time, network, out_edges);
    
    return 0;
}