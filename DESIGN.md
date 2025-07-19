
## **Technical Design Document: Graphserver Planning Engine**

### 1. Overview & Vision

The Graphserver Planning Engine is a general-purpose, high-performance planning library designed for flexibility and embeddability. Its primary goal is to find optimal or near-optimal paths through abstract state spaces, making it applicable to a wide range of domains from multi-modal travel routing to compiler optimization and game AI.

The core principle of Graphserver is a **pluggable architecture built on graph theory**. The system models problems as a graph where a **Vertex** represents a state in the system and an **Edge** represents a valid transition between states. The key innovation is that the graph is not pre-computed but rather **expanded dynamically on-the-fly**. This is achieved by **Edge Providers**—pluggable modules that know how to generate valid next states (Edges) from a given current state (Vertex).

This design prioritizes flexibility and performance on resource-constrained environments (edge computing) over massive, pre-processed graph storage. The core engine is written in C for maximum performance and portability, with first-class language bindings for Kotlin, Swift, and Python to enable rapid development on mobile, desktop, and server platforms.

### 2. Goals and Non-Goals

#### 2.1. Goals

*   **Generality:** The core engine must be domain-agnostic, relying solely on the abstract concepts of Vertices and Edges.
*   **Flexibility:** The pluggable Edge Provider architecture must allow developers to easily define new problem domains and transition rules.
*   **Performance:** The C core must be highly optimized for low-latency, on-the-fly graph expansion and pathfinding.
*   **Advanced Planning Support:** Natively support multi-objective planning (e.g., balancing time and cost), stochastic outcomes (e.g., variable travel times), and the discovery of alternative paths.
*   **Embeddability & Portability:** The C core with a stable ABI allows for easy integration into various platforms (iOS, Android) and languages (Python, etc.).

#### 2.2. Non-Goals

*   **Large-Scale Graph Pre-computation:** This engine is not designed to compete with systems like Google Maps that pre-process and store petabytes of road network data for instantaneous lookups. Graph expansion is dynamic.
*   **A Complete Solution Out-of-the-Box:** Graphserver provides the *engine* and a framework. It will ship with examples, but domain-specific data and rules (e.g., a complete, real-time bus schedule) must be provided by the user via custom Edge Providers.
*   **User Interface (UI):** Graphserver is a library/engine and is not concerned with any form of graphical presentation.

### 3. Core Concepts & Terminology

*   **Vertex:** A representation of a single state in the system. It is fundamentally a dictionary of key-value pairs.
    *   **Keys:** Strings, which can be namespaced (e.g., `"location:lat"`, `"system:time"`). Namespacing helps avoid collisions between different Edge Providers.
    *   **Values:** Can be of any fundamental type: integer, float, string, boolean, or arrays of these types.
*   **Edge:** A directed transition between two Vertices. An edge contains:
    *   `target_vertex`: The Vertex that this edge leads to.
    *   `cost`: A representation of the "cost" of traversing this edge. This can be a single float for simple cases or a vector of floats for multi-objective planning (e.g., `[time, dollars, emissions]`). For stochastic planning, this can represent a distribution.
    *   `metadata`: An optional key-value dictionary for storing edge-specific information, like `"transit:line_name": "Red Line"`.
*   **Edge Provider:** A pluggable module responsible for generating valid Edges from a given Vertex. It contains the "rules" of the problem domain. For example, a `street_network` provider would look for a `location:*` key in a Vertex and generate walking/driving edges to adjacent locations.
*   **Planner:** An algorithm that uses the services of the Graph Expander to find a path. Examples: Dijkstra, A*, Dual-Path A*.
*   **Graph Expander:** The core component that, given a Vertex, queries all registered Edge Providers and aggregates the list of generated outgoing Edges. This is the bridge between Planners and Edge Providers.
*   **Plan / Path:** A sequence of Edges from a start Vertex to a goal Vertex.

### 4. High-Level Architecture

The system is composed of several distinct layers, ensuring a strong separation of concerns.

```
+-------------------------------------------------+
|               User Application                  |
| (e.g., Android App, iOS App, Python Script)     |
+----------------------+--------------------------+
                       |
+----------------------+--------------------------+
|          Language Bindings (Idiomatic API)      |
|  (Kotlin / Swift / Python)                      |
+----------------------+--------------------------+
                       | (FFI: JNI, C ABI, CTypes)
+======================+==========================+
|               Graphserver Core (C Library)            |
|                                                 |
|  +----------------+      +--------------------+ |
|  |    Planners    |----->|  Graph Expander    | |
|  | (A*, Dijkstra) |      | (Routes requests)  | |
|  +----------------+      +---------+----------+ |
|                                    |            |
|  +---------------------------------+----------+ |
|  |     Registered Edge Providers (Plugins)     | |
|  | +----------+ +----------+ +----------+      | |
|  | | street   | | bus      | | subway   | ...  | |
|  | +----------+ +----------+ +----------+      | |
|  +---------------------------------------------+ |
+=================================================+
```

### 5. Detailed Component Design

#### 5.1. The Graphserver Core (C Library)

This is the self-contained, dependency-free C library.

**Data Structures (Illustrative C `struct`s):**

```c
// Represents any value type
typedef enum { GS_INT, GS_FLOAT, GS_STRING, ... } GraphserverValueType;
typedef struct {
    GraphserverValueType type;
    union {
        int64_t i_val;
        double f_val;
        const char* s_val;
        // ... array types
    } as;
} GraphserverValue;

// A key-value pair in a Vertex
typedef struct {
    const char* key;   // e.g., "location:lat"
    GraphserverValue value;
} GraphserverKeyPair;

// A Vertex is effectively a sorted array of key-value pairs for efficient lookup.
typedef struct {
    size_t num_pairs;
    GraphserverKeyPair* pairs;
} GraphserverVertex;

// An Edge, supporting multi-objective distances.
typedef struct {
    GraphserverVertex* target_vertex;
    double* distance_vector; // Array of distances, e.g., [time, meters]
    size_t distance_vector_size;
    // Optional metadata can be here as well
} GraphserverEdge;

// A list of edges returned by an Edge Provider
typedef struct {
    size_t num_edges;
    GraphserverEdge* edges;
} GraphserverEdgeList;
```

**Core API (C ABI):**

The C API will be function-based and manage memory explicitly.

```c
// Opaque handle to the main engine instance
typedef struct GraphserverEngine GraphserverEngine;

// Engine lifecycle
GraphserverEngine* gs_engine_create();
void gs_engine_destroy(GraphserverEngine* engine);

// Edge Provider registration
// The function pointer is the contract for all providers.
typedef int (*gs_generate_edges_fn)(
    const GraphserverVertex* current_vertex,
    GraphserverEdgeList* out_edges,
    void* user_data
);

void gs_engine_register_provider(
    GraphserverEngine* engine,
    const char* provider_name,
    gs_generate_edges_fn generator_func,
    void* user_data // Optional state for the provider
);

// Main planning function
typedef bool (*gs_goal_predicate_fn)(const GraphserverVertex* vertex, void* user_data);

GraphserverPath* gs_plan(
    GraphserverEngine* engine,
    const GraphserverVertex* start_vertex,
    gs_goal_predicate_fn is_goal,
    const char* planner_name // e.g., "A_STAR"
    // ... other options like heuristic function pointers
);
```

#### 5.2. Edge Provider (Plugin) Interface

A developer creates a new Edge Provider by implementing a single function with the `gs_generate_edges_fn` signature.

*   **Input:** The current `Vertex` being considered by the planner.
*   **Logic:** The function inspects the `Vertex`'s key-value pairs. If it contains data relevant to the provider's domain (e.g., `street_network` provider finds `location:lat` and `location:lon`), it calculates possible next states.
*   **Output:** It populates the `out_edges` list with newly created `Edge` structures. Each `Edge` must contain a fully-defined `target_vertex`.

#### 5.3. Language Bindings (FFI)

The goal is to provide an idiomatic API in the target language, abstracting away the C pointers and manual memory management.

**Python Example:**

```python
import graphserver

# Create and configure the engine
engine = graphserver.Engine()
engine.register_provider("street_network", street_provider_logic)
engine.register_provider("bus_network", bus_provider_logic)

# Define start and goal
start_vertex = graphserver.Vertex({
    "location:lat": 40.7128,
    "location:lon": -74.0060,
    "system:time": 1678886400
})

def is_at_destination(vertex):
    return vertex.get("location:name") == "Office"

# Plan
plan = engine.plan(
    start=start_vertex,
    goal=is_at_destination,
    planner="A_STAR_MULTI_OBJECTIVE"
)

# Use the result
for edge in plan.edges:
    print(f"Transition to {edge.target_vertex} with cost {edge.cost}")
```

The Python `graphserver.Vertex` class would internally call the C functions (`gs_vertex_create`, `gs_vertex_add_pair`, etc.) and manage the `GraphserverVertex*` pointer's lifecycle via its `__init__` and `__del__` methods.

### 6. Handling Advanced Features

*   **Multi-Objective Planning:**
    *   The `GraphserverEdge` `distance_vector` is central.
    *   Planners like A* will be adapted. Instead of a single `f = g + h` value, the priority queue will order states based on a Pareto dominance check or a weighted sum of the cost vectors. The `gs_plan` function will take a weighting vector as an argument.
*   **Stochastic Planning:**
    *   The `distance_vector` can be re-interpreted. For example, instead of `[time]`, it could be `[mean_time, time_variance]`.
    *   Stochastic-aware algorithms (e.g., finding the path with the highest probability of arriving under a certain time budget) will be added to the planner library. This requires a different kind of "cost" accumulation, moving from addition to probabilistic composition.
*   **Alternative Paths:**
    *   Implement planners specifically for this, such as Yen's K-shortest paths or a "Dual-Path A*" which maintains two path solutions (optimal and next-best) for each node during the search. The `gs_plan` API can be extended to return a list of `GraphserverPath` objects.

### 7. Example Use Case: Multi-Modal Transit

1.  **Setup:** The application creates a `GraphserverEngine` and registers three providers:
    *   `walk_provider`: Generates walking edges to nearby coordinates.
    *   `bus_provider`: Queries an external API or local database for bus stops near a `location:*` vertex. If a stop is nearby, it generates an edge for "wait for bus" (cost is waiting time) and a subsequent edge for "ride bus" (cost is ride time + fare). It manipulates the `system:time` key in its generated vertices.
    *   `subway_provider`: Similar to the bus provider, but for subway stations.
2.  **Query:**
    *   `start_vertex`: `{ "location:lat": 40.7, "location:lon": -74.0, "system:time": ... }`
    *   `goal_predicate`: A function that returns `true` if a vertex's `location:*` is within a small radius of the destination coordinates.
    *   `cost_weights`: `[1.0, 0.5]` representing a desire to minimize time primarily, and cost secondarily.
3.  **Execution Flow:**
    *   A* planner starts with `start_vertex`.
    *   It calls the Graph Expander. The expander calls all three providers.
    *   `walk_provider` generates edges to nearby street corners.
    *   `bus_provider` finds a nearby bus stop and generates a "wait" edge.
    *   `subway_provider` finds a nearby subway station and generates a "walk to station" edge.
    *   The A* planner adds these new vertices to its open set, prioritizes them based on the weighted cost, and continues expanding the most promising vertex until the goal is found.

### 8. Development Roadmap & Milestones

*   **M1: Core C Library & Data Structures:**
    *   Implement `GraphserverVertex`, `GraphserverEdge`, and `GraphserverEngine` in C.
    *   Implement the Graph Expander and provider registration system.
    *   Implement a simple, single-objective Dijkstra planner.
    *   Unit tests for all core components.
*   **M2: Python Bindings & First Example:**
    *   Develop Python bindings using `ctypes` or `cffi`.
    *   Create a simple "grid world" Edge Provider to test the whole system end-to-end.
    *   Write documentation for using the Python API.
*   **M3: Advanced Planners & Features:**
    *   Implement a multi-objective A* planner.
    *   Enhance the `GraphserverEdge` struct and planner to support the multi-objective distance_vector.
    *   Implement a dual-path planner for alternative routes.
*   **M4: Mobile Bindings:**
    *   Develop Kotlin/JNI bindings for Android.
    *   Develop Swift bindings using its C interoperability.
    *   Create simple example applications for both iOS and Android.
*   **M5: Stochastic Support:**
    *   Research and define the data structures for representing stochastic costs.
    *   Implement a basic stochastic-aware planning algorithm.
*   **Future:** Performance profiling and optimization, more built-in planners, a library of common Edge Providers (e.g., using OpenStreetMap data), improved documentation.

Excellent. Let's continue building out the design document, moving into more detailed implementation specifics, strategies, and project considerations.

---

### 9. Detailed API & Data Model Specification

This section provides a more granular look at the core C API and how it will be exposed through the language bindings.

#### 9.1. C Core API - Detailed Specification

The C API is the bedrock of the system. It must be stable, performant, and thread-safe where applicable. The primary interaction pattern is: the user creates objects (Vertices, etc.), passes them to the engine (which treats them as `const`), and the engine returns new, engine-managed objects that the user must eventually release.

**Vertex & Value Management:**

```c
// --- Value Creation ---
GraphserverValue gs_value_create_int(int64_t val);
GraphserverValue gs_value_create_float(double val);
GraphserverValue gs_value_create_string(const char* val); // String is copied internally

// --- Vertex Creation and Manipulation ---
// A Vertex handle is opaque to the user.
typedef struct GraphserverVertex GraphserverVertex;

GraphserverVertex* gs_vertex_create();
// Adds or updates a key. The key string is copied. The value is consumed.
int gs_vertex_set_kv(GraphserverVertex* vertex, const char* key, GraphserverValue value);
// Returns a copy of the value. The user does not need to free the returned value.
GraphserverValue gs_vertex_get_value(const GraphserverVertex* vertex, const char* key);
// Creates a deep copy of a vertex.
GraphserverVertex* gs_vertex_clone(const GraphserverVertex* vertex);
// Releases memory associated with the vertex.
void gs_vertex_destroy(GraphserverVertex* vertex);
// Generates a canonical hash for a vertex. Essential for 'closed set' tracking in planners.
uint64_t gs_vertex_hash(const GraphserverVertex* vertex);
// Compares two vertices for equality.
bool gs_vertex_are_equal(const GraphserverVertex* v1, const GraphserverVertex* v2);
```

**Planning API:**

```c
// Opaque handle to a plan result.
typedef struct GraphserverPath GraphserverPath;

// --- Heuristic Function Pointer for A* ---
// Estimates the distance from a given vertex to the goal.
// The distance_vector must be allocated by the user and have the correct size.
typedef void (*gs_heuristic_fn)(
    const GraphserverVertex* vertex,
    double* out_distance_vector,
    void* user_data
);

// --- Planner Configuration ---
// A struct to hold all planning options to avoid a function with 20 arguments.
typedef struct {
    const char* planner_name; // "A_STAR", "DIJKSTRA"
    const GraphserverVertex* start_vertex;
    gs_goal_predicate_fn is_goal_fn;
    void* is_goal_user_data;

    // Optional for A* and other heuristic planners
    gs_heuristic_fn heuristic_fn;
    void* heuristic_user_data;

    // For multi-objective planners
    const double* distance_weights;
    size_t distance_vector_size;

    // Other options
    uint32_t max_path_alternatives; // for alternative path planners
    double timeout_seconds;
} GraphserverPlanOptions;

// --- Main Planning Function (Revised) ---
// Returns a list of paths found.
GraphserverPathList* gs_plan(GraphserverEngine* engine, const GraphserverPlanOptions* options);

// --- Path Result Inspection ---
size_t gs_pathlist_get_count(const GraphserverPathList* path_list);
GraphserverPath* gs_pathlist_get_path(const GraphserverPathList* path_list, size_t index);
void gs_pathlist_destroy(GraphserverPathList* path_list);

size_t gs_path_get_num_edges(const GraphserverPath* path);
const GraphserverEdge* gs_path_get_edge(const GraphserverPath* path, size-t index);
const double* gs_path_get_total_cost(const GraphserverPath* path);
```

#### 9.2. Memory Management Strategy

A clear memory ownership model is critical for preventing leaks when crossing the FFI boundary.

*   **Rule 1: Library Owns What It Creates.** Any object pointer returned by a `gs_*` function (e.g., `gs_vertex_create`, `gs_plan`) is owned by the C library's heap, but its lifetime is managed by the caller. The caller is responsible for calling the corresponding `gs_*_destroy` function on it.
*   **Rule 2: Caller Owns What It Passes In.** When passing pointers into the API (e.g., `GraphserverVertex*` in `gs_plan`), the library will treat them as `const` and will not attempt to free them. The caller retains ownership.
*   **Rule 3: Primitives and `const char*` are Copied.** The library will internally copy data from primitive types and input strings. The caller can free their local `char*` buffer immediately after the API call returns.
*   **Language Binding Responsibility:** The idiomatic language bindings (Python, Swift, Kotlin) are responsible for implementing this contract correctly. For example, a Python `Vertex` class will call `gs_vertex_create` in its `__init__` and `gs_vertex_destroy` in its `__del__` or `__exit__` method, implementing the RAII (Resource Acquisition Is Initialization) pattern.

### 10. Performance Considerations & Optimizations

The "on-the-fly" nature of the engine requires careful optimization of the planning loop.

*   **Vertex Representation:**
    *   **Hashing & Canonical Form:** To efficiently check if a state has already been visited (the "closed set" in A*), vertices need a fast, canonical hash. The `gs_vertex_set_kv` function will insert keys in a sorted order. This ensures that two vertices with the same key-value pairs, added in a different order, will have an identical memory layout, allowing for a simple `memcmp` for equality and a fast hash function (`gs_vertex_hash`) over the raw bytes.
*   **Memory Allocation:**
    *   **Arena Allocation:** A single planning operation can create and destroy thousands of small `Vertex` and `Edge` objects. Frequent `malloc`/`free` calls can be a major bottleneck. We will implement an arena allocator for each `gs_plan` call. A large block of memory is allocated once at the start of the planning process, and all transient objects (new vertices, edges, planner nodes) are allocated from this arena with a simple pointer bump. The entire arena is freed in a single `free()` call when planning is complete. This dramatically reduces allocation overhead.
*   **Algorithm Data Structures:**
    *   **Priority Queue:** The performance of Dijkstra and A* is dominated by the efficiency of their priority queue ("open set"). A standard binary heap is a good starting point. For very dense graphs, a Fibonacci heap could be implemented and chosen via `GraphserverPlanOptions` for potentially better asymptotic performance, though with higher constant overhead.
*   **Concurrency:**
    *   The `Graph Expander` is a natural candidate for parallelization. When expanding a vertex, the engine could invoke multiple Edge Providers concurrently on a thread pool. This would be particularly effective if providers perform I/O (e.g., querying a network service or a local database). The core `GraphserverEngine` object would manage this thread pool. The `gs_plan` call itself would be a blocking, single-threaded operation from the user's perspective, but would leverage concurrency internally.

### 11. Testing Strategy

A multi-layered testing approach will be used to ensure correctness and robustness.

*   **Layer 1: C Core Unit Tests:**
    *   Framework: A simple C unit testing framework like `CTest`, `Check`, or even a custom minimal runner.
    *   Coverage: Test all data structures (Vertex hashing/equality, value types), individual planners with mock providers, and memory management (testing for leaks with tools like Valgrind).
*   **Layer 2: FFI Integration Tests:**
    *   Goal: Verify that the language bindings correctly map data types, manage memory, and handle return values from the C core.
    *   Process: For each language (Python, Swift, Kotlin), tests will be written that call every exposed C API function and assert the results. For example, a Python test would create a `graphserver.Vertex`, check its properties, pass it to a simple plan, and verify that the `__del__` method correctly frees the underlying C memory.
*   **Layer 3: End-to-End (E2E) Tests:**
    *   Goal: Test a complete, realistic user scenario.
    *   Process: These tests will use the high-level language bindings (e.g., Python). They will set up an engine with multiple, interacting mock Edge Providers (e.g., `walk_provider`, `bus_provider`) and run a complex multi-objective plan. The resulting path will be validated for correctness, cost, and adherence to the rules of the mock providers.
*   **Layer 4: Benchmarking:**
    *   Goal: Track and prevent performance regressions.
    *   Process: A dedicated benchmarking suite will be created. It will run standardized planning problems (e.g., finding a path on a 1000x1000 grid, a mock city transit scenario) and record key metrics: time-to-first-solution, total execution time, and peak memory usage. These benchmarks will run as part of the CI/CD pipeline.

### 12. Risk Assessment & Mitigation

| Risk                                     | Likelihood | Impact | Mitigation Strategy                                                                                                                                                                                                |
| ---------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Performance of C Core is Insufficient**| Medium     | High   | Prioritize M1/M2 to establish performance baselines early. Use aggressive optimization (arena allocation, canonical vertex forms). Profile extensively with tools like `perf` or Valgrind/Callgrind.                |
| **FFI Complexity Leads to Instability**  | Medium     | High   | Keep the C API surface minimal and data-oriented. Invest heavily in FFI integration tests (Layer 2) for each language. Provide clear documentation on the memory management contract for all binding developers.   |
| **Pluggable Architecture is Inflexible** | Low        | High   | The "Vertex as a dictionary" model is inherently flexible. The main mitigation is to dogfood the API by building several diverse example Edge Providers (travel, game AI) during initial development (M2, M3). |
| **Scope Creep**                          | High       | Medium | Adhere strictly to the Goals and Non-Goals. Defer complex features like a graphical debugger or a sophisticated stochastic modeling language. Maintain a clear backlog and roadmap.                           |
| **State Explosion in Complex Problems**  | High       | Medium | This is an inherent problem in planning. The engine's role is to provide the tools to manage it: efficient closed-set checking, good heuristics (user's job), and memory-efficient data structures. Document best practices for users on how to design their state space (Vertex) to be as minimal as possible. |

### 13. Deployment and Packaging

*   **C Core Library:** Will be built using CMake. It will produce a static library (`.a`) for linking directly into mobile apps and a dynamic library (`.so`/`.dylib`/`.dll`) for use by Python and other server-side languages. A CI/CD pipeline (e.g., GitHub Actions) will build and test these artifacts for Linux, macOS, and Windows.
*   **Python Package:** A `setup.py` script will be created to package the Python bindings and the pre-compiled dynamic library into a wheel. This will be published to PyPI for easy installation (`pip install graphserver-engine`).
*   **Kotlin (Android) Package:** The C core will be compiled as a static library for various Android ABIs (arm64-v8a, x86_64). A small JNI wrapper in C++ will be written. These will be packaged into an Android Archive (AAR) and published to a repository like Maven Central.
*   **Swift (iOS) Package:** The C core will be compiled as a static library for iOS architectures. It will be distributed via the Swift Package Manager, which has excellent support for including C libraries in a Swift project.

### 14. Open Questions & Future Considerations

*   **Stochastic Representation:** What is the best generic format for representing a probability distribution for an edge cost? A simple `(mean, variance)` pair? A list of `(outcome, probability)` pairs? This requires more research into the needs of common stochastic planning algorithms.
*   **Edge Provider Versioning:** How do we handle potential breaking changes in the data an Edge Provider expects or produces in a Vertex? A formal versioning system for namespaces (e.g., `"location-v2:lat"`) might be necessary for long-term stability.
*   **Hot-Reloading of Providers:** For interactive use cases (e.g., game development), could we support unloading and reloading Edge Provider logic without restarting the engine? This would require dynamic library loading (`dlopen`) and careful state management.
*   **Asynchronous Planning API:** Should `gs_plan` have a non-blocking variant that returns a future/promise and executes the planning on a background thread? This would be a valuable addition for responsive UI applications.