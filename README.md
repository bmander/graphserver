# Graphserver Planning Engine

Graphserver is a general-purpose, high-performance planning library designed for flexibility and embeddability. It finds optimal paths through abstract state spaces using a pluggable architecture where **Vertices** represent states and **Edges** represent transitions between states.

The core innovation is dynamic, on-the-fly graph expansion through **Edge Providers** - pluggable modules that generate valid transitions from any given state. This makes Graphserver applicable to diverse domains from multi-modal travel routing to game AI and compiler optimization.

## Implementation

The system is built around a C core library for maximum performance and portability, with planned language bindings for Python, Kotlin, and Swift. Key components include:

- **GraphserverVertex**: State representation using key-value pairs with efficient canonical form
- **GraphserverEdge**: Multi-objective transitions with metadata support  
- **GraphserverEngine**: Coordinates edge providers and planning algorithms
- **Edge Providers**: Function-pointer based plugins that define domain-specific transition rules
- **Planners**: Algorithms like Dijkstra and A* that search for optimal paths

**Current Status**: M1 Stage 4 complete - core library with full integration testing and end-to-end scenarios.

## Building

Requirements:
- CMake 3.12 or higher
- C99-compatible compiler (GCC, Clang, MSVC)

```bash
cd core
mkdir build && cd build
cmake ..
make
```

This generates:
- `libgraphserver_core.a` - Static library
- `libgraphserver_core.so` - Shared library  
- Test executables: `test_vertex`, `test_edge`, `test_memory`, `test_engine`, `test_planner`, `test_integration`
- Performance benchmarks: `test_performance`
- Example applications: `simple_routing` (in examples directory)

## Testing

### Unit Tests
Run all core unit tests:
```bash
make run_tests
```

Or run individual test suites:
```bash
./test_vertex   # Vertex functionality tests
./test_edge     # Edge functionality tests  
./test_memory   # Memory management tests
./test_engine   # Engine and provider tests
./test_planner  # Dijkstra planner tests
```

### Integration Tests
Run comprehensive integration tests with real-world scenarios:
```bash
./test_integration
```

This test suite includes:
- Utility function validation (distance calculation, location handling)
- Walking provider with realistic constraints and accessibility
- Transit provider with NYC-style subway/bus simulation
- Road network provider with traffic modeling and vehicle routing
- Multi-modal journey planning end-to-end scenarios
- Large-scale network performance testing
- Edge case handling and error validation
- Memory management across multiple planning cycles

Expected output: `8/8 tests passed` with detailed scenario results.

### Performance Benchmarks
Run performance analysis (not included in automated testing):
```bash
./test_performance
```

Measures planning time, memory usage, and scalability across different network sizes.

### Memory Leak Detection
Run Valgrind analysis to detect memory leaks:
```bash
# Install Valgrind if needed
sudo apt-get install valgrind

# Run automated memory analysis
../scripts/valgrind_test.sh
```

This script runs all test executables under Valgrind with comprehensive memory checking options, generating detailed reports for each test. Expected output: `All tests passed Valgrind analysis!`

### Example Applications
Test complete workflow with realistic usage:
```bash
cd ../examples
./simple_routing
```

Demonstrates engine setup, provider registration, multi-modal journey planning from Financial District to Brooklyn Bridge area with detailed route analysis.

## Usage

The library is fully functional with complete engine implementation, edge provider registration, and Dijkstra planning algorithm.

### Basic Planning Workflow
```c
#include "graphserver.h"
#include "include/example_providers.h"

// Initialize library
gs_initialize();

// Create engine and register providers
GraphserverEngine* engine = gs_engine_create();

// Walking provider for pedestrian routing
WalkingConfig walking_config = walking_config_default();
gs_engine_register_provider(engine, "walking", walking_provider, &walking_config);

// Transit provider for subway/bus routing
TransitNetwork* transit = transit_network_create_example();
gs_engine_register_provider(engine, "transit", transit_provider, transit);

// Plan a multi-modal journey
GraphserverVertex* start = create_location_vertex(40.7074, -74.0113, time(NULL));
LocationGoal goal = {40.7061, -73.9969, 200.0}; // Brooklyn Bridge area

GraphserverPlanStats stats;
GraphserverPath* path = gs_plan_simple(engine, start, location_goal_predicate, &goal, &stats);

if (path) {
    size_t num_edges = gs_path_get_num_edges(path);
    const double* total_cost = gs_path_get_total_cost(path);
    printf("Found path with %zu edges, %.1f minutes\n", num_edges, total_cost[0]);
    gs_path_destroy(path);
}

// Cleanup
gs_vertex_destroy(start);
transit_network_destroy(transit);
gs_engine_destroy(engine);
gs_cleanup();
```

### Available Providers
- **Walking Provider**: Pedestrian routing with configurable speed, distance limits, and accessibility options
- **Transit Provider**: Public transit with schedule simulation, transfers, and multi-objective costs (time + fare)
- **Road Network Provider**: Vehicle routing with traffic modeling and vehicle-specific constraints (car, bicycle, motorcycle)

Run `./simple_routing` in the examples directory for a complete working demonstration.

See `DESIGN.md` for complete architecture documentation and `PLAN_M1.md` for current implementation status.