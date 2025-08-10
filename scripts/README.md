# GraphServer Core Routing Algorithm Profiling Suite

This directory contains profiling scripts designed to identify performance bottlenecks in the GraphServer core routing algorithm using real-world UW Campus OSM data.

## Overview

The profiling suite focuses on **profiling the C code** rather than the Python wrapper, providing detailed insights into the core routing performance with realistic workloads.

## Files

### Core Profiling Scripts

- **`profile_routing.c`** - C-based profiler that directly exercises core C routing functions
- **`profile_osm_routing.py`** - Python script that uses OSM data but profiles C-level performance  
- **`Makefile`** - Build system for compiling and running profilers

### Key Features

- **Real-world scenarios**: Uses UW Campus OSM data with realistic routing coordinates
- **C-level profiling**: Focuses on core C algorithm performance, not Python overhead
- **Multiple test modes**: Standard timing, stress testing, memory profiling, gprof integration
- **Comprehensive analysis**: Performance breakdowns, bottleneck identification, optimization recommendations

## Quick Start

### 1. Build and Run C Profiler (Recommended)

```bash
# Build the C profiler
cd scripts/
make

# Run with default settings (25 scenarios)
make profile

# Run with specific number of scenarios
make profile-25      # 25 scenarios (recommended)
make profile-50      # 50 scenarios (intensive)

# Run with gprof profiling
make gprof

# Clean build artifacts
make clean
```

### 2. Use Python OSM Profiler (Requires Installation)

First install the Python library:
```bash
cd python/
pip install -e .
```

Then run the profiler:
```bash
cd scripts/
python profile_osm_routing.py 10 2    # 10 routes, 2 repetitions
python profile_osm_routing.py --cprofile 15 1  # Detailed cProfile analysis
```

## Profiling Output

### C Profiler Output

```
🚀 GraphServer Core Routing Algorithm Profiler
================================================

🏗️  Setting up routing engine...
✅ Engine configured with walking provider
   Max walking distance: 1200m
   Walking speed: 1.3m/s

📍 Using 15 realistic campus locations for routing scenarios

🏫 Generating 5 realistic campus routing scenarios...
  Route 1: Student Union → South Entrance
    ✅ Path found: 3 edges, 3.8 minutes, 0.002 seconds
  Route 2: North Gate → Student Union  
    ✅ Path found: 1 edges, 1.3 minutes, 0.000 seconds
  ...

📊 Campus Routing Performance Summary:
  Scenarios tested: 5
  Successful routes: 5 (100.0%)
  Total planning time: 0.003 seconds
  Average per route: 0.001 seconds
  Total vertices expanded: 87 (avg: 17.4 per route)
  Total edges examined: 984 (avg: 196.8 per route)

🔥 Running intensive routing stress test...
  Stress test completed: 50/50 successful routes in 0.219 seconds
  Stress test throughput: 227.8 routes/second

🧠 Profiling memory usage patterns...
  Cycle 1: 4856 bytes peak memory, 1 vertices expanded
  ...

============================================================
🔍 CORE ROUTING ALGORITHM PROFILING RESULTS
============================================================

⏱️  Function Performance Breakdown:
Function                       Calls     Total(s)      Avg(ms)      Min(ms)      Max(ms)
-------------------------------------------------------------------------------------
total_planning                    75     0.641285        8.550        0.002      221.551

🎯 Performance Insights:
  🐌 Slowest function: total_planning (99.099% of total time)
  🔄 Most called function: total_planning (75 calls)

💡 Optimization Recommendations:
  🎯 HIGH PRIORITY: Optimize total_planning (99.1% of execution time)

⚡ Total execution time: 0.647 seconds
🏁 Profiling completed! Use results to identify performance bottlenecks.
```

### Python OSM Profiler Output

```
🚀 GraphServer Core Routing Algorithm Profiler
==============================================

🏗️  Loading OSM data from python/examples/uw_campus.osm...
✅ OSM data loaded in 2.45 seconds
   Network: 1,234 nodes, 567 ways

🎯 Profiling 10 routes × 2 repetitions = 20 total routing operations
======================================================================

📊 Repetition 1/2
  Route  1: (47.6591,122.3044) → (47.6591,-122.3043) ✅ 0.023s (12 edges)
  ...

======================================================================
🔍 CORE ROUTING ALGORITHM PERFORMANCE ANALYSIS
======================================================================

📊 Overall Statistics:
  Total routing operations: 20
  Successful routes: 18 (90.0%)
  Total execution time: 4.56 seconds
  Average time per route: 0.228 seconds
  Throughput: 4.4 routes/second

🧠 Core Algorithm Performance:
  Total vertices expanded: 2,847
  Total edges generated: 15,432
  Avg vertices per route: 158.2
  Avg edges per route: 857.3
  Peak memory usage: 12.3 MB

⏱️  Timing Analysis:
  Fastest route: 0.012 seconds
  Slowest route: 0.456 seconds
  Average route: 0.228 seconds
  Timing variance: 38.0x

💾 Cache Performance:
  Cache hits: 145
  Cache misses: 67
  Hit rate: 68.4%
  Provider calls: 1,892

🎯 Performance Assessment:
  ⚠️  MODERATE: Consider optimization for better performance
  ✅ HIGH SUCCESS RATE: Excellent route connectivity
```

## Understanding the Results

### Key Metrics

1. **Success Rate**: Percentage of routes successfully found
2. **Average Route Time**: Mean time per routing operation
3. **Vertices Expanded**: Core algorithm workload indicator
4. **Memory Usage**: Peak memory consumption patterns
5. **Cache Performance**: Efficiency of edge caching system

### Performance Assessment

- **Excellent** (< 50ms): Very fast routing performance
- **Good** (50-100ms): Acceptable routing performance  
- **Moderate** (100-200ms): Consider optimization
- **Slow** (> 200ms): Performance optimization recommended

### Bottleneck Identification

The profiler identifies functions consuming the most execution time and provides optimization recommendations:

- **HIGH PRIORITY**: Functions using >25% of execution time
- **MEDIUM PRIORITY**: Functions using 10-25% of execution time

## Advanced Profiling

### gprof Integration

```bash
make gprof
# Generates gprof_report.txt with detailed function call analysis
```

### Valgrind Memory Profiling

```bash
make valgrind
# Requires Valgrind installation
# Generates callgrind.out for detailed memory analysis
```

### Performance Comparison

```bash
make compare
# Runs multiple scenario sizes for performance comparison
```

## Customization

### Modifying Test Scenarios

Edit the `uw_campus_locations[]` array in `profile_routing.c` to add new test locations:

```c
static CampusLocation uw_campus_locations[] = {
    {47.6590651, -122.3043738, "Central Plaza"},
    {47.6591000, -122.3043000, "Library Entrance"}, 
    // Add your locations here
};
```

### Adjusting Engine Configuration

Modify walking parameters in the profiler initialization:

```c
WalkingConfig walking_config = walking_config_default();
walking_config.max_walking_distance = 1200.0; // Adjust max distance
walking_config.walking_speed_mps = 1.3;       // Adjust walking speed
```

## Requirements

### C Profiler
- CMake 3.12+
- GCC with C99 support
- Built GraphServer core library

### Python Profiler  
- Python 3.8+
- GraphServer Python library: `pip install graphserver[osm]`
- UW Campus OSM data (included)

## Troubleshooting

### Build Issues

```bash
# Ensure core library is built first
cd core/
mkdir build && cd build
cmake .. && make

# Clean and rebuild profiler
cd scripts/
make clean && make
```

### Missing Dependencies

```bash
# Install build tools
sudo apt-get install build-essential cmake

# Install Python dependencies
pip install graphserver[osm]
```

### No Routes Found

- Check that OSM data contains connected pedestrian paths
- Verify coordinate pairs are within the OSM data bounds
- Increase `max_walking_distance` in walking configuration

## Performance Optimization Tips

Based on profiling results:

1. **High vertex expansion**: Consider implementing A* with better heuristics
2. **Memory growth**: Investigate arena allocation efficiency 
3. **Cache misses**: Optimize edge caching strategy
4. **Slow individual routes**: Profile specific routing scenarios

## Contributing

When adding new profiling capabilities:

1. Focus on C-level performance rather than Python overhead
2. Use realistic routing scenarios based on real OSM data
3. Provide clear performance assessments and recommendations
4. Include both timing and memory analysis

## Files Generated

- `profile_routing` - Compiled C profiler executable
- `gprof_report.txt` - gprof function analysis (if using `make gprof`)
- `callgrind.out` - Valgrind memory profile (if using `make valgrind`) 
- `routing_profile.prof` - cProfile data (if using Python `--cprofile`)