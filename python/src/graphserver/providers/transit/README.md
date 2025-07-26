# Transit Edge Provider

The Transit Edge Provider enables pathfinding on public transit networks using GTFS (General Transit Feed Specification) data. It implements dynamic edge expansion for multi-modal journey planning.

## Overview

The transit provider supports transit routing with the following vertex types and expansion rules:

1. **Geographic coordinates with time** `{lat, lon, time}` → **Stop vertices** with arrival times
2. **Stop vertices** `{stop_id}` → **Boarding vertices** representing vehicle departures  
3. **Boarding vertices** `{trip_id, stop_sequence, vehicle_state: "boarding"}` → **Alright vertices** at the next stop
4. **Alright vertices** `{trip_id, stop_sequence, vehicle_state: "alright"}` → **Transfer options** (boarding + stop vertices)

## Usage

### Basic Setup

```python
from graphserver.core import Engine
from graphserver.providers.transit import TransitProvider

# Initialize with GTFS data
transit_provider = TransitProvider(
    gtfs_path="/path/to/gtfs/directory",
    search_radius_km=0.5,           # Radius for finding nearby stops
    departure_window_hours=2,       # Hours to look ahead for departures
    walking_speed_ms=1.2,          # Walking speed in m/s
    max_nearby_stops=10            # Max stops to consider from coordinates
)

# Register with planning engine
engine = Engine()
engine.register_provider("transit", transit_provider)
```

### Edge Expansion Examples

#### 1. Coordinates → Nearby Stops
```python
start_vertex = Vertex({
    "lat": 40.7589,                # Latitude
    "lon": -73.9851,               # Longitude  
    "time": 8 * 3600               # 08:00:00 (seconds since midnight)
})

edges = transit_provider(start_vertex)
# Returns edges to nearby stops with walking times and arrival times
```

#### 2. Stop → Vehicle Departures
```python
stop_vertex = Vertex({
    "stop_id": "station_123",
    "time": 8 * 3600              # Current time
})

edges = transit_provider(stop_vertex)
# Returns boarding vertices for departures in the next 2 hours
```

#### 3. Boarding → Travel to Next Stop
```python
boarding_vertex = Vertex({
    "time": 28800,                 # Departure time
    "trip_id": "trip_456",
    "stop_sequence": 1,
    "vehicle_state": "boarding",
    "stop_id": "station_123"
})

edges = transit_provider(boarding_vertex)
# Returns alright vertex at the next stop on the trip
```

#### 4. Alright → Transfer Options
```python
alright_vertex = Vertex({
    "time": 29100,                 # Arrival time
    "trip_id": "trip_456", 
    "stop_sequence": 2,
    "vehicle_state": "alright",
    "stop_id": "station_456"
})

edges = transit_provider(alright_vertex)
# Returns transfer to other routes + option to exit station
```

### Complete Journey Planning

```python
# Plan a multi-modal journey
start = Vertex({
    "lat": 40.7589,
    "lon": -73.9851, 
    "time": 8 * 3600
})

goal = Vertex({
    "stop_id": "destination_station"
})

result = engine.plan(start=start, goal=goal)
```

## GTFS Data Requirements

The provider requires standard GTFS files in the specified directory:

- `stops.txt` - Transit stops/stations
- `routes.txt` - Transit routes  
- `trips.txt` - Individual trip instances
- `stop_times.txt` - Scheduled arrival/departure times

### Example GTFS Files

**stops.txt:**
```csv
stop_id,stop_name,stop_lat,stop_lon,location_type
station_1,Main Street Station,40.7589,-73.9851,0
station_2,Central Plaza,40.7614,-73.9776,0
```

**routes.txt:**
```csv
route_id,route_short_name,route_long_name,route_type
route_1,6,Lexington Ave Express,1
route_2,M15,First/Second Avenue Local,3
```

**trips.txt:**
```csv
trip_id,route_id,service_id,direction_id,trip_headsign
trip_1,route_1,weekday,0,Downtown
trip_2,route_1,weekday,1,Uptown
```

**stop_times.txt:**
```csv
trip_id,stop_id,arrival_time,departure_time,stop_sequence
trip_1,station_1,08:00:00,08:00:30,1
trip_1,station_2,08:05:00,08:05:30,2
```

## Time Representation

Times are represented as seconds since midnight:
- `8 * 3600 = 28800` represents 08:00:00
- `8 * 3600 + 30 * 60 = 30600` represents 08:30:00

## Configuration Options

- **search_radius_km**: Maximum distance to search for nearby stops from coordinates
- **departure_window_hours**: How far ahead to look for vehicle departures 
- **walking_speed_ms**: Walking speed for coordinate-to-stop connections
- **max_nearby_stops**: Maximum number of nearby stops to consider

## Features

- **Time-based scheduling**: Respects actual transit timetables
- **Multi-modal support**: Handles different transit modes (bus, rail, etc.)
- **Transfer planning**: Supports transfers between routes
- **Efficient spatial queries**: Fast lookup of nearby stops
- **Robust parsing**: Handles various GTFS format variations
- **Rich metadata**: Detailed edge information for analysis

## Testing

Run the test suite:
```bash
python -m pytest tests/test_transit_provider.py -v
```

Run the demo:
```bash
python examples/transit_demo.py
```

## Limitations

- Requires properly formatted GTFS data
- Service calendars are not currently implemented (assumes all trips run daily)
- Real-time updates are not supported
- Fare calculation is not included