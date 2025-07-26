# Graph Web Browser Implementation Plan

## Status
- ✅ **Phase 1 Complete**: Basic HTTP server with query parsing and HTML responses
- ✅ **Phase 2 Complete**: Provider integration (OSM, GTFS) with real edge discovery
- 🔄 **Phase 3 In Progress**: Enhanced response generation
- ⏳ **Phase 4 Planned**: Additional features and enhancements

## Overview
Build a simple HTTP web server that provides a browser-based interface for exploring graph vertices and edges. The server exposes a single endpoint that accepts vertex properties as query parameters and returns clickable links to adjacent vertices.

## Core Requirements
1. Single GET "/" endpoint
2. Query parameters define vertex key/value pairs
3. Response shows outbound edges as HTML links
4. Command-line arguments specify edge providers (--osm, --gtfs)
5. Use only Python's built-in http.server module
6. Automatic type inference for values (float, int, string)

## Architecture

### Components

#### 1. HTTP Server (`graphserver_web.py`)
- Built on `http.server.HTTPServer` and `BaseHTTPRequestHandler`
- Parse query parameters into vertex properties
- Format response as HTML with links
- Handle errors gracefully

#### 2. Query Parameter Parser
- Extract key=value pairs from URL query string
- Type inference logic:
  - Try float first (e.g., "1.2" → 1.2)
  - Try int if not float (e.g., "3" → 3)
  - Default to string (e.g., "foo" → "foo")
- Handle URL encoding/decoding

#### 3. Edge Provider Manager
- Initialize providers based on command-line arguments
- Map provider types to vertex patterns
- Register all providers with the engine

#### 4. Response Formatter
- Generate HTML response with:
  - Current vertex properties
  - List of outbound edges
  - Links to adjacent vertices
  - Edge metadata (cost, properties)

## Implementation Details

### URL Structure
```
# Root endpoint shows usage
GET /

# Vertex with coordinates
GET /?lat=47.6&lon=-122.3

# OSM node
GET /?osm_node_id=12345

# Transit stop with time
GET /?stop_id=STOP123&time=1234567890

# Mixed types
GET /?lat=47.6&lon=-122.3&mode=walk
```

### Response Format
```html
<!DOCTYPE html>
<html>
<head>
    <title>Graph Browser</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        .vertex { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
        .edges { margin-left: 20px; }
        .edge { margin: 5px 0; }
        .link { color: blue; text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Graph Browser</h1>
    
    <div class="vertex">
        <h2>Current Vertex</h2>
        <pre>{
    "lat": 47.6,
    "lon": -122.3
}</pre>
    </div>
    
    <div class="edges">
        <h2>Outbound Edges (3 found)</h2>
        
        <div class="edge">
            → <a href="/?osm_node_id=12345" class="link">{"osm_node_id": 12345}</a>
            <small>(cost: 150.5m)</small>
        </div>
        
        <div class="edge">
            → <a href="/?osm_node_id=67890" class="link">{"osm_node_id": 67890}</a>
            <small>(cost: 200.3m)</small>
        </div>
        
        <div class="edge">
            → <a href="/?stop_id=STOP123&time=1234567890" class="link">{"stop_id": "STOP123", "time": 1234567890}</a>
            <small>(walk to transit stop, cost: 300m)</small>
        </div>
    </div>
</body>
</html>
```

### Command-Line Interface
```bash
# OSM-only routing
python graphserver_web.py --osm map.osm --port 8080

# Transit routing with GTFS
python graphserver_web.py --gtfs transit.zip --port 8080

# Combined OSM + Transit
python graphserver_web.py --osm map.osm --gtfs transit.zip --port 8080

# Multiple GTFS feeds
python graphserver_web.py --gtfs feed1.zip --gtfs feed2.zip --port 8080
```

### Provider Selection Logic
1. **OSM Providers** (when --osm is specified):
   - `OSMNetworkProvider`: For vertices with `osm_node_id`
   - `OSMAccessProvider`: For vertices with `lat` and `lon`

2. **Transit Provider** (when --gtfs is specified):
   - Handles vertices with:
     - `lat`, `lon`, and `time`
     - `stop_id` and `time`
     - `vehicle_state` and related fields

3. **Provider Registration Strategy**:
   - Register providers in order of specificity
   - More specific patterns first (e.g., transit before OSM access)
   - Engine will try providers in registration order

### Error Handling
1. **Invalid Query Parameters**:
   - Show helpful error message
   - Provide example URLs

2. **No Edges Found**:
   - Display message: "No outbound edges from this vertex"
   - Suggest trying different parameters

3. **Provider Initialization Errors**:
   - Clear error messages for missing files
   - Validation of file formats

4. **Type Conversion Errors**:
   - Gracefully handle malformed values
   - Default to string type

## Implementation Steps

### Phase 1: Basic HTTP Server ✅ COMPLETED
1. ✅ Create `graphserver_web.py` with basic HTTP server
2. ✅ Implement query parameter parsing with type inference
3. ✅ Create simple HTML response template
4. ✅ Add command-line argument parsing

### Phase 2: Provider Integration ✅ COMPLETED
1. ✅ Initialize providers based on CLI arguments
2. ✅ Create vertex from query parameters
3. ✅ Register providers with engine
4. ✅ Get edges from providers for current vertex

### Phase 3: Response Generation
1. Format vertex properties as JSON
2. Generate HTML links for adjacent vertices
3. Include edge metadata (cost, properties)
4. Add CSS styling for readability

### Phase 4: Enhancement
1. ✅ Add usage instructions on root page
2. Implement breadcrumb navigation
3. Add vertex property validation
4. Include provider statistics

## Example Usage Flow

1. **Start Server**:
   ```bash
   python graphserver_web.py --osm seattle.osm --port 8080
   ```

2. **Browse to Root**:
   - Navigate to http://localhost:8080/
   - See usage instructions and example links

3. **Explore from Coordinate**:
   - Click example or enter: http://localhost:8080/?lat=47.6&lon=-122.3
   - See edges to nearby OSM nodes

4. **Follow Edge**:
   - Click on edge link: http://localhost:8080/?osm_node_id=12345
   - See edges from that OSM node to connected nodes

5. **Continue Exploration**:
   - Keep clicking edges to traverse the graph
   - Use browser back button to return to previous vertices

## Technical Considerations

### Performance
- Engine edge caching enabled by default
- Limit number of edges displayed (configurable)
- Efficient HTML generation

### Security
- Validate and sanitize all query parameters
- Escape HTML in vertex properties
- Use URL encoding for links

### Extensibility
- Easy to add new providers via CLI arguments
- Provider detection based on vertex properties
- Modular design for future enhancements

## Future Enhancements (Not in Initial Scope)
- Visualization of vertex on map
- Path planning between two vertices
- Edge filtering options
- JSON API endpoint
- WebSocket support for real-time updates
- Caching of frequently accessed vertices