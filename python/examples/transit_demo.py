#!/usr/bin/env python3
"""Example usage of the transit provider for GTFS-based routing.

This example demonstrates how to use the TransitProvider for pathfinding
on transit networks using GTFS data.
"""

import tempfile
import time
import zipfile
from pathlib import Path

from graphserver import Engine, Vertex
from graphserver.providers import TransitProvider


def create_example_gtfs() -> Path:
    """Create a sample GTFS feed for demonstration."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    gtfs_zip = temp_dir / "example_transit.zip"
    
    # GTFS files content - a simple bus route
    agency_txt = """agency_id,agency_name,agency_url,agency_timezone
metro,Metro Transit,http://metro.example.com,America/New_York
"""
    
    stops_txt = """stop_id,stop_name,stop_lat,stop_lon
downtown,Downtown Station,40.7589,-73.9851
midtown,Midtown Plaza,40.7614,-73.9776
uptown,Uptown Center,40.7505,-73.9934
eastside,Eastside Mall,40.7505,-73.9600
"""
    
    routes_txt = """route_id,agency_id,route_short_name,route_long_name,route_type
red_line,metro,Red,Red Line Express,3
blue_line,metro,Blue,Blue Line Local,3
"""
    
    trips_txt = """route_id,service_id,trip_id,trip_headsign
red_line,weekday,red_trip_1,To Uptown
red_line,weekday,red_trip_2,To Downtown
blue_line,weekday,blue_trip_1,To Eastside
"""
    
    stop_times_txt = """trip_id,arrival_time,departure_time,stop_id,stop_sequence
red_trip_1,09:00:00,09:00:00,downtown,1
red_trip_1,09:05:00,09:05:00,midtown,2
red_trip_1,09:10:00,09:10:00,uptown,3
red_trip_2,09:30:00,09:30:00,uptown,1
red_trip_2,09:35:00,09:35:00,midtown,2
red_trip_2,09:40:00,09:40:00,downtown,3
blue_trip_1,09:15:00,09:15:00,downtown,1
blue_trip_1,09:20:00,09:20:00,midtown,2
blue_trip_1,09:30:00,09:30:00,eastside,3
"""
    
    calendar_txt = """service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
weekday,1,1,1,1,1,0,0,20240101,20241231
"""
    
    # Create zip file with GTFS data
    with zipfile.ZipFile(gtfs_zip, 'w') as zf:
        zf.writestr("agency.txt", agency_txt)
        zf.writestr("stops.txt", stops_txt)
        zf.writestr("routes.txt", routes_txt)
        zf.writestr("trips.txt", trips_txt)
        zf.writestr("stop_times.txt", stop_times_txt)
        zf.writestr("calendar.txt", calendar_txt)
    
    return gtfs_zip


def main() -> None:
    """Demonstrate transit provider usage."""
    print("🚌 Transit Provider Example")
    print("=" * 50)
    
    # Create example GTFS data
    print("📁 Creating example GTFS data...")
    gtfs_file = create_example_gtfs()
    
    try:
        # Initialize the transit provider
        print("🔧 Initializing transit provider...")
        provider = TransitProvider(gtfs_file)
        
        print(f"📊 Provider stats:")
        print(f"   • Stops: {provider.stop_count}")
        print(f"   • Routes: {provider.route_count}")
        print(f"   • Trips: {provider.trip_count}")
        
        # Create and register with engine
        print("🏗️  Setting up planning engine...")
        engine = Engine(enable_edge_caching=True)
        engine.register_provider("transit", provider)
        
        # Example 1: Coordinate to coordinate routing
        print("\\n🗺️  Example 1: Coordinate-based routing")
        print("-" * 40)
        
        # Start near downtown (at 8:55 AM)
        start_time = int(time.time()) - 3600  # 1 hour ago for demo
        start_vertex = Vertex({
            "lat": 40.7590,  # Near downtown stop
            "lon": -73.9850,
            "time": start_time
        })
        
        # Goal near uptown (flexible arrival time)
        goal_vertex = Vertex({
            "lat": 40.7506,  # Near uptown stop
            "lon": -73.9935,
            "time": start_time + 3600  # 1 hour later
        })
        
        print(f"Start: {start_vertex['lat']:.4f}, {start_vertex['lon']:.4f}")
        print(f"Goal:  {goal_vertex['lat']:.4f}, {goal_vertex['lon']:.4f}")
        
        # Example 2: Test edge expansion from coordinates
        print("\\n🔍 Example 2: Edge expansion from coordinates")
        print("-" * 40)
        
        coord_vertex = Vertex({
            "lat": 40.7589,  # Downtown coordinates
            "lon": -73.9851,
            "time": start_time
        })
        
        edges = provider(coord_vertex)
        print(f"Found {len(edges)} nearby stops:")
        for i, (target, edge) in enumerate(edges):
            stop_name = target.get("stop_name", "Unknown")
            distance = edge.get_metadata("distance_m", 0)
            walking_time = edge.get_metadata("walking_time_s", 0)
            print(f"  {i+1}. {stop_name} ({distance:.0f}m, {walking_time:.0f}s walk)")
        
        # Example 3: Test departures from a stop
        print("\\n🚌 Example 3: Departures from downtown stop")
        print("-" * 40)
        
        stop_vertex = Vertex({
            "stop_id": "downtown",
            "time": start_time
        })
        
        departure_edges = provider(stop_vertex)
        print(f"Found {len(departure_edges)} departures:")
        for i, (target, edge) in enumerate(departure_edges):
            trip_id = target.get("trip_id", "Unknown")
            route_id = target.get("route_id", "Unknown")
            departure_time = target.get("time", 0)
            waiting_time = edge.get_metadata("waiting_time_s", 0)
            print(f"  {i+1}. {route_id} (Trip: {trip_id}) - wait {waiting_time:.0f}s")
        
        # Example 4: Test vehicle state transitions
        print("\\n🎭 Example 4: Vehicle state transitions")
        print("-" * 40)
        
        # Boarding vertex
        boarding_vertex = Vertex({
            "time": start_time + 1800,  # 30 minutes later
            "trip_id": "red_trip_1",
            "stop_sequence": 1,
            "vehicle_state": "boarding",
            "stop_id": "downtown",
            "route_id": "red_line"
        })
        
        boarding_edges = provider(boarding_vertex)
        print(f"From boarding vertex: {len(boarding_edges)} transitions")
        for target, edge in boarding_edges:
            state = target.get("vehicle_state", "none")
            edge_type = edge.get_metadata("edge_type", "unknown")
            print(f"  → {state} state ({edge_type})")
        
        # Alright vertex  
        alright_vertex = Vertex({
            "time": start_time + 2100,  # 35 minutes later
            "trip_id": "red_trip_1",
            "stop_sequence": 2,
            "vehicle_state": "alright",
            "stop_id": "midtown",
            "route_id": "red_line"
        })
        
        alright_edges = provider(alright_vertex)
        print(f"From alright vertex: {len(alright_edges)} transitions")
        for target, edge in alright_edges:
            state = target.get("vehicle_state", "stop")
            edge_type = edge.get_metadata("edge_type", "unknown")
            stop_id = target.get("stop_id", "unknown")
            print(f"  → {state} at {stop_id} ({edge_type})")
        
        print("\\n✅ Transit provider example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("🧹 Cleaning up...")
        gtfs_file.unlink()
        gtfs_file.parent.rmdir()
        print("Done!")


if __name__ == "__main__":
    main()