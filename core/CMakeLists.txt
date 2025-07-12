cmake_minimum_required(VERSION 3.8)
project(graphserver_core C)

# Build options
set(CMAKE_C_STANDARD 99)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Find clang-tidy
find_program(CLANG_TIDY_EXE
    NAMES "clang-tidy"
    DOC "Path to clang-tidy executable")

# Enable clang-tidy if found
if(CLANG_TIDY_EXE)
    message(STATUS "Found clang-tidy: ${CLANG_TIDY_EXE}")
    set(CMAKE_C_CLANG_TIDY ${CLANG_TIDY_EXE})
else()
    message(WARNING "clang-tidy not found. Install clang-tidy to enable static analysis.")
endif()

# Source files
file(GLOB CORE_SRCS
    "${CMAKE_CURRENT_SOURCE_DIR}/*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/edgetypes/*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/fibheap/*.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/hashtable/*.c")

# router.c is a legacy file that is not part of the library
list(REMOVE_ITEM CORE_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/router.c")

add_library(graphserver SHARED ${CORE_SRCS})

# Public headers for installation
set(PUBLIC_HEADERS
    fibheap/fibheap.h
    fibheap/dirfibheap.h
    graph.h
    hashtable/hashtable_gs.h
    hashtable/hashtable_itr.h
    hashtable/hashtable.h
    hashtable/hashtable_utility.h
    hashtable/hashtable_private.h)

# Include directories
target_include_directories(graphserver
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/fibheap
    ${CMAKE_CURRENT_SOURCE_DIR}/hashtable
    ${CMAKE_CURRENT_SOURCE_DIR}/edgetypes)

# Link libraries
find_library(M_LIB m)
find_library(DL_LIB dl)
if(M_LIB)
    target_link_libraries(graphserver PUBLIC ${M_LIB})
endif()
if(DL_LIB)
    target_link_libraries(graphserver PUBLIC ${DL_LIB})
endif()

set_target_properties(graphserver PROPERTIES OUTPUT_NAME graphserver)

install(TARGETS graphserver
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)
install(FILES ${PUBLIC_HEADERS} DESTINATION include/graphserver)


