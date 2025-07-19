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

**Current Status**: M1 Stage 1 complete - core data structures implemented and tested.

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
- `test_vertex` and `test_edge` - Unit test executables

## Testing

Run all tests:
```bash
make run_tests
```

Or run individual test suites:
```bash
./test_vertex   # 10 vertex functionality tests
./test_edge     # 8 edge functionality tests
```

Expected output: `All tests PASSED!` with 100% pass rate.

## Running

Currently implemented: Core data structures for vertices and edges with comprehensive APIs.

**Coming next**: Engine implementation with edge provider registration and simple Dijkstra planner.

Basic usage (when engine is complete):
```c
#include "graphserver.h"

// Create engine and register providers
GraphserverEngine* engine = gs_engine_create();
gs_engine_register_provider(engine, "my_provider", my_edge_generator, NULL);

// Plan a path
GraphserverVertex* start = gs_vertex_create();
// ... configure start vertex ...
GraphserverPath* path = gs_plan_simple(engine, start, goal_predicate, NULL);
```

See `DESIGN.md` for complete architecture documentation and `PLAN_M1.md` for current implementation status.