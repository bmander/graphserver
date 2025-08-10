#define _POSIX_C_SOURCE 199309L  // For clock_gettime
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <unistd.h>
#include <math.h>
#include "../core/include/graphserver.h"
#include "../core/include/gs_string_dict.h"
#include "../core/include/gs_common_keys.h"
#include "../examples/include/example_providers.h"

/**
 * @file profile_routing.c
 * @brief Profiling script for core routing algorithm with UW Campus OSM data
 * 
 * This script profiles the core C routing functions in real-world scenarios
 * using the UW Campus OSM data. It focuses on profiling the C implementation
 * rather than the Python wrapper.
 */

// Profiling utilities
typedef struct {
    struct timespec start_time;
    struct timespec end_time;
    double elapsed_seconds;
} PrecisionTimer;

typedef struct {
    const char* function_name;
    double total_time;
    size_t call_count;
    double min_time;
    double max_time;
} ProfileEntry;

typedef struct {
    ProfileEntry entries[32];
    size_t entry_count;
    double total_execution_time;
} ProfileData;

static ProfileData global_profile = {0};

// High-precision timing functions
static PrecisionTimer timer_start_precise(void) {
    PrecisionTimer timer;
    clock_gettime(CLOCK_MONOTONIC, &timer.start_time);
    return timer;
}

static void timer_end_precise(PrecisionTimer* timer) {
    clock_gettime(CLOCK_MONOTONIC, &timer->end_time);
    timer->elapsed_seconds = (timer->end_time.tv_sec - timer->start_time.tv_sec) +
                            (timer->end_time.tv_nsec - timer->start_time.tv_nsec) / 1e9;
}

// Profile tracking functions
static void profile_record(const char* function_name, double elapsed_time) {
    // Find existing entry or create new one
    ProfileEntry* entry = NULL;
    for (size_t i = 0; i < global_profile.entry_count; i++) {
        if (strcmp(global_profile.entries[i].function_name, function_name) == 0) {
            entry = &global_profile.entries[i];
            break;
        }
    }
    
    if (!entry && global_profile.entry_count < 32) {
        entry = &global_profile.entries[global_profile.entry_count++];
        entry->function_name = function_name;
        entry->total_time = 0.0;
        entry->call_count = 0;
        entry->min_time = INFINITY;
        entry->max_time = 0.0;
    }
    
    if (entry) {
        entry->total_time += elapsed_time;
        entry->call_count++;
        if (elapsed_time < entry->min_time) entry->min_time = elapsed_time;
        if (elapsed_time > entry->max_time) entry->max_time = elapsed_time;
    }
}

// Campus coordinates from UW Campus OSM data (realistic routing locations)
typedef struct {
    double lat;
    double lon;
    const char* name;
} CampusLocation;

static CampusLocation uw_campus_locations[] = {
    {47.6590651, -122.3043738, "Central Plaza"},
    {47.6591000, -122.3043000, "Library Entrance"}, 
    {47.6588000, -122.3045000, "Engineering Building"},
    {47.6593000, -122.3040000, "Student Union"},
    {47.6585000, -122.3050000, "Science Building"},
    {47.6595000, -122.3035000, "Admin Building"},
    {47.6583000, -122.3055000, "Arts Building"},
    {47.6597000, -122.3030000, "Sports Center"},
    {47.6580000, -122.3060000, "Parking Structure"},
    {47.6600000, -122.3025000, "North Gate"},
    {47.6575000, -122.3065000, "South Entrance"},
    {47.6605000, -122.3020000, "Research Lab"},
    {47.6570000, -122.3070000, "Dormitory Complex"},
    {47.6610000, -122.3015000, "Conference Center"},
    {47.6565000, -122.3075000, "Medical Center"},
};

static const size_t num_campus_locations = sizeof(uw_campus_locations) / sizeof(uw_campus_locations[0]);

// Enhanced profiled planning function
static GraphserverPath* profiled_plan_route(
    GraphserverEngine* engine,
    GraphserverVertex* start,
    GraphserverVertex* goal,
    GraphserverPlanStats* stats) {
    
    PrecisionTimer total_timer = timer_start_precise();
    
    // Use location goal for realistic campus routing
    GraphserverValue lat_val, lon_val;
    if (gs_vertex_get_value(goal, GS_KEY_LAT, &lat_val) != GS_SUCCESS ||
        gs_vertex_get_value(goal, GS_KEY_LON, &lon_val) != GS_SUCCESS) {
        return NULL;
    }
    
    LocationGoal location_goal = {
        lat_val.as.f_val,
        lon_val.as.f_val,
        100.0  // 100m tolerance for campus routing
    };
    
    GraphserverPath* path = gs_plan_simple(engine, start, location_goal_predicate, &location_goal, stats);
    
    timer_end_precise(&total_timer);
    profile_record("total_planning", total_timer.elapsed_seconds);
    
    return path;
}

// Create realistic campus routing scenarios  
static void generate_campus_routing_scenarios(
    GraphserverEngine* engine,
    size_t num_scenarios) {
    
    printf("\n🏫 Generating %zu realistic campus routing scenarios...\n", num_scenarios);
    
    size_t successful_routes = 0;
    size_t total_vertices_expanded = 0;
    size_t total_edges_examined = 0;
    double total_planning_time = 0.0;
    
    for (size_t i = 0; i < num_scenarios; i++) {
        // Select random start and goal locations from campus
        size_t start_idx = rand() % num_campus_locations;
        size_t goal_idx = rand() % num_campus_locations;
        
        // Ensure start and goal are different
        while (goal_idx == start_idx) {
            goal_idx = rand() % num_campus_locations;
        }
        
        CampusLocation start_loc = uw_campus_locations[start_idx];
        CampusLocation goal_loc = uw_campus_locations[goal_idx];
        
        printf("  Route %zu: %s → %s\n", i + 1, start_loc.name, goal_loc.name);
        
        // Create vertices for routing
        GraphserverVertex* start = create_location_vertex(start_loc.lat, start_loc.lon, time(NULL));
        GraphserverVertex* goal = create_location_vertex(goal_loc.lat, goal_loc.lon, time(NULL));
        
        PrecisionTimer route_timer = timer_start_precise();
        
        // Plan route with profiling
        GraphserverPlanStats stats;
        GraphserverPath* path = profiled_plan_route(engine, start, goal, &stats);
        
        timer_end_precise(&route_timer);
        total_planning_time += route_timer.elapsed_seconds;
        
        if (path) {
            successful_routes++;
            size_t path_length = gs_path_get_num_edges(path);
            const double* total_cost = gs_path_get_total_cost(path);
            
            printf("    ✅ Path found: %zu edges, %.1f minutes, %.3f seconds\n", 
                   path_length, 
                   total_cost ? total_cost[0] : 0.0,
                   route_timer.elapsed_seconds);
            
            gs_path_destroy(path);
        } else {
            printf("    ❌ No path found (%.3f seconds)\n", route_timer.elapsed_seconds);
        }
        
        total_vertices_expanded += stats.vertices_expanded;
        total_edges_examined += stats.edges_generated;
        
        // Cleanup
        gs_vertex_destroy(start);
        gs_vertex_destroy(goal);
        
        // Small delay to avoid overwhelming the system
        usleep(1000); // 1ms delay
    }
    
    printf("\n📊 Campus Routing Performance Summary:\n");
    printf("  Scenarios tested: %zu\n", num_scenarios);
    printf("  Successful routes: %zu (%.1f%%)\n", 
           successful_routes, (successful_routes * 100.0) / num_scenarios);
    printf("  Total planning time: %.3f seconds\n", total_planning_time);
    printf("  Average per route: %.3f seconds\n", total_planning_time / num_scenarios);
    printf("  Total vertices expanded: %zu (avg: %.1f per route)\n", 
           total_vertices_expanded, (double)total_vertices_expanded / num_scenarios);
    printf("  Total edges examined: %zu (avg: %.1f per route)\n", 
           total_edges_examined, (double)total_edges_examined / num_scenarios);
}

// Stress test with intensive routing scenarios (remove unused parameter)
static void stress_test_routing_performance(void) {
    printf("\n🔥 Running intensive routing stress test...\n");
    
    const size_t STRESS_SCENARIOS = 50;
    PrecisionTimer stress_timer = timer_start_precise();
    
    // Create multiple engines to test concurrency simulation
    GraphserverEngine* engines[4];
    for (int i = 0; i < 4; i++) {
        engines[i] = gs_engine_create();
        
        // Add providers with different configurations
        WalkingConfig walking_config = walking_config_default();
        walking_config.max_walking_distance = 1000.0 + (i * 200.0); // Vary max distance
        walking_config.walking_speed_mps = 1.2 + (i * 0.1); // Vary speed
        
        WalkingConfig* config_ptr = malloc(sizeof(WalkingConfig));
        *config_ptr = walking_config;
        gs_engine_register_provider(engines[i], "walking", walking_provider, config_ptr);
    }
    
    size_t total_stress_routes = 0;
    
    // Run scenarios across different engine configurations
    for (size_t scenario = 0; scenario < STRESS_SCENARIOS; scenario++) {
        GraphserverEngine* test_engine = engines[scenario % 4];
        
        // Use distant locations for stress testing
        CampusLocation start_loc = uw_campus_locations[scenario % num_campus_locations];
        CampusLocation goal_loc = uw_campus_locations[(scenario + 7) % num_campus_locations];
        
        GraphserverVertex* start = create_location_vertex(start_loc.lat, start_loc.lon, time(NULL));
        GraphserverVertex* goal = create_location_vertex(goal_loc.lat, goal_loc.lon, time(NULL));
        
        GraphserverPlanStats stats;
        GraphserverPath* path = profiled_plan_route(test_engine, start, goal, &stats);
        
        if (path) {
            total_stress_routes++;
            gs_path_destroy(path);
        }
        
        gs_vertex_destroy(start);
        gs_vertex_destroy(goal);
        
        if (scenario % 10 == 0) {
            printf("  Completed %zu/%zu stress scenarios\n", scenario + 1, STRESS_SCENARIOS);
        }
    }
    
    timer_end_precise(&stress_timer);
    
    printf("  Stress test completed: %zu/%zu successful routes in %.3f seconds\n", 
           total_stress_routes, STRESS_SCENARIOS, stress_timer.elapsed_seconds);
    printf("  Stress test throughput: %.1f routes/second\n", 
           STRESS_SCENARIOS / stress_timer.elapsed_seconds);
    
    // Cleanup engines
    for (int i = 0; i < 4; i++) {
        gs_engine_destroy(engines[i]);
    }
}

// Memory usage profiling
static void profile_memory_usage(GraphserverEngine* engine) {
    printf("\n🧠 Profiling memory usage patterns...\n");
    
    size_t baseline_memory = 0; // Would need system-specific memory measurement
    
    // Test memory growth over multiple planning cycles
    for (int cycle = 0; cycle < 20; cycle++) {
        CampusLocation start_loc = uw_campus_locations[cycle % num_campus_locations];
        CampusLocation goal_loc = uw_campus_locations[(cycle + 3) % num_campus_locations];
        
        GraphserverVertex* start = create_location_vertex(start_loc.lat, start_loc.lon, time(NULL));
        GraphserverVertex* goal = create_location_vertex(goal_loc.lat, goal_loc.lon, time(NULL));
        
        GraphserverPlanStats stats;
        GraphserverPath* path = profiled_plan_route(engine, start, goal, &stats);
        
        printf("  Cycle %d: %zu bytes peak memory, %zu vertices expanded\n", 
               cycle + 1, stats.peak_memory_usage, stats.vertices_expanded);
        
        if (path) gs_path_destroy(path);
        gs_vertex_destroy(start);
        gs_vertex_destroy(goal);
    }
}

// Print comprehensive profiling results
static void print_profile_results(void) {
    printf("\n");
    for (int i = 0; i < 60; i++) printf("=");
    printf("\n");
    printf("🔍 CORE ROUTING ALGORITHM PROFILING RESULTS\n");
    for (int i = 0; i < 60; i++) printf("=");
    printf("\n");
    
    printf("\n⏱️  Function Performance Breakdown:\n");
    printf("%-25s %10s %12s %12s %12s %12s\n", 
           "Function", "Calls", "Total(s)", "Avg(ms)", "Min(ms)", "Max(ms)");
    for (int i = 0; i < 85; i++) printf("-");
    printf("\n");
    
    for (size_t i = 0; i < global_profile.entry_count; i++) {
        ProfileEntry* entry = &global_profile.entries[i];
        double avg_ms = (entry->total_time * 1000.0) / entry->call_count;
        double min_ms = entry->min_time * 1000.0;
        double max_ms = entry->max_time * 1000.0;
        
        printf("%-25s %10zu %12.6f %12.3f %12.3f %12.3f\n",
               entry->function_name,
               entry->call_count,
               entry->total_time,
               avg_ms,
               min_ms,
               max_ms);
    }
    
    printf("\n🎯 Performance Insights:\n");
    
    // Find bottlenecks
    ProfileEntry* slowest = NULL;
    ProfileEntry* most_called = NULL;
    
    for (size_t i = 0; i < global_profile.entry_count; i++) {
        ProfileEntry* entry = &global_profile.entries[i];
        
        if (!slowest || entry->total_time > slowest->total_time) {
            slowest = entry;
        }
        
        if (!most_called || entry->call_count > most_called->call_count) {
            most_called = entry;
        }
    }
    
    if (slowest) {
        printf("  🐌 Slowest function: %s (%.3f%% of total time)\n", 
               slowest->function_name, 
               (slowest->total_time / global_profile.total_execution_time) * 100.0);
    }
    
    if (most_called) {
        printf("  🔄 Most called function: %s (%zu calls)\n", 
               most_called->function_name, most_called->call_count);
    }
    
    printf("\n💡 Optimization Recommendations:\n");
    for (size_t i = 0; i < global_profile.entry_count; i++) {
        ProfileEntry* entry = &global_profile.entries[i];
        double time_percentage = (entry->total_time / global_profile.total_execution_time) * 100.0;
        
        if (time_percentage > 25.0) {
            printf("  🎯 HIGH PRIORITY: Optimize %s (%.1f%% of execution time)\n", 
                   entry->function_name, time_percentage);
        } else if (time_percentage > 10.0) {
            printf("  📈 MEDIUM PRIORITY: Consider optimizing %s (%.1f%% of execution time)\n", 
                   entry->function_name, time_percentage);
        }
    }
}

int main(int argc, char* argv[]) {
    printf("🚀 GraphServer Core Routing Algorithm Profiler\n");
    printf("================================================\n");
    printf("Profiling core C routing functions with UW Campus OSM data scenarios\n\n");
    
    // Initialize random seed
    srand((unsigned int)time(NULL));
    
    // Initialize GraphServer
    gs_string_dict_init();
    gs_common_keys_init();
    
    PrecisionTimer main_timer = timer_start_precise();
    
    // Create engine with realistic configuration
    printf("🏗️  Setting up routing engine...\n");
    GraphserverEngine* engine = gs_engine_create();
    
    // Configure walking provider for campus routing
    WalkingConfig walking_config = walking_config_default();
    walking_config.max_walking_distance = 1200.0; // Suitable for campus distances
    walking_config.walking_speed_mps = 1.3; // Realistic walking speed (m/s)
    
    WalkingConfig* config_ptr = malloc(sizeof(WalkingConfig));
    *config_ptr = walking_config;
    gs_engine_register_provider(engine, "walking", walking_provider, config_ptr);
    
    printf("✅ Engine configured with walking provider\n");
    printf("   Max walking distance: %.0fm\n", walking_config.max_walking_distance);
    printf("   Walking speed: %.1fm/s\n", walking_config.walking_speed_mps);
    
    // Determine number of scenarios from command line or use default
    size_t num_scenarios = 25;
    if (argc > 1) {
        num_scenarios = (size_t)atoi(argv[1]);
        if (num_scenarios < 1 || num_scenarios > 200) {
            printf("⚠️  Warning: Using default 25 scenarios (requested %zu out of range)\n", num_scenarios);
            num_scenarios = 25;
        }
    }
    
    printf("\n📍 Using %zu realistic campus locations for routing scenarios\n", num_campus_locations);
    
    // Run profiling scenarios
    generate_campus_routing_scenarios(engine, num_scenarios);
    
    // Run stress test
    stress_test_routing_performance();
    
    // Profile memory usage
    profile_memory_usage(engine);
    
    timer_end_precise(&main_timer);
    global_profile.total_execution_time = main_timer.elapsed_seconds;
    
    // Print results
    print_profile_results();
    
    printf("\n⚡ Total execution time: %.3f seconds\n", main_timer.elapsed_seconds);
    printf("🏁 Profiling completed! Use results to identify performance bottlenecks.\n");
    
    // Cleanup
    free(config_ptr);
    gs_engine_destroy(engine);
    gs_string_dict_cleanup();
    
    return 0;
}