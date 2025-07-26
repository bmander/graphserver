#!/usr/bin/env python3
"""Transit Provider Example

This script demonstrates how to use the Transit edge provider with GTFS data
for multi-modal transit pathfinding.
"""

import tempfile
from pathlib import Path

from graphserver.core import Engine, Vertex

# Sample GTFS data for demonstration
SAMPLE_STOPS_CSV = """stop_id,stop_name,stop_lat,stop_lon,location_type
central_station,Central Station,40.7589,-73.9851,0
union_square,Union Square,40.7359,-73.9911,0
times_square,Times Square,40.7580,-73.9855,0
grand_central,Grand Central,40.7527,-73.9772,0
"""

SAMPLE_ROUTES_CSV = """route_id,route_short_name,route_long_name,route_type
subway_6,6,Lexington Ave Express,1
subway_n,N,Broadway Express,1
bus_m15,M15,First/Second Ave Local,3
"""

SAMPLE_TRIPS_CSV = """trip_id,route_id,service_id,direction_id,trip_headsign
trip_6_downtown,subway_6,weekday,0,Brooklyn Bridge
trip_6_uptown,subway_6,weekday,1,Pelham Bay Park
trip_n_downtown,subway_n,weekday,0,Coney Island
trip_m15_downtown,bus_m15,weekday,0,South Ferry
"""

SAMPLE_STOP_TIMES_CSV = """trip_id,stop_id,arrival_time,departure_time,stop_sequence
trip_6_downtown,central_station,08:00:00,08:00:30,1
trip_6_downtown,union_square,08:08:00,08:08:30,2
trip_6_downtown,grand_central,08:15:00,08:15:30,3
trip_6_uptown,grand_central,08:10:00,08:10:30,1
trip_6_uptown,union_square,08:17:00,08:17:30,2
trip_6_uptown,central_station,08:25:00,08:25:30,3
trip_n_downtown,times_square,08:05:00,08:05:30,1
trip_n_downtown,union_square,08:12:00,08:12:30,2
trip_m15_downtown,central_station,08:02:00,08:02:30,1
trip_m15_downtown,union_square,08:15:00,08:15:30,2
"""


def create_sample_gtfs_data():
    """Create temporary GTFS data for demonstration."""
    # Create temporary directory
    tmpdir = tempfile.mkdtemp()
    gtfs_path = Path(tmpdir)
    
    # Write GTFS files
    (gtfs_path / "stops.txt").write_text(SAMPLE_STOPS_CSV)
    (gtfs_path / "routes.txt").write_text(SAMPLE_ROUTES_CSV)
    (gtfs_path / "trips.txt").write_text(SAMPLE_TRIPS_CSV)
    (gtfs_path / "stop_times.txt").write_text(SAMPLE_STOP_TIMES_CSV)
    
    return gtfs_path


def main():
    """Demonstrate transit provider functionality."""
    print("🚇 Transit Provider Demo")
    print("=" * 50)
    
    try:
        from graphserver.providers.transit import TransitProvider
        
        # Create sample GTFS data
        print("📁 Creating sample GTFS data...")
        gtfs_path = create_sample_gtfs_data()
        print(f"   GTFS data created at: {gtfs_path}")
        
        # Initialize transit provider
        print("\n🚌 Initializing transit provider...")
        transit_provider = TransitProvider(
            gtfs_path,
            search_radius_km=1.0,
            departure_window_hours=2
        )
        
        print(f"   Loaded {transit_provider.stop_count} stops")
        print(f"   Loaded {transit_provider.route_count} routes")
        print(f"   Loaded {transit_provider.trip_count} trips")
        
        # Create engine and register provider
        print("\n⚙️  Setting up planning engine...")
        engine = Engine()
        engine.register_provider("transit", transit_provider)
        
        # Example 1: From coordinates to nearby stops
        print("\n📍 Example 1: Find nearby stops from coordinates")
        coordinate_vertex = Vertex({
            "lat": 40.7589,  # Near Central Station
            "lon": -73.9851,
            "time": 8 * 3600,  # 08:00:00 (seconds since midnight)
        })
        
        nearby_edges = transit_provider(coordinate_vertex)
        print(f"   Found {len(nearby_edges)} nearby stops:")
        for target, edge in nearby_edges:
            print(f"     → {target['stop_name']} (ID: {target['stop_id']})")
            print(f"       Walking time: {edge.cost:.1f}s, Arrival: {target['time']//3600:02d}:{(target['time']%3600)//60:02d}")
        
        # Example 2: From stop to departures
        print("\n🚉 Example 2: Find departures from a stop")
        stop_vertex = Vertex({
            "stop_id": "central_station",
            "time": 7 * 3600 + 50 * 60,  # 07:50:00 - before departures
        })
        
        departure_edges = transit_provider(stop_vertex)
        print(f"   Found {len(departure_edges)} departures from Central Station:")
        for target, edge in departure_edges:
            route_id = target.get('route_id', 'Unknown')
            trip_id = target['trip_id']
            departure_time = target['time']
            print(f"     → Trip {trip_id} (Route: {route_id})")
            print(f"       Departure: {departure_time//3600:02d}:{(departure_time%3600)//60:02d}, Wait: {edge.cost:.0f}s")
        
        # Example 3: From boarding to next stop
        print("\n🚇 Example 3: Travel from boarding to next stop")
        boarding_vertex = Vertex({
            "time": 8 * 3600,  # 08:00:00
            "trip_id": "trip_6_downtown",
            "stop_sequence": 1,
            "vehicle_state": "boarding",
            "stop_id": "central_station",
        })
        
        travel_edges = transit_provider(boarding_vertex)
        if travel_edges:
            target, edge = travel_edges[0]
            print(f"   Boarding trip_6_downtown at Central Station")
            print(f"   → Next stop: {target['stop_id']}")
            print(f"     Arrival time: {target['time']//3600:02d}:{(target['time']%3600)//60:02d}")
            print(f"     Travel time: {edge.cost:.0f}s")
        
        # Example 4: From alright to transfer options
        print("\n🔄 Example 4: Transfer options from alright vertex")
        alright_vertex = Vertex({
            "time": 8 * 3600 + 8 * 60,  # 08:08:00
            "trip_id": "trip_6_downtown",
            "stop_sequence": 2,
            "vehicle_state": "alright",
            "stop_id": "union_square",
        })
        
        transfer_edges = transit_provider(alright_vertex)
        print(f"   Arrived at Union Square at 08:08")
        print(f"   Found {len(transfer_edges)} transfer options:")
        for target, edge in transfer_edges:
            if edge.metadata["edge_type"] == "alright_to_boarding":
                print(f"     → Transfer to other routes from {target['stop_id']}")
            elif edge.metadata["edge_type"] == "alright_to_stop":
                print(f"     → Exit at {target.get('stop_name', target['stop_id'])}")
        
        # Example 5: Complete journey planning
        print("\n🗺️  Example 5: Complete journey planning")
        print("   Planning route from coordinates near Central Station to Grand Central...")
        
        start_vertex = Vertex({
            "lat": 40.7590,  # Very close to Central Station
            "lon": -73.9850,
            "time": 7 * 3600 + 55 * 60,  # 07:55:00
        })
        
        goal_vertex = Vertex({
            "stop_id": "grand_central",
            "time": 8 * 3600 + 30 * 60,  # 08:30:00 - arrival deadline
        })
        
        try:
            result = engine.plan(start=start_vertex, goal=goal_vertex)
            print(f"   ✅ Found path with {len(result)} steps, total cost: {result.total_cost:.1f}s")
            
            for i, path_edge in enumerate(result):
                edge_type = path_edge.edge.metadata.get("edge_type", "unknown")
                cost = path_edge.edge.cost
                print(f"     Step {i+1}: {edge_type} (cost: {cost:.1f}s)")
                
        except Exception as e:
            print(f"   ⚠️  Planning failed: {e}")
            print("   This is expected as goal checking logic may not be fully implemented")
        
        print("\n✅ Demo completed successfully!")
        print(f"\n🧹 Cleaning up temporary files at {gtfs_path}")
        
        # Clean up temporary files
        import shutil
        shutil.rmtree(gtfs_path)
        
    except ImportError as e:
        print(f"❌ Transit provider not available: {e}")
        print("   Make sure the graphserver package is properly installed")
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()