cmake_minimum_required(VERSION 3.15)
project(graphserver_python)

# Find Python and required components
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

# Get absolute paths
get_filename_component(CORE_BUILD_DIR "../core/build" ABSOLUTE)
get_filename_component(CORE_INCLUDE_DIR "../core/include" ABSOLUTE)
get_filename_component(CORE_SOURCE_DIR "../core" ABSOLUTE)

# Check if core library exists, if not try to build it
if(EXISTS "${CORE_BUILD_DIR}/libgraphserver_core.a")
    # Use pre-built core library
    add_library(graphserver_core STATIC IMPORTED)
    set_target_properties(graphserver_core PROPERTIES
        IMPORTED_LOCATION "${CORE_BUILD_DIR}/libgraphserver_core.a"
        INTERFACE_INCLUDE_DIRECTORIES "${CORE_INCLUDE_DIR}"
    )
else()
    # Try to build core library if source is available
    if(EXISTS "${CORE_SOURCE_DIR}/CMakeLists.txt")
        add_subdirectory(${CORE_SOURCE_DIR} core_build)
    else()
        message(FATAL_ERROR "Core library not found. Please build the core library first by running 'cmake --build build' in the ../core directory.")
    endif()
endif()

# Create the extension module with all source files
Python_add_library(_graphserver MODULE 
    src/graphserver/_graphserver.c
    src/graphserver/extension/engine.c
    src/graphserver/extension/providers.c
    src/graphserver/extension/conversion.c
    src/graphserver/extension/validation.c
    src/graphserver/extension/cleanup.c
    src/graphserver/extension/cache.c
)

# Link to core graphserver library
target_include_directories(_graphserver PRIVATE ../core/include)
target_link_libraries(_graphserver PRIVATE graphserver_core m)

# Set C standard and compiler flags
target_compile_features(_graphserver PRIVATE c_std_99)
target_compile_options(_graphserver PRIVATE -Wall -Wextra)

# Install the extension module for py-build-cmake
# Use default Python module installation destination
if(DEFINED PY_BUILD_CMAKE_MODULE_NAME)
    install(TARGETS _graphserver 
        COMPONENT python_extension
        LIBRARY DESTINATION ${PY_BUILD_CMAKE_MODULE_NAME}
        RUNTIME DESTINATION ${PY_BUILD_CMAKE_MODULE_NAME}
    )
else()
    # Fallback for standalone builds
    install(TARGETS _graphserver 
        LIBRARY DESTINATION .
        RUNTIME DESTINATION .
    )
endif()