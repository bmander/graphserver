# Graphserver Examples

This directory contains example code demonstrating how to use the Graphserver Planning Engine for multi-modal journey planning.

## Overview

The Graphserver Planning Engine is a C library that provides efficient pathfinding across different transportation modes including walking, public transit, and road networks. These examples show how to:

- Set up and configure the planning engine
- Register custom edge providers for different transportation modes
- Plan multi-modal journeys with realistic constraints
- Handle complex routing scenarios with multiple objectives

## Quick Start

### Building the Examples

```bash
# Build everything (providers + simple_routing example)
make all

# Or build individual components
make providers      # Build the provider library
make simple_routing # Build the simple routing example
```

### Running the Simple Routing Example

```bash
# Run with proper library path
LD_LIBRARY_PATH=../core/build:$LD_LIBRARY_PATH ./simple_routing

# Or use the convenience target
LD_LIBRARY_PATH=../core/build:$LD_LIBRARY_PATH make run
```

## Example Breakdown

### simple_routing.c

The main example demonstrates a complete multi-modal journey planning scenario:

**1. Engine Setup**
```c
// Create planning engine with custom configuration
GraphserverConfig config = {
    .distance_objectives = 2,     // Time and cost optimization
    .max_search_time_ms = 30000,  // 30 second timeout
    .memory_limit_mb = 256        // 256MB memory limit
};
GraphserverEngine* engine = gs_engine_create(&config);
```

**2. Provider Registration**
```c
// Register transportation mode providers
gs_engine_register_provider(engine, "walking", walking_provider, walk_network);
gs_engine_register_provider(engine, "transit", transit_provider, transit_network);
gs_engine_register_provider(engine, "road", road_network_provider, road_network);
```

**3. Journey Planning**
```c
// Plan route from Financial District to Brooklyn Bridge
GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, current_time);
GraphserverVertex* goal = create_location_vertex(40.7061, -73.9969, target_time);

GraphserverPath* path = gs_plan_simple(engine, start, goal);
```

**Key Features Demonstrated:**
- **Multi-objective optimization**: Minimizes both travel time and cost
- **Mode switching**: Seamlessly transitions between walking, transit, and driving
- **Real-time constraints**: Considers schedules, traffic, and time-dependent factors
- **Error handling**: Graceful handling of unreachable destinations
- **Memory management**: Proper cleanup of all allocated resources

## Transportation Providers

### Walking Provider (`providers/walking_provider.c`)

Simulates pedestrian movement with realistic constraints:

- **Speed modeling**: 1.3 m/s average walking speed
- **Distance limits**: Maximum 2km walks, 800m to transit stops
- **Terrain awareness**: Different speeds for various surface types
- **Safety considerations**: Avoids highways and unsafe areas
- **POI connectivity**: Links points of interest with walking paths

### Transit Provider (`providers/transit_provider.c`)

Models public transportation with schedule simulation:

- **Multi-modal transit**: Subway, bus, and light rail systems
- **Schedule adherence**: Real-time frequency and wait time calculations
- **Transfer handling**: Automatic transfer detection with penalty costs
- **Peak hour modeling**: Different frequencies for rush hour vs off-peak
- **Fare integration**: Includes transit costs in multi-objective planning

**Example Transit Routes:**
- Red Line Subway (3-6 min frequency, $2.75)
- Blue Line Subway (4-8 min frequency, $2.75)  
- M15/M14 Bus Lines (8-20 min frequency, $2.90)

### Road Network Provider (`providers/road_network_provider.c`)

Simulates vehicle routing with traffic modeling:

- **Vehicle types**: Car, bicycle, motorcycle with different constraints
- **Road classification**: Highway, arterial, local, residential streets
- **Traffic simulation**: Dynamic congestion based on time of day
- **Speed limits**: Enforced per road type and vehicle capability
- **Route restrictions**: One-way streets, vehicle-specific limitations

**Traffic Modeling Features:**
- Rush hour congestion (7-9 AM, 5-7 PM)
- Vehicle-specific speed adjustments
- Traffic avoidance preferences
- Real-time speed calculations

## Advanced Usage

### Custom Provider Development

To create your own transportation provider:

```c
int my_custom_provider(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data) {
    
    // Extract location and time from current vertex
    double lat, lon;
    time_t current_time;
    extract_location_from_vertex(current_vertex, &lat, &lon, &current_time);
    
    // Generate edges to reachable destinations
    // ... your custom logic here ...
    
    return 0; // Success
}
```

### Multi-Objective Planning

The examples demonstrate planning with multiple objectives:

- **Objective 0**: Travel time (minutes)
- **Objective 1**: Financial cost (dollars)

The Dijkstra planner finds Pareto-optimal solutions balancing both objectives.

### Memory Management

All examples follow proper memory management:

```c
// Always clean up resources
gs_path_destroy(path);
gs_vertex_destroy(start);
gs_vertex_destroy(goal);
gs_engine_destroy(engine);
```

## Testing and Validation

### Memory Safety

Run with Valgrind to check for memory leaks:

```bash
make memcheck
```

### Performance Benchmarking

The integration tests include performance benchmarks:

```bash
cd ../core/build
./test_performance
```

## Integration with Core Library

These examples use the core Graphserver library located in `../core/`. Key integration points:

- **Headers**: `#include "../core/include/graphserver.h"`
- **Linking**: `-lgraphserver_core -lm`
- **Library path**: `../core/build/libgraphserver_core.a`

## Example Output

```
Graphserver Simple Routing Example
==================================

1. Creating planning engine...
2. Registering providers...
   ✓ Walking provider registered
   ✓ Transit provider registered  
   ✓ Road network provider registered
   Total providers registered: 3

3. Planning journey...
   From: Financial District (40.7074, -74.0113)
   To: Brooklyn Bridge area (40.7061, -73.9969)

4. Planning results:
   Planning time: 1.107 seconds
   Vertices expanded: 867
   Edges examined: 30852
   Memory used: 177992 bytes

5. Route found with 3 segments:
   Walk to Wall St Station (2.3 min, $0.00)
   Red Line to Brooklyn Bridge (4.5 min, $2.75)
   Walk to destination (1.8 min, $0.00)
   
   Total: 8.6 minutes, $2.75
```

## Further Reading

- **Core Documentation**: `../core/README.md`
- **Integration Tests**: `../core/tests/test_integration.c`
- **Performance Analysis**: `../core/tests/test_performance.c`
- **API Reference**: `../core/include/graphserver.h`

## Troubleshooting

**Build Issues:**
- Ensure core library is built: `cd ../core/build && make`
- Check library paths in Makefile match your system

**Runtime Issues:**
- Set `LD_LIBRARY_PATH=../core/build:$LD_LIBRARY_PATH`
- Verify all required providers are registered

**Memory Issues:**
- Use `make memcheck` to identify leaks
- Ensure proper cleanup of all allocated resources

For more advanced usage and integration scenarios, see the comprehensive integration tests in the core library.