# Route Planner Makefile
# Simple commands for setting up and running the Route Planner

.PHONY: setup clean run test help

# Default target
help:
	@echo "Route Planner Commands:"
	@echo "  make setup    - Download JavaScript dependencies"
	@echo "  make clean    - Remove downloaded dependencies"
	@echo "  make run      - Run the server (requires OSM_FILE)"
	@echo "  make test     - Run with test OSM file"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make setup"
	@echo "  make run OSM_FILE=../../examples/uw_campus.osm"
	@echo "  make test"

# Setup JavaScript dependencies
setup:
	@echo "Setting up Route Planner dependencies..."
	python setup.py

# Clean downloaded dependencies
clean:
	@echo "Cleaning up downloaded dependencies..."
	rm -rf static/lib/leaflet
	@echo "✓ Cleaned up"

# Run the server (requires OSM_FILE parameter)
run:
	@if [ -z "$(OSM_FILE)" ]; then \
		echo "Error: OSM_FILE parameter is required"; \
		echo "Usage: make run OSM_FILE=path/to/your/file.osm"; \
		exit 1; \
	fi
	@echo "Starting Route Planner server with $(OSM_FILE)..."
	PYTHONPATH=../../../python python -m examples.route_planner --osm $(OSM_FILE)

# Run with test OSM file
test:
	@echo "Creating test OSM file..."
	@mkdir -p ../../examples
	@echo '<?xml version="1.0" encoding="UTF-8"?>' > ../../examples/test.osm
	@echo '<osm version="0.6" generator="test">' >> ../../examples/test.osm
	@echo '  <node id="1" lat="47.6505" lon="-122.3033"/>' >> ../../examples/test.osm
	@echo '  <node id="2" lat="47.6515" lon="-122.3043"/>' >> ../../examples/test.osm
	@echo '  <way id="1">' >> ../../examples/test.osm
	@echo '    <nd ref="1"/>' >> ../../examples/test.osm
	@echo '    <nd ref="2"/>' >> ../../examples/test.osm
	@echo '    <tag k="highway" v="residential"/>' >> ../../examples/test.osm
	@echo '  </way>' >> ../../examples/test.osm
	@echo '</osm>' >> ../../examples/test.osm
	@echo "✓ Test OSM file created"
	@echo "Starting Route Planner server with test data..."
	PYTHONPATH=../../../python python -m examples.route_planner --osm ../../examples/test.osm