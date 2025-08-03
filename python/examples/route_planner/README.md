# Route Planner Example

An interactive web-based route planning application using the Graphserver engine. This example demonstrates how to build a complete mapping application with route calculation capabilities.

## Overview

The Route Planner provides a modern web interface for calculating routes using OSM and GTFS data. Users can click on an interactive map to set origin and destination points, then request route calculations that are processed by the graphserver backend.

## Features

- 🗺️ Interactive map interface (Leaflet.js)
- 📍 Click-to-set route endpoints
- 🚶 Walking route calculation
- 🚌 Transit route planning (with GTFS data)
- 📱 Mobile-responsive design
- 🔄 Real-time server status monitoring

## Installation

### 1. Install Graphserver

This example requires the graphserver package to be installed:

```bash
cd python
pip install -e .
```

### 2. Setup Route Planner Dependencies

Run the setup script to download required JavaScript libraries:

```bash
cd python/examples/route_planner
python setup.py
```

This will automatically download:
- Leaflet.js v1.9.4 (map library)
- Leaflet CSS and marker icons
- All required assets for the web interface

**Alternative Manual Setup:**
If the setup script fails, you can manually download the files:
```bash
mkdir -p static/lib/leaflet/images
curl -o static/lib/leaflet/leaflet.css https://unpkg.com/leaflet@1.9.4/dist/leaflet.css
curl -o static/lib/leaflet/leaflet.js https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
curl -o static/lib/leaflet/images/marker-icon.png https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png
curl -o static/lib/leaflet/images/marker-shadow.png https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png
```

## Usage

### Quick Start

1. **Setup dependencies** (one-time setup):
   ```bash
   cd python/examples/route_planner
   python setup.py
   ```

2. **Run the application**:
   ```bash
   export PYTHONPATH=python
   python -m examples.route_planner --osm examples/uw_campus.osm
   ```

3. **Open your browser** to http://localhost:8080 and start clicking on the map!

### Basic Usage

Run the route planner with an OSM file:

```bash
export PYTHONPATH=python
python -m examples.route_planner --osm examples/uw_campus.osm
```

### With Transit Data

Include GTFS transit data for multimodal routing:

```bash
python -m route_planner --osm city.osm --gtfs transit.zip
```

### Multiple GTFS Files

You can specify multiple GTFS files:

```bash
python -m route_planner --osm city.osm --gtfs bus.zip --gtfs rail.zip
```

### Custom Port and Host

```bash
python -m route_planner --osm city.osm --port 8080 --host 0.0.0.0
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--osm FILE` | OSM file path (required) | - |
| `--gtfs FILE` | GTFS file path (repeatable) | - |
| `--port PORT` | Server port | 8080 |
| `--host HOST` | Host to bind to | localhost |

## API Endpoints

The server provides the following API endpoints:

### GET /api/status
Returns server status and configuration information.

**Response:**
```json
{
  "status": "ok",
  "message": "Route planner is running",
  "config": {
    "osm_file": "examples/uw_campus.osm",
    "gtfs_files": ["transit.zip"]
  }
}
```

### Future Endpoints (Phase 3+)

- `POST /api/route` - Calculate routes between points
- `GET /api/providers` - List available data providers
- `GET /api/bounds` - Get map bounds from OSM data

## Development Phases

### Phase 1: Basic Infrastructure ✅
- Command-line interface
- HTTP server with static file serving
- Basic HTML/CSS interface
- Server status monitoring

### Phase 2: Map Interface (Next)
- Leaflet.js integration
- Interactive map with click handlers
- Marker placement for origin/destination
- Map bounds from OSM data

### Phase 3: Routing Integration
- Graphserver engine initialization
- Route calculation API
- Path result visualization
- Turn-by-turn directions

### Phase 4: Enhanced Features
- Multiple routing modes
- Time-based transit routing
- Route alternatives
- Mobile optimizations

## Project Structure

```
route_planner/
├── __init__.py          # Package initialization
├── __main__.py          # CLI entry point
├── server.py            # HTTP server implementation
├── static/              # Frontend assets
│   ├── index.html       # Main application page
│   ├── style.css        # Application styles
│   └── lib/             # Third-party libraries
└── README.md            # This file
```

## Browser Compatibility

The application is tested with:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

This is an example application demonstrating graphserver usage. For contributions to the core graphserver library, please see the main project repository.

## License

This example follows the same license as the graphserver project.

## Troubleshooting

### Port Already in Use
If you get a "port already in use" error, try a different port:
```bash
python -m route_planner --osm your_file.osm --port 8081
```

### File Not Found
Ensure your OSM and GTFS files exist and are readable:
```bash
ls -la examples/uw_campus.osm
```

### Browser Connection Issues
- Check that the server is running without errors
- Verify the port number in your browser URL
- Check for firewall restrictions if accessing from another machine

### Performance Issues
For large OSM files, the initial server startup may take time as data is loaded and indexed. This is normal and only happens once per server start.