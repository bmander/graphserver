# Missing Tests in Core C Library

This document outlines the test coverage gaps identified in the core C library and provides a prioritized plan for adding comprehensive tests.

## Analysis Summary

**Existing Infrastructure**: The project uses a macro-based testing framework (`TEST`, `ASSERT`, etc.) that is simple and effective. New tests should follow this established pattern.

**Critical Gaps**: While most modules have some testing, significant gaps exist in core components that are critical for routing functionality.

## Test Plan

### Priority 1: Create Dedicated Test Suite for `priority_queue.c` (HIGHEST)

**Rationale**: The priority queue is fundamental to Dijkstra's algorithm. Its correctness is non-negotiable.

**Actions**:
1. Create new test file: `core/tests/test_priority_queue.c`
2. Copy test framework macros from existing test files
3. Move existing priority queue tests from `core/tests/test_planner.c`
4. Implement comprehensive test cases:
   - `test_pq_creation_and_destruction`: Memory allocation/deallocation
   - `test_pq_extract_from_empty`: Empty queue handling
   - `test_pq_decrease_nonexistent_key`: Non-existent vertex handling
   - `test_pq_insert_with_duplicate_priorities`: Duplicate priority behavior
   - `test_pq_stress_test`: Large dataset handling (>1000 elements)
   - `test_pq_null_inputs`: NULL input robustness

### Priority 2: Add Unit Tests for `planner_dijkstra.c` Internals (HIGH)

**Rationale**: Existing tests are integration-focused but don't verify internal algorithm logic.

**Actions**:
1. Create new test file: `core/tests/test_planner_dijkstra.c`
2. Implement algorithm-specific test cases:
   - `test_dijkstra_path_reconstruction`: Verify path building from closed_set
   - `test_dijkstra_max_visited_vertices_limit`: Vertex limit enforcement
   - `test_dijkstra_graph_with_cycles`: Cycle handling without infinite loops
   - `test_dijkstra_zero_cost_edges`: Zero-weight edge behavior
   - `test_dijkstra_provider_error`: Error handling during planning

### Priority 3: Review and Enhance Existing Tests (MEDIUM)

**Rationale**: General coverage improvements after addressing critical gaps.

**Actions**:
- Review public functions in `engine.c`, `cache.c`, `hashmap.c`
- Compare against existing test coverage
- Add tests for uncovered functions and error-handling paths

## Current Test Status

**Files with Good Coverage**:
- `edge.c` - Has dedicated test suite
- `graph.c` - Has dedicated test suite
- Basic planner functionality - Integration tests exist

**Files Needing Attention**:
- `priority_queue.c` - Missing dedicated test suite
- `planner_dijkstra.c` - Missing unit tests for internal logic
- `engine.c` - May have coverage gaps
- `cache.c` - May have coverage gaps
- `hashmap.c` - May have coverage gaps

## Implementation Notes

- Follow existing test patterns and macro usage
- Ensure all new tests integrate with current build system
- Focus on edge cases, error conditions, and boundary testing
- Include stress tests for performance-critical components
- Verify memory management (allocation/deallocation) in all tests