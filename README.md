# Graphserver Planning Engine

Graphserver is a general-purpose, high-performance planning library designed for flexibility and embeddability. It finds optimal paths through abstract state spaces using a pluggable architecture where **Vertices** represent states and **Edges** represent transitions between states.

The core innovation is dynamic, on-the-fly graph expansion through **Edge Providers** - pluggable modules that generate valid transitions from any given state. This makes Graphserver applicable to diverse domains from multi-modal travel routing to game AI and compiler optimization.

## Implementation

The system is built around a C core library for maximum performance and portability, with complete Python bindings and planned language bindings for Kotlin and Swift. Key components include:

- **GraphserverVertex**: State representation using key-value pairs with efficient canonical form
- **GraphserverEdge**: Multi-objective transitions with metadata support  
- **GraphserverEngine**: Coordinates edge providers and planning algorithms
- **Edge Providers**: Function-pointer based plugins that define domain-specific transition rules
- **Planners**: Algorithms like Dijkstra and A* that search for optimal paths

**Current Status**: M1 Stage 4 complete - core library with full integration testing. M2 Phase 2 complete - Python bindings with end-to-end provider integration working.

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
../../scripts/valgrind_test.sh
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

## Python Library

**Status**: Phase 2 Complete ✅ - Full Python provider integration with end-to-end pathfinding working!

The Python library provides a high-level interface to the Graphserver planning engine with complete integration for writing custom edge providers in Python.

### Installation

```bash
cd python
pip install -e .
```

Requirements:
- Python 3.8+
- C99-compatible compiler for building the extension
- Core library dependencies (built automatically)

### Building from Source

The Python library includes a C extension that automatically builds the core library:

```bash
cd python
python -m pip install build
python -m build
pip install dist/graphserver-*.whl
```

### Testing

Run the complete test suite:
```bash
cd python
python -m pytest tests/ -v
```

Run specific test categories:
```bash
# C extension functionality
python -m pytest tests/test_extension.py -v

# Python API integration  
python -m pytest tests/test_core.py -v

# Type checking validation
python -m pytest tests/test_types.py -v
```

### Example Usage

```python
from graphserver import Engine

# Create planning engine
engine = Engine()

# Define a custom edge provider in Python
def grid_world_provider(vertex):
    """2D grid world with simple movement rules."""
    x, y = vertex.get('x', 0), vertex.get('y', 0)
    edges = []
    
    # Can move right
    if x < 10:
        edges.append({
            'target': {'x': x + 1, 'y': y},
            'cost': 1.0,
            'metadata': {'direction': 'east'}
        })
    
    # Can move up
    if y < 10:
        edges.append({
            'target': {'x': x, 'y': y + 1},
            'cost': 1.0,
            'metadata': {'direction': 'north'}
        })
    
    return edges

# Register the provider
engine.register_provider("grid", grid_world_provider)

# Plan a path
result = engine.plan(
    start={'x': 0, 'y': 0},
    goal={'x': 3, 'y': 2}
)

print(f"Found path with {len(result)} steps")
print(f"Total cost: {sum(edge['cost'] for edge in result)}")
```

### Advanced Features

**Complex Data Types**: Full support for Python data types in vertices:
```python
# Rich vertex data with multiple types
start_vertex = {
    'x': 0, 'y': 0,           # Coordinates (int)
    'elevation': 125.5,        # Elevation (float)  
    'name': 'start_point',     # Labels (string)
    'accessible': True,        # Flags (bool)
    'equipment': [1, 2, 3]     # Lists (converted to string representation)
}
```

**Multi-Objective Costs**: Support for multiple cost dimensions:
```python
def transport_provider(vertex):
    return [{
        'target': {'station': 'downtown'},
        'cost': [15.0, 5.50],  # [time_minutes, fare_dollars]
        'metadata': {'mode': 'subway', 'line': 'red'}
    }]
```

**Provider Metadata**: Rich edge metadata for analysis:
```python
def road_provider(vertex):
    return [{
        'target': {'intersection': 'main_st'},
        'cost': 2.5,
        'metadata': {
            'road_type': 'residential',
            'speed_limit': 25,
            'traffic_level': 'light'
        }
    }]
```

### Demo Application

Run the comprehensive demo to see the full system in action:
```bash
python phase2_demo.py
```

This demonstrates:
- Engine creation and provider registration
- Complex data type conversion
- Multi-step pathfinding with optimal results
- Provider functions called multiple times during search
- Cost calculation and path analysis

Expected output: Successful pathfinding from (0,0) to (2,1) with optimal 3-step path and total cost 3.0.

### Known Limitations

- Target vertex data in path results is temporarily simplified due to memory management complexity
- All core functionality (planning, providers, costs) works perfectly
- Can be enhanced in future iterations if full vertex data access is needed

### Type Safety

The library includes full type hints and supports static analysis:
```bash
cd python  
mypy src/graphserver --strict
```