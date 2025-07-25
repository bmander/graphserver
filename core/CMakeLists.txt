cmake_minimum_required(VERSION 3.12)
project(GraphserverCore VERSION 1.0.0 LANGUAGES C)

# Set C standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Compiler flags
if(CMAKE_COMPILER_IS_GNUCC OR CMAKE_C_COMPILER_ID MATCHES "Clang")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra -Werror -fPIC")
    set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -g -O0 -DDEBUG")
    set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -O3 -DNDEBUG")
endif()

# Include directories
include_directories(include)

# Source files
set(CORE_SOURCES
    src/vertex.c
    src/edge.c
    src/memory.c
    src/hash_table.c
    src/cache.c
    src/engine.c
    src/priority_queue.c
    src/planner_dijkstra.c
)

# Example provider sources
set(EXAMPLE_SOURCES
    ../examples/providers/utility_functions.c
    ../examples/providers/walking_provider.c
    ../examples/providers/transit_provider.c
    ../examples/providers/road_network_provider.c
)

# Create the core library
add_library(graphserver_core STATIC ${CORE_SOURCES})

# Create the shared library as well
add_library(graphserver_core_shared SHARED ${CORE_SOURCES})
set_target_properties(graphserver_core_shared PROPERTIES OUTPUT_NAME graphserver_core)

# Set include directories for the library
target_include_directories(graphserver_core PUBLIC include)
target_include_directories(graphserver_core_shared PUBLIC include)

# Testing
enable_testing()

# Test executables
add_executable(test_vertex tests/test_vertex.c)
target_link_libraries(test_vertex graphserver_core)
add_test(NAME vertex_tests COMMAND test_vertex)

add_executable(test_edge tests/test_edge.c)
target_link_libraries(test_edge graphserver_core)
add_test(NAME edge_tests COMMAND test_edge)

add_executable(test_memory tests/test_memory.c)
target_link_libraries(test_memory graphserver_core)
add_test(NAME memory_tests COMMAND test_memory)

add_executable(test_cache tests/test_cache.c)
target_link_libraries(test_cache graphserver_core)
add_test(NAME cache_tests COMMAND test_cache)

add_executable(test_engine tests/test_engine.c)
target_link_libraries(test_engine graphserver_core)
add_test(NAME engine_tests COMMAND test_engine)

add_executable(test_planner tests/test_planner.c)
target_link_libraries(test_planner graphserver_core)
add_test(NAME planner_tests COMMAND test_planner)

add_executable(test_precache tests/test_precache.c)
target_link_libraries(test_precache graphserver_core)
add_test(NAME precache_tests COMMAND test_precache)

add_executable(test_integration tests/test_integration.c ${EXAMPLE_SOURCES})
target_link_libraries(test_integration graphserver_core m)
target_include_directories(test_integration PRIVATE ../examples/include)
add_test(NAME integration_tests COMMAND test_integration)

add_executable(test_performance tests/test_performance.c ${EXAMPLE_SOURCES})
target_link_libraries(test_performance graphserver_core m)
target_include_directories(test_performance PRIVATE ../examples/include)
# Note: Performance tests are not run automatically with 'make test'
# Run manually with: ./test_performance

# Custom target to run all tests
add_custom_target(run_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --verbose
    DEPENDS test_vertex test_edge test_memory test_cache test_engine test_planner test_precache test_integration
    COMMENT "Running all tests"
)

# Install targets
install(TARGETS graphserver_core graphserver_core_shared
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(DIRECTORY include/ DESTINATION include)

# Debug target to check what files are found
add_custom_target(debug_files
    COMMAND ${CMAKE_COMMAND} -E echo "Source files: ${CORE_SOURCES}"
    COMMAND find ${CMAKE_CURRENT_SOURCE_DIR} -name "*.c" -o -name "*.h"
)