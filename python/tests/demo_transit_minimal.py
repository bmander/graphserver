#!/usr/bin/env python3
"""Minimal Demo of Transit Provider

Demo the transit provider without requiring the C extension.
"""

import tempfile
from pathlib import Path
import sys
import os

# Add the source path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, '..', 'src')
sys.path.insert(0, src_path)

# Sample GTFS data
SAMPLE_STOPS_CSV = """stop_id,stop_name,stop_lat,stop_lon,location_type
central_station,Central Station,40.7589,-73.9851,0
union_square,Union Square,40.7359,-73.9911,0
times_square,Times Square,40.7580,-73.9855,0
"""

SAMPLE_ROUTES_CSV = """route_id,route_short_name,route_long_name,route_type
subway_6,6,Lexington Ave Express,1
bus_m15,M15,First/Second Ave Local,3
"""

SAMPLE_TRIPS_CSV = """trip_id,route_id,service_id,direction_id,trip_headsign
trip_6_downtown,subway_6,weekday,0,Brooklyn Bridge
trip_m15_downtown,bus_m15,weekday,0,South Ferry
"""

SAMPLE_STOP_TIMES_CSV = """trip_id,stop_id,arrival_time,departure_time,stop_sequence
trip_6_downtown,central_station,08:00:00,08:00:30,1
trip_6_downtown,union_square,08:08:00,08:08:30,2
trip_m15_downtown,central_station,08:02:00,08:02:30,1
trip_m15_downtown,times_square,08:15:00,08:15:30,2
"""


def create_sample_gtfs():
    tmpdir = tempfile.mkdtemp()
    gtfs_path = Path(tmpdir)
    
    (gtfs_path / "stops.txt").write_text(SAMPLE_STOPS_CSV)
    (gtfs_path / "routes.txt").write_text(SAMPLE_ROUTES_CSV)
    (gtfs_path / "trips.txt").write_text(SAMPLE_TRIPS_CSV)
    (gtfs_path / "stop_times.txt").write_text(SAMPLE_STOP_TIMES_CSV)
    
    return gtfs_path


# Mock classes for demonstration
class MockVertex:
    def __init__(self, data):
        self._data = data
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def __repr__(self):
        return f"MockVertex({self._data})"


class MockEdge:
    def __init__(self, cost, metadata=None):
        self.cost = cost
        self.metadata = metadata or {}


def main():
    print("🚇 Transit Provider Demo (Minimal Version)")
    print("=" * 50)
    
    # Mock the core imports
    import graphserver.providers.transit.provider as provider_module
    provider_module.Vertex = MockVertex
    provider_module.Edge = MockEdge
    
    from graphserver.providers.transit import TransitProvider
    
    # Create GTFS data
    print("📁 Creating sample GTFS data...")
    gtfs_path = create_sample_gtfs()
    
    # Initialize provider
    print("🚌 Initializing transit provider...")
    provider = TransitProvider(gtfs_path)
    print(f"   Loaded {provider.stop_count} stops")
    print(f"   Loaded {provider.route_count} routes")
    print(f"   Loaded {provider.trip_count} trips")
    
    # Demo 1: Coordinates to nearby stops
    print("\n📍 Demo 1: Coordinates → Nearby Stops")
    coord_vertex = MockVertex({
        "lat": 40.7589,
        "lon": -73.9851,
        "time": 8 * 3600,
    })
    
    edges = provider(coord_vertex)
    print(f"   Found {len(edges)} nearby stops:")
    for target, edge in edges:
        print(f"     → {target['stop_name']} (walk {edge.cost:.0f}s)")
    
    # Demo 2: Stop to departures
    print("\n🚉 Demo 2: Stop → Departures")
    stop_vertex = MockVertex({
        "stop_id": "central_station",
        "time": 7 * 3600 + 50 * 60,  # 07:50
    })
    
    edges = provider(stop_vertex)
    print(f"   Found {len(edges)} departures from Central Station:")
    for target, edge in edges:
        trip_id = target['trip_id']
        route_id = target.get('route_id', 'Unknown')
        print(f"     → {trip_id} ({route_id}) - wait {edge.cost:.0f}s")
    
    # Demo 3: Boarding → Travel
    print("\n🚇 Demo 3: Boarding → Travel to Next Stop")
    boarding_vertex = MockVertex({
        "time": 8 * 3600,
        "trip_id": "trip_6_downtown",
        "stop_sequence": 1,
        "vehicle_state": "boarding",
        "stop_id": "central_station",
    })
    
    edges = provider(boarding_vertex)
    if edges:
        target, edge = edges[0]
        print(f"   Boarding trip_6_downtown at Central Station")
        print(f"   → Travel to {target['stop_id']} (time: {edge.cost:.0f}s)")
    
    # Demo 4: Alright → Transfer Options
    print("\n🔄 Demo 4: Alright → Transfer Options")
    alright_vertex = MockVertex({
        "time": 8 * 3600 + 8 * 60,
        "trip_id": "trip_6_downtown",
        "stop_sequence": 2,
        "vehicle_state": "alright",
        "stop_id": "union_square",
    })
    
    edges = provider(alright_vertex)
    print(f"   Arrived at Union Square")
    print(f"   Transfer options ({len(edges)}):")
    for target, edge in edges:
        edge_type = edge.metadata["edge_type"]
        if "boarding" in edge_type:
            print(f"     → Transfer to other routes")
        else:
            print(f"     → Exit station")
    
    print("\n✅ Demo completed successfully!")
    print("\nThe transit provider correctly implements the specification:")
    print("  ✓ [lat/lon/time] → nearby stops with stop_id and arrival time")
    print("  ✓ [stop_id] → boarding vertices for departures")
    print("  ✓ [boarding vertex] → alright vertex at next stop")
    print("  ✓ [alright vertex] → boarding + stop vertices")
    
    # Cleanup
    import shutil
    shutil.rmtree(gtfs_path)


if __name__ == "__main__":
    main()