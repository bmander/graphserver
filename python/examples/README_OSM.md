# OpenStreetMap Provider for Graphserver

This example demonstrates how to use the OpenStreetMap (OSM) edge provider for pedestrian pathfinding with the Graphserver planning engine.

## Installation

Install Graphserver with OSM support:

```bash
pip install graphserver[osm]
```

This will install the required dependencies:
- `pyosmium>=4.0.2` - Efficient OSM data parsing
- `shapely>=2.0` - Geometric operations
- `pyproj>=3.7` - Accurate geodesic distance calculations
- `rtree>=1.4.0` - Spatial indexing for fast queries

## Getting OSM Data

Download OpenStreetMap data for your area of interest:

1. Visit [openstreetmap.org/export](https://www.openstreetmap.org/export)
2. Select your area of interest
3. Choose "OpenStreetMap XML Data" and download the `.osm` file
4. For larger areas, consider using [Overpass API](https://overpass-api.de/) or [BBBike extracts](https://extract.bbbike.org/)

## Usage

### Basic Example

```python
from graphserver import Engine, Vertex
from graphserver.providers.osm import OSMDataSource, OSMNetworkProvider, OSMAccessProvider

# Load OSM data once
osm_data = OSMDataSource("data/your_area.osm")

# Create providers using shared data source
osm_network = OSMNetworkProvider(osm_data)
osm_access = OSMAccessProvider(osm_data)

# Create planning engine
engine = Engine()
engine.register_provider("osm_network", osm_network)
engine.register_provider("osm_access", osm_access)

# Create vertices for start and goal coordinates
start = Vertex({"lat": 47.6062, "lon": -122.3321})
goal = Vertex({"lat": 47.6205, "lon": -122.3493})

# Link vertices to OSM network
osm_access.link(start, 47.6062, -122.3321)
osm_access.link(goal, 47.6205, -122.3493)

# Plan route between coordinates
result = engine.plan(start=start, goal=goal)
```

### Vertex Types

The OSM providers support two types of input vertices:

1. **Geographic coordinates**: `{"lat": float, "lon": float}`
   - Handled by OSMAccessProvider
   - Finds nearby OSM nodes within search radius
   - Generates edges from coordinates to OSM nodes

2. **OSM node IDs**: `{"osm_node_id": int}`
   - Handled by OSMNetworkProvider
   - Returns edges to all connected nodes in the walkable network
   - Uses actual OSM way data for routing

### Walking Profile Configuration

Customize pedestrian routing behavior:

```python
from graphserver.providers.osm import OSMDataSource
from graphserver.providers.osm.types import WalkingProfile

profile = WalkingProfile(
    base_speed_ms=1.4,        # Walking speed (m/s)
    avoid_stairs=False,       # Allow/avoid stairs
    avoid_busy_roads=True,    # Prefer dedicated pedestrian paths
    max_detour_factor=1.5     # Maximum detour tolerance
)

# Create data source with custom walking profile
osm_data = OSMDataSource("data.osm", walking_profile=profile)
```

### Provider Configuration

Adjust spatial search parameters:

```python
# Create data source with spatial indexing
osm_data = OSMDataSource("data.osm", build_spatial_index=True)

# Create access provider with custom search parameters
osm_access = OSMAccessProvider(
    osm_data,
    search_radius_m=200.0,    # Search radius for coordinate queries
    max_nearby_nodes=5,       # Max nodes to consider from coordinates
)
```

## Performance Tips

1. **Use spatial indexing**: Keep `build_spatial_index=True` in OSMDataSource for coordinate-based queries
2. **Share data source**: Create one OSMDataSource and pass it to multiple providers to avoid redundant parsing
3. **Adjust search radius**: Larger radius finds more options but slower queries
4. **Limit nearby nodes**: Reduce `max_nearby_nodes` for faster coordinate queries
5. **Filter OSM data**: Use smaller OSM extracts for faster loading

## Supported OSM Highway Types

The provider automatically detects walkable ways based on OSM highway tags:

- **Primary walkable**: `footway`, `path`, `steps`, `pedestrian`, `living_street`
- **Secondary walkable**: `residential`, `unclassified`, `service`, `track`
- **Roads with sidewalks**: `primary`, `secondary`, `tertiary` (if `sidewalk` tag present)

Access restrictions (`foot=no`, `access=no`) are respected.

## Example Script

Run the complete example:

```bash
python examples/osm_routing_example.py data/your_area.osm
```

This demonstrates:
- Loading OSM data and building spatial index
- Finding nearest nodes to coordinates
- Generating edges from different vertex types
- Pathfinding between coordinates

## Limitations

- Currently supports pedestrian routing only
- Limited to OSM XML/PBF formats (via PyOsmium)
- Path quality depends on OSM data completeness
- Large datasets may require significant memory

## Future Enhancements

Potential improvements for the OSM provider:

- Vehicle routing support (cars, bicycles)
- Route optimization (shortest vs. fastest)
- Real-time traffic integration
- Multi-modal routing (walking + transit)
- Turn restrictions and routing preferences
- Elevation-aware routing