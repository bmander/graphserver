# Makefile for Graphserver Examples
# 
# This makefile builds the simple_routing example and provider examples

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -g -O2
INCLUDES = -I../core/include -I./include
LDFLAGS = -L../core/build
LIBS = -lgraphserver_core -lm

# Core library path
CORE_LIB = ../core/build/libgraphserver_core.a

# Source files
SIMPLE_ROUTING_SRC = simple_routing.c
PROVIDER_SRCS = $(wildcard providers/*.c)
PROVIDER_OBJS = $(PROVIDER_SRCS:.c=.o)

# Targets
SIMPLE_ROUTING_TARGET = simple_routing
PROVIDER_LIB = libexample_providers.a

.PHONY: all clean providers simple_routing help

all: providers simple_routing

help:
	@echo "Available targets:"
	@echo "  all           - Build everything"
	@echo "  simple_routing - Build the simple routing example"
	@echo "  providers     - Build provider library"
	@echo "  clean         - Clean build artifacts"
	@echo "  help          - Show this help"

# Build provider library
providers: $(PROVIDER_LIB)

$(PROVIDER_LIB): $(PROVIDER_OBJS)
	ar rcs $@ $^
	@echo "Built provider library: $@"

# Build simple routing example
simple_routing: $(SIMPLE_ROUTING_TARGET)

$(SIMPLE_ROUTING_TARGET): $(SIMPLE_ROUTING_SRC) $(PROVIDER_LIB) $(CORE_LIB)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $< $(PROVIDER_LIB) $(LDFLAGS) $(LIBS)
	@echo "Built simple routing example: $@"

# Compile provider object files
providers/%.o: providers/%.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Check if core library exists
$(CORE_LIB):
	@echo "Error: Core library not found at $(CORE_LIB)"
	@echo "Please build the core library first:"
	@echo "  cd ../core/build && make"
	@exit 1

clean:
	rm -f $(SIMPLE_ROUTING_TARGET)
	rm -f $(PROVIDER_LIB)
	rm -f providers/*.o
	@echo "Cleaned build artifacts"

# Install example (optional)
install: all
	@echo "Installing examples to /usr/local/bin (requires sudo)"
	sudo cp $(SIMPLE_ROUTING_TARGET) /usr/local/bin/

# Run the simple routing example
run: simple_routing
	./$(SIMPLE_ROUTING_TARGET)

# Debug with gdb
debug: simple_routing
	gdb ./$(SIMPLE_ROUTING_TARGET)

# Memory check with valgrind
memcheck: simple_routing
	valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./$(SIMPLE_ROUTING_TARGET)