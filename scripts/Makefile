#!/usr/bin/make -f

# Makefile for GraphServer Routing Profiler
# Builds and runs performance profiling for core routing algorithm

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2 -g -DNDEBUG
PROFILE_FLAGS = -pg -fprofile-arcs -ftest-coverage
LDFLAGS = -lm -lrt -lpthread

# Paths
CORE_DIR = ../core
BUILD_DIR = ../core/build
EXAMPLES_DIR = ../examples
SCRIPT_DIR = .

# Include directories
INCLUDES = -I$(CORE_DIR)/include -I$(EXAMPLES_DIR)/include

# Core library
CORE_LIB = $(BUILD_DIR)/libgraphserver_core.a

# Example providers object files
PROVIDER_SOURCES = $(EXAMPLES_DIR)/providers/utility_functions.c \
                   $(EXAMPLES_DIR)/providers/walking_provider.c \
                   $(EXAMPLES_DIR)/providers/transit_provider.c \
                   $(EXAMPLES_DIR)/providers/road_network_provider.c

PROVIDER_OBJECTS = $(PROVIDER_SOURCES:.c=.o)

# Profiler executable
PROFILER_TARGET = profile_routing
GPROF_TARGET = profile_routing_gprof

.PHONY: all clean profile gprof help build-core

all: $(PROFILER_TARGET)

help:
	@echo "GraphServer Routing Profiler Build System"
	@echo "==========================================="
	@echo ""
	@echo "Targets:"
	@echo "  all           - Build standard profiler (default)"
	@echo "  profile       - Build and run profiler with default scenarios"
	@echo "  profile-25    - Run profiler with 25 scenarios (recommended)"
	@echo "  profile-50    - Run profiler with 50 scenarios (intensive)"
	@echo "  gprof         - Build with gprof profiling and run"
	@echo "  clean         - Remove built files"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Requirements:"
	@echo "  - Core library must be built first (run 'make build-core')"
	@echo "  - GCC with C99 support"
	@echo ""
	@echo "Usage Examples:"
	@echo "  make profile          # Run with default settings"
	@echo "  make profile-25       # Run 25 routing scenarios"
	@echo "  make gprof            # Generate gprof profile data"

# Ensure core library is built
build-core:
	@echo "🏗️  Building core GraphServer library..."
	@if [ ! -d "$(BUILD_DIR)" ]; then \
		mkdir -p $(BUILD_DIR); \
		cd $(BUILD_DIR) && cmake ..; \
	fi
	@cd $(BUILD_DIR) && make -j$$(nproc)
	@echo "✅ Core library built successfully"

# Build provider objects
$(PROVIDER_OBJECTS): %.o: %.c
	@echo "🔧 Compiling provider: $<"
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Standard profiler build
$(PROFILER_TARGET): build-core $(PROVIDER_OBJECTS) $(SCRIPT_DIR)/profile_routing.c
	@echo "🔨 Building routing profiler..."
	$(CC) $(CFLAGS) $(INCLUDES) \
		$(SCRIPT_DIR)/profile_routing.c \
		$(PROVIDER_OBJECTS) \
		$(CORE_LIB) \
		$(LDFLAGS) \
		-o $(PROFILER_TARGET)
	@echo "✅ Profiler built successfully: ./$(PROFILER_TARGET)"

# gprof-enabled build
$(GPROF_TARGET): build-core $(PROVIDER_OBJECTS) $(SCRIPT_DIR)/profile_routing.c
	@echo "🔨 Building gprof-enabled profiler..."
	$(CC) $(CFLAGS) $(PROFILE_FLAGS) $(INCLUDES) \
		$(SCRIPT_DIR)/profile_routing.c \
		$(PROVIDER_OBJECTS) \
		$(CORE_LIB) \
		$(LDFLAGS) \
		-o $(GPROF_TARGET)
	@echo "✅ gprof profiler built successfully: ./$(GPROF_TARGET)"

# Run profiler with default settings
profile: $(PROFILER_TARGET)
	@echo ""
	@echo "🚀 Running GraphServer Routing Profiler"
	@echo "========================================"
	@echo ""
	./$(PROFILER_TARGET)

# Run with specific scenario counts
profile-25: $(PROFILER_TARGET)
	@echo ""
	@echo "🚀 Running Routing Profiler - 25 Scenarios"
	@echo "==========================================="
	@echo ""
	./$(PROFILER_TARGET) 25

profile-50: $(PROFILER_TARGET)
	@echo ""
	@echo "🚀 Running Routing Profiler - 50 Scenarios (Intensive)"
	@echo "====================================================="
	@echo ""
	./$(PROFILER_TARGET) 50

profile-stress: $(PROFILER_TARGET)
	@echo ""
	@echo "🔥 Running Routing Profiler - Stress Test (100 scenarios)"
	@echo "========================================================"
	@echo ""
	./$(PROFILER_TARGET) 100

# Run gprof profiling
gprof: $(GPROF_TARGET)
	@echo ""
	@echo "🔬 Running gprof profiling analysis"
	@echo "===================================="
	@echo ""
	./$(GPROF_TARGET) 25
	@if [ -f gmon.out ]; then \
		echo ""; \
		echo "📊 Generating gprof report..."; \
		gprof $(GPROF_TARGET) gmon.out > gprof_report.txt; \
		echo "✅ gprof report saved to: gprof_report.txt"; \
		echo ""; \
		echo "🎯 Top functions by execution time:"; \
		head -30 gprof_report.txt | tail -20; \
	else \
		echo "❌ No gprof data generated (gmon.out not found)"; \
	fi

# Valgrind memory profiling
valgrind: $(PROFILER_TARGET)
	@echo ""
	@echo "🧠 Running Valgrind memory profiling"
	@echo "===================================="
	@echo ""
	valgrind --tool=callgrind --callgrind-out-file=callgrind.out ./$(PROFILER_TARGET) 10
	@echo ""
	@echo "✅ Valgrind profile saved to: callgrind.out"
	@echo "   View with: kcachegrind callgrind.out"

# Performance comparison
compare: $(PROFILER_TARGET)
	@echo ""
	@echo "⚖️  Running performance comparison tests"
	@echo "======================================="
	@echo ""
	@echo "Testing 10 scenarios..."
	@time ./$(PROFILER_TARGET) 10
	@echo ""
	@echo "Testing 25 scenarios..."
	@time ./$(PROFILER_TARGET) 25

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -f $(PROFILER_TARGET) $(GPROF_TARGET)
	rm -f $(PROVIDER_OBJECTS)
	rm -f gmon.out gprof_report.txt callgrind.out
	rm -f *.gcda *.gcno *.gcov
	@echo "✅ Clean completed"

# Install profiler to system (optional)
install: $(PROFILER_TARGET)
	@echo "📦 Installing profiler to /usr/local/bin..."
	sudo cp $(PROFILER_TARGET) /usr/local/bin/graphserver-profile-routing
	@echo "✅ Installed as: graphserver-profile-routing"

.PHONY: profile profile-25 profile-50 profile-stress gprof valgrind compare install