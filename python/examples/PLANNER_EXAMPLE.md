# Route Planner Example Application

## Overview

A standalone web application that provides an interactive map-based interface for route planning using the graphserver engine. Users can click on the map to set start and end points, then request routing calculations that are processed by the graphserver backend.

## Architecture

### Directory Structure
```
python/examples/route_planner/
├── __init__.py
├── __main__.py          # Entry point for python -m route_planner
├── server.py            # HTTP server and request handlers
├── static/              # Static assets
│   ├── index.html       # Main HTML page
│   ├── style.css        # Application styles
│   ├── app.js           # JavaScript application logic
│   └── lib/             # Third-party libraries
│       └── leaflet/     # Map library files
├── templates/           # HTML templates if needed
└── README.md           # Usage documentation
```

## Core Components

### 1. Command Line Interface (`__main__.py`)
- Similar interface to graphserver-web
- Arguments:
  - `--port`: Server port (default: 8080)
  - `--osm`: OSM file path (required)
  - `--gtfs`: GTFS file paths (optional, multiple)
  - `--host`: Host to bind to (default: localhost)

Example usage:
```bash
python -m route_planner --osm examples/uw_campus.osm --port 8080
```

### 2. Web Server (`server.py`)
- Built on Python's http.server or a lightweight framework like Flask
- Endpoints:
  - `/` - Serve the main map interface
  - `/static/*` - Serve static assets
  - `/api/route` - POST endpoint for routing requests
  - `/api/providers` - GET endpoint to list available providers
  - `/api/bounds` - GET endpoint for map data bounds

### 3. Frontend Application (`static/app.js`)
- Interactive map using Leaflet.js (open-source, no API key required)
- Features:
  - Click to set origin point (green marker)
  - Click to set destination point (red marker)
  - Right-click to clear points
  - "Calculate Route" button
  - Route visualization on map
  - Route details panel (distance, time, steps)

### 4. Routing API (`/api/route`)

Request format:
```json
{
  "origin": {
    "lat": 47.65852,
    "lon": -122.30322
  },
  "destination": {
    "lat": 47.65500,
    "lon": -122.30900
  },
  "options": {
    "mode": "walk",  // walk, transit, bike
    "departure_time": 1234567890  // Unix timestamp (optional)
  }
}
```

Response format:
```json
{
  "success": true,
  "route": {
    "total_cost": 450.5,  // seconds
    "total_distance": 520.3,  // meters
    "geometry": {
      "type": "LineString",
      "coordinates": [[lon1, lat1], [lon2, lat2], ...]
    },
    "steps": [
      {
        "instruction": "Walk north on 15th Ave NE",
        "distance": 150.2,
        "duration": 120.5,
        "geometry": {...}
      }
    ]
  }
}
```

## Implementation Phases

### Phase 1: Basic Infrastructure
1. Create directory structure and module files
2. Implement command-line interface
3. Set up basic HTTP server
4. Create minimal HTML page with map

### Phase 2: Map Interface
1. Integrate Leaflet.js for map display
2. Implement click handlers for origin/destination selection
3. Add visual markers and UI controls
4. Set initial map bounds based on OSM data

### Phase 3: Routing Integration
1. Initialize graphserver engine with OSM/GTFS data
2. Implement `/api/route` endpoint
3. Convert lat/lon clicks to vertices
4. Run shortest path calculation
5. Convert path result to GeoJSON

### Phase 4: Route Visualization
1. Display route geometry on map
2. Show turn-by-turn directions
3. Add route statistics (time, distance)
4. Handle routing errors gracefully

### Phase 5: Enhancements
1. Support for different routing modes
2. Time-based routing for transit
3. Draggable markers for route adjustment
4. Route alternatives
5. Elevation profile (if data available)

## Key Technical Decisions

### Map Library: Leaflet.js
- Open source, no API keys required
- Lightweight and mobile-friendly
- Extensive plugin ecosystem
- Good documentation

### Routing Engine Integration
- Reuse graphserver.Engine from parent package
- Provider initialization similar to graphserver-web
- Efficient vertex lookup using spatial indices

### Coordinate System
- Store all coordinates in WGS84 (lat/lon)
- Convert to appropriate projection for display
- Use graphserver's spatial utilities

### Error Handling
- Graceful fallbacks for routing failures
- User-friendly error messages
- Validation of click locations

## Development Steps

1. **Create Module Structure**
   ```bash
   mkdir -p python/examples/route_planner/static/lib
   touch python/examples/route_planner/{__init__.py,__main__.py,server.py}
   ```

2. **Download Leaflet.js**
   - Download Leaflet CSS and JS files
   - Place in static/lib/leaflet/

3. **Implement Basic Server**
   - Start with minimal HTTP server
   - Serve static files
   - Add CORS headers for development

4. **Create Map Interface**
   - Basic HTML with map container
   - Initialize Leaflet map
   - Add tile layer (OpenStreetMap)

5. **Add Routing Logic**
   - Initialize graphserver engine
   - Implement coordinate-to-vertex lookup
   - Calculate shortest path
   - Convert to GeoJSON

## Example Code Structure

### `__main__.py`
```python
"""Route planner web application entry point."""
import argparse
from .server import RoutePlannerServer

def main():
    parser = argparse.ArgumentParser(description="Interactive route planner")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--osm", required=True, help="OSM file path")
    parser.add_argument("--gtfs", action="append", help="GTFS file paths")
    
    args = parser.parse_args()
    
    server = RoutePlannerServer(
        port=args.port,
        osm_file=args.osm,
        gtfs_files=args.gtfs
    )
    server.run()

if __name__ == "__main__":
    main()
```

### `static/index.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Route Planner</title>
    <link rel="stylesheet" href="/static/lib/leaflet/leaflet.css" />
    <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
    <div id="map"></div>
    <div id="controls">
        <button id="calculate-route">Calculate Route</button>
        <button id="clear-route">Clear</button>
    </div>
    <div id="route-info"></div>
    
    <script src="/static/lib/leaflet/leaflet.js"></script>
    <script src="/static/app.js"></script>
</body>
</html>
```

## Testing Strategy

1. **Unit Tests**
   - Routing calculations
   - Coordinate conversions
   - API response formatting

2. **Integration Tests**
   - End-to-end routing requests
   - Map interaction workflows
   - Error scenarios

3. **Manual Testing**
   - Visual route verification
   - Performance with large graphs
   - Mobile responsiveness

## Future Enhancements

1. **Multi-modal routing** - Combine walk + transit
2. **Route preferences** - Fastest, shortest, scenic
3. **Accessibility routing** - Avoid stairs, steep hills
4. **Real-time updates** - Live transit data
5. **Route sharing** - Permalink generation
6. **Offline support** - Service workers for PWA