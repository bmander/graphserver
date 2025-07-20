cmake_minimum_required(VERSION 3.15)
project(graphserver_python)

# Find Python and required components
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)

# Create the extension module
Python_add_library(_graphserver MODULE src/graphserver/_graphserver.c)

# Link to core graphserver library
target_include_directories(_graphserver PRIVATE ../core/include)
target_link_directories(_graphserver PRIVATE ../core/build)
target_link_libraries(_graphserver PRIVATE graphserver_core m)

# Set C standard and compiler flags
target_compile_features(_graphserver PRIVATE c_std_99)
target_compile_options(_graphserver PRIVATE -Wall -Wextra)

# Install the extension
install(TARGETS _graphserver DESTINATION graphserver)