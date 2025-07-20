#include "../include/gs_engine.h"
#include "../include/gs_memory.h"
#include "../include/gs_vertex.h"
#include "../include/gs_edge.h"
#include "../include/gs_planner_internal.h"
#include "../include/gs_cache.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <assert.h>

// Provider registration entry
typedef struct {
    char* name;
    gs_generate_edges_fn generator;
    void* user_data;
    bool is_enabled;
} Provider;

// Engine structure
struct GraphserverEngine {
    Provider* providers;
    size_t provider_count;
    size_t provider_capacity;
    
    GraphserverEngineConfig config;
    
    // Edge cache for vertex expansion acceleration
    EdgeCache* edge_cache;
    
    // Statistics
    GraphserverPlanStats last_plan_stats;
    
    // Future: thread pool for concurrent expansion
    // ThreadPool* thread_pool;
};

// Path structure (basic implementation for now)
struct GraphserverPath {
    GraphserverEdge** edges;
    size_t num_edges;
    double* total_cost;
    size_t cost_vector_size;
};

// Path list structure
struct GraphserverPathList {
    GraphserverPath** paths;
    size_t num_paths;
    size_t capacity;
};

// Helper function to duplicate string
static char* duplicate_string(const char* str) {
    if (!str) return NULL;
    
    size_t len = strlen(str);
    char* copy = malloc(len + 1);
    if (!copy) return NULL;
    
    memcpy(copy, str, len + 1);
    return copy;
}

// Helper function to find provider by name
static Provider* find_provider(GraphserverEngine* engine, const char* name) {
    if (!engine || !name) return NULL;
    
    for (size_t i = 0; i < engine->provider_count; i++) {
        if (strcmp(engine->providers[i].name, name) == 0) {
            return &engine->providers[i];
        }
    }
    
    return NULL;
}

// Helper function to ensure provider capacity
static GraphserverResult ensure_provider_capacity(GraphserverEngine* engine, size_t min_capacity) {
    if (engine->provider_capacity >= min_capacity) return GS_SUCCESS;
    
    size_t new_capacity = engine->provider_capacity == 0 ? 4 : engine->provider_capacity * 2;
    while (new_capacity < min_capacity) {
        new_capacity *= 2;
    }
    
    Provider* new_providers = realloc(engine->providers, sizeof(Provider) * new_capacity);
    if (!new_providers) return GS_ERROR_OUT_OF_MEMORY;
    
    engine->providers = new_providers;
    engine->provider_capacity = new_capacity;
    
    return GS_SUCCESS;
}

// Get default configuration
GraphserverEngineConfig gs_engine_get_default_config(void) {
    GraphserverEngineConfig config = {0};
    config.default_arena_size = GS_DEFAULT_ARENA_SIZE;
    config.max_memory_limit = 0; // No limit
    config.default_timeout_seconds = 30.0; // 30 seconds
    config.enable_concurrent_expansion = false; // Not implemented yet
    config.max_worker_threads = 4;
    config.enable_edge_caching = false; // Disabled by default
    
    return config;
}

// Engine lifecycle
GraphserverEngine* gs_engine_create(void) {
    GraphserverEngineConfig config = gs_engine_get_default_config();
    return gs_engine_create_with_config(&config);
}

GraphserverEngine* gs_engine_create_with_config(const GraphserverEngineConfig* config) {
    if (!config) return NULL;
    
    GraphserverEngine* engine = malloc(sizeof(GraphserverEngine));
    if (!engine) return NULL;
    
    engine->providers = NULL;
    engine->provider_count = 0;
    engine->provider_capacity = 0;
    engine->config = *config;
    
    // Initialize edge cache if enabled
    if (config->enable_edge_caching) {
        engine->edge_cache = edge_cache_create();
        if (!engine->edge_cache) {
            free(engine);
            return NULL;
        }
    } else {
        engine->edge_cache = NULL;
    }
    
    // Initialize stats
    memset(&engine->last_plan_stats, 0, sizeof(GraphserverPlanStats));
    
    return engine;
}

void gs_engine_destroy(GraphserverEngine* engine) {
    if (!engine) return;
    
    // Free provider names
    for (size_t i = 0; i < engine->provider_count; i++) {
        free(engine->providers[i].name);
    }
    
    // Destroy edge cache
    if (engine->edge_cache) {
        edge_cache_destroy(engine->edge_cache);
    }
    
    free(engine->providers);
    free(engine);
}

// Provider management
GraphserverResult gs_engine_register_provider(
    GraphserverEngine* engine,
    const char* provider_name,
    gs_generate_edges_fn generator_func,
    void* user_data) {
    
    if (!engine || !provider_name || !generator_func) {
        return GS_ERROR_NULL_POINTER;
    }
    
    // Check if provider already exists
    if (find_provider(engine, provider_name) != NULL) {
        return GS_ERROR_INVALID_ARGUMENT; // Provider already exists
    }
    
    // Ensure capacity
    GraphserverResult result = ensure_provider_capacity(engine, engine->provider_count + 1);
    if (result != GS_SUCCESS) return result;
    
    // Add new provider
    Provider* provider = &engine->providers[engine->provider_count];
    provider->name = duplicate_string(provider_name);
    if (!provider->name) return GS_ERROR_OUT_OF_MEMORY;
    
    provider->generator = generator_func;
    provider->user_data = user_data;
    provider->is_enabled = true;
    
    engine->provider_count++;
    
    return GS_SUCCESS;
}

GraphserverResult gs_engine_unregister_provider(
    GraphserverEngine* engine,
    const char* provider_name) {
    
    if (!engine || !provider_name) return GS_ERROR_NULL_POINTER;
    
    // Find provider
    for (size_t i = 0; i < engine->provider_count; i++) {
        if (strcmp(engine->providers[i].name, provider_name) == 0) {
            // Free the name
            free(engine->providers[i].name);
            
            // Shift remaining providers down
            for (size_t j = i; j < engine->provider_count - 1; j++) {
                engine->providers[j] = engine->providers[j + 1];
            }
            
            engine->provider_count--;
            return GS_SUCCESS;
        }
    }
    
    return GS_ERROR_KEY_NOT_FOUND;
}

GraphserverResult gs_engine_set_provider_enabled(
    GraphserverEngine* engine,
    const char* provider_name,
    bool enabled) {
    
    if (!engine || !provider_name) return GS_ERROR_NULL_POINTER;
    
    Provider* provider = find_provider(engine, provider_name);
    if (!provider) return GS_ERROR_KEY_NOT_FOUND;
    
    provider->is_enabled = enabled;
    return GS_SUCCESS;
}

GraphserverResult gs_engine_list_providers(
    const GraphserverEngine* engine,
    GraphserverProviderInfo** out_provider_info,
    size_t* out_count) {
    
    if (!engine || !out_provider_info || !out_count) {
        return GS_ERROR_NULL_POINTER;
    }
    
    if (engine->provider_count == 0) {
        *out_provider_info = NULL;
        *out_count = 0;
        return GS_SUCCESS;
    }
    
    GraphserverProviderInfo* info = malloc(sizeof(GraphserverProviderInfo) * engine->provider_count);
    if (!info) return GS_ERROR_OUT_OF_MEMORY;
    
    for (size_t i = 0; i < engine->provider_count; i++) {
        info[i].name = engine->providers[i].name;
        info[i].generator = engine->providers[i].generator;
        info[i].user_data = engine->providers[i].user_data;
        info[i].is_enabled = engine->providers[i].is_enabled;
    }
    
    *out_provider_info = info;
    *out_count = engine->provider_count;
    
    return GS_SUCCESS;
}

size_t gs_engine_get_provider_count(const GraphserverEngine* engine) {
    return engine ? engine->provider_count : 0;
}

bool gs_engine_has_provider(const GraphserverEngine* engine, const char* provider_name) {
    return find_provider((GraphserverEngine*)engine, provider_name) != NULL;
}

// Graph expansion
GraphserverResult gs_engine_expand_vertex(
    GraphserverEngine* engine,
    const GraphserverVertex* vertex,
    GraphserverEdgeList* out_edges) {
    
    if (!engine || !vertex || !out_edges) return GS_ERROR_NULL_POINTER;
    
    // Clear the output edge list
    gs_edge_list_clear(out_edges);
    
    // Check cache first if caching is enabled
    if (engine->config.enable_edge_caching && engine->edge_cache) {
        GraphserverEdgeList* cached_edges = NULL;
        GraphserverResult cache_result = edge_cache_get(engine->edge_cache, vertex, &cached_edges);
        
        if (cache_result == GS_SUCCESS && cached_edges) {
            // Cache hit! Clone all cached edges for output
            size_t cached_edge_count = gs_edge_list_get_count(cached_edges);
            for (size_t i = 0; i < cached_edge_count; i++) {
                GraphserverEdge* edge;
                GraphserverResult get_result = gs_edge_list_get_edge(cached_edges, i, &edge);
                if (get_result == GS_SUCCESS && edge) {
                    // Clone the edge so output list owns its own copy
                    GraphserverEdge* edge_clone = gs_edge_clone(edge);
                    if (edge_clone) {
                        gs_edge_list_add_edge(out_edges, edge_clone);
                    }
                }
            }
            
            // Update statistics
            engine->last_plan_stats.cache_hits++;
            engine->last_plan_stats.edges_generated += cached_edge_count;
            
            // Clean up cached edges and return early
            gs_edge_list_destroy(cached_edges);
            return GS_SUCCESS;
        } else if (cache_result == GS_ERROR_KEY_NOT_FOUND) {
            // Cache miss - proceed with provider calls
            engine->last_plan_stats.cache_misses++;
        }
        // For other cache errors, just proceed with provider calls
    }
    
    GraphserverResult overall_result = GS_SUCCESS;
    
    // Call each enabled provider
    for (size_t i = 0; i < engine->provider_count; i++) {
        Provider* provider = &engine->providers[i];
        
        if (!provider->is_enabled) continue;
        
        // Create a temporary edge list for this provider
        GraphserverEdgeList* provider_edges = gs_edge_list_create();
        if (!provider_edges) {
            overall_result = GS_ERROR_OUT_OF_MEMORY;
            break;
        }
        
        // Call the provider
        int provider_result = provider->generator(vertex, provider_edges, provider->user_data);
        
        if (provider_result == 0) { // Success
            // Add all edges from this provider to the output
            size_t provider_edge_count = gs_edge_list_get_count(provider_edges);
            for (size_t j = 0; j < provider_edge_count; j++) {
                GraphserverEdge* edge;
                GraphserverResult get_result = gs_edge_list_get_edge(provider_edges, j, &edge);
                if (get_result == GS_SUCCESS && edge) {
                    gs_edge_list_add_edge(out_edges, edge);
                }
            }
            
            // Update statistics
            engine->last_plan_stats.providers_called++;
            engine->last_plan_stats.edges_generated += provider_edge_count;
        }
        
        gs_edge_list_destroy(provider_edges);
    }
    
    // Store results in cache if caching is enabled and providers succeeded
    if (engine->config.enable_edge_caching && engine->edge_cache && overall_result == GS_SUCCESS) {
        (void)edge_cache_put(engine->edge_cache, vertex, out_edges);
        // Update cache_puts statistics regardless of success/failure
        engine->last_plan_stats.cache_puts++;
        // Note: We don't fail the overall operation if cache storage fails
    }
    
    return overall_result;
}

// Configuration
GraphserverResult gs_engine_set_config(
    GraphserverEngine* engine,
    const GraphserverEngineConfig* config) {
    
    if (!engine || !config) return GS_ERROR_NULL_POINTER;
    
    engine->config = *config;
    return GS_SUCCESS;
}

GraphserverResult gs_engine_get_config(
    const GraphserverEngine* engine,
    GraphserverEngineConfig* out_config) {
    
    if (!engine || !out_config) return GS_ERROR_NULL_POINTER;
    
    *out_config = engine->config;
    return GS_SUCCESS;
}

GraphserverResult gs_engine_get_stats(
    const GraphserverEngine* engine,
    GraphserverPlanStats* out_stats) {
    
    if (!engine || !out_stats) return GS_ERROR_NULL_POINTER;
    
    *out_stats = engine->last_plan_stats;
    return GS_SUCCESS;
}

// Basic path management (will be expanded when planners are implemented)
GraphserverPath* gs_path_create(size_t cost_vector_size) {
    GraphserverPath* path = malloc(sizeof(GraphserverPath));
    if (!path) return NULL;
    
    path->edges = NULL;
    path->num_edges = 0;
    path->cost_vector_size = cost_vector_size;
    
    if (cost_vector_size > 0) {
        path->total_cost = calloc(cost_vector_size, sizeof(double));
        if (!path->total_cost) {
            free(path);
            return NULL;
        }
    } else {
        path->total_cost = NULL;
    }
    
    return path;
}

void gs_path_destroy(GraphserverPath* path) {
    if (!path) return;
    
    // Destroy individual edges
    if (path->edges) {
        for (size_t i = 0; i < path->num_edges; i++) {
            if (path->edges[i]) {
                gs_edge_destroy(path->edges[i]);
            }
        }
        free(path->edges);
    }
    
    free(path->total_cost);
    free(path);
}

size_t gs_path_get_num_edges(const GraphserverPath* path) {
    return path ? path->num_edges : 0;
}

const GraphserverEdge* gs_path_get_edge(const GraphserverPath* path, size_t index) {
    if (!path || index >= path->num_edges) return NULL;
    return path->edges[index];
}

const double* gs_path_get_total_cost(const GraphserverPath* path) {
    return path ? path->total_cost : NULL;
}

size_t gs_path_get_cost_vector_size(const GraphserverPath* path) {
    return path ? path->cost_vector_size : 0;
}

char* gs_path_to_string(const GraphserverPath* path) {
    if (!path) return duplicate_string("null");
    
    // Simple implementation for now
    char* buffer = malloc(256);
    if (!buffer) return NULL;
    
    snprintf(buffer, 256, "Path{edges: %zu, cost_size: %zu}", 
             path->num_edges, path->cost_vector_size);
    
    return buffer;
}

// Path list management
GraphserverPathList* gs_pathlist_create(void) {
    GraphserverPathList* list = malloc(sizeof(GraphserverPathList));
    if (!list) return NULL;
    
    list->paths = NULL;
    list->num_paths = 0;
    list->capacity = 0;
    
    return list;
}

void gs_pathlist_destroy(GraphserverPathList* path_list) {
    if (!path_list) return;
    
    for (size_t i = 0; i < path_list->num_paths; i++) {
        gs_path_destroy(path_list->paths[i]);
    }
    
    free(path_list->paths);
    free(path_list);
}

size_t gs_pathlist_get_count(const GraphserverPathList* path_list) {
    return path_list ? path_list->num_paths : 0;
}

GraphserverPath* gs_pathlist_get_path(const GraphserverPathList* path_list, size_t index) {
    if (!path_list || index >= path_list->num_paths) return NULL;
    return path_list->paths[index];
}

// Planning function implementations using Dijkstra algorithm

GraphserverPathList* gs_plan(
    GraphserverEngine* engine,
    const GraphserverPlanOptions* options,
    GraphserverPlanStats* out_stats) {
    
    if (!engine || !options) return NULL;
    
    // Clear previous stats
    memset(&engine->last_plan_stats, 0, sizeof(GraphserverPlanStats));
    
    // Create arena for planning operations
    GraphserverArena* arena = gs_arena_create(engine->config.default_arena_size);
    if (!arena) return NULL;
    
    GraphserverPath* path = NULL;
    GraphserverPlanStats stats = {0};
    
    // Use Dijkstra planner (currently only single-objective supported)
    GraphserverResult result = gs_plan_dijkstra(
        engine,
        options->start_vertex,
        options->is_goal_fn,
        options->is_goal_user_data,
        options->timeout_seconds,
        arena,
        &path,
        &stats
    );
    
    // Create path list result
    GraphserverPathList* path_list = gs_pathlist_create();
    if (!path_list) {
        if (path) gs_path_destroy(path);
        gs_arena_destroy(arena);
        return NULL;
    }
    
    // Add path to list if found
    if (result == GS_SUCCESS && path) {
        // Expand path list capacity if needed
        if (path_list->capacity == 0) {
            path_list->capacity = 1;
            path_list->paths = malloc(sizeof(GraphserverPath*) * path_list->capacity);
            if (!path_list->paths) {
                gs_path_destroy(path);
                gs_pathlist_destroy(path_list);
                gs_arena_destroy(arena);
                return NULL;
            }
        }
        
        path_list->paths[0] = path;
        path_list->num_paths = 1;
    }
    
    // Store stats in engine
    engine->last_plan_stats = stats;
    
    if (out_stats) {
        *out_stats = stats;
    }
    
    gs_arena_destroy(arena);
    return path_list;
}

GraphserverPath* gs_plan_simple(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    void* goal_user_data,
    GraphserverPlanStats* out_stats) {
    
    if (!engine || !start_vertex || !is_goal) return NULL;
    
    // Create arena for planning operations
    GraphserverArena* arena = gs_arena_create(engine->config.default_arena_size);
    if (!arena) return NULL;
    
    GraphserverPath* path = NULL;
    GraphserverPlanStats stats = {0};
    
    // Use Dijkstra planner directly
    GraphserverResult result = gs_plan_dijkstra(
        engine,
        start_vertex,
        is_goal,
        goal_user_data,
        engine->config.default_timeout_seconds,
        arena,
        &path,
        &stats
    );
    
    // Store stats in engine
    engine->last_plan_stats = stats;
    
    if (out_stats) {
        *out_stats = stats;
    }
    
    gs_arena_destroy(arena);
    
    if (result == GS_SUCCESS) {
        return path;
    } else {
        if (path) gs_path_destroy(path);
        return NULL;
    }
}

// Utility functions
const char* gs_get_error_message(GraphserverResult result) {
    switch (result) {
        case GS_SUCCESS: return "Success";
        case GS_ERROR_NULL_POINTER: return "Null pointer";
        case GS_ERROR_INVALID_ARGUMENT: return "Invalid argument";
        case GS_ERROR_OUT_OF_MEMORY: return "Out of memory";
        case GS_ERROR_KEY_NOT_FOUND: return "Key not found";
        case GS_ERROR_TYPE_MISMATCH: return "Type mismatch";
        case GS_ERROR_TIMEOUT: return "Timeout";
        case GS_ERROR_NO_PATH_FOUND: return "No path found";
        default: return "Unknown error";
    }
}

const char* gs_get_version(void) {
    return "2.0.0";
}

GraphserverResult gs_initialize(void) {
    // Currently no global initialization needed
    return GS_SUCCESS;
}

void gs_cleanup(void) {
    // Currently no global cleanup needed
}