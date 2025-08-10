#!/usr/bin/env python3
"""
OSM-based Profiling Script for GraphServer Core Routing Algorithm

This script uses the UW Campus OSM data to create realistic routing scenarios
that exercise the core C routing functions. It focuses on profiling the C
implementation by measuring performance at the C layer while leveraging
Python's OSM parsing capabilities.

Usage:
    python profile_osm_routing.py [num_routes] [repetitions]
    
Examples:
    python profile_osm_routing.py                 # Default: 20 routes, 3 repetitions
    python profile_osm_routing.py 50 5           # 50 routes, 5 repetitions
    
Requirements:
    pip install graphserver[osm]
"""

import argparse
import cProfile
import pstats
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
    from graphserver.providers.osm.types import WalkingProfile
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Please install with: pip install graphserver[osm]")
    sys.exit(1)


class RoutingProfiler:
    """Profiler for core GraphServer routing functions using real OSM data."""
    
    def __init__(self, osm_file: Path):
        self.osm_file = osm_file
        self.engine = None
        self.network_provider = None
        self.access_provider = None
        
        # Performance tracking
        self.route_times: List[float] = []
        self.successful_routes = 0
        self.total_vertices_expanded = 0
        self.total_edges_generated = 0
        self.memory_usage = []
        
        # UW Campus coordinate pairs for realistic routing
        self.campus_routes = [
            # Main campus routes with known connectivity
            ((47.6590651, -122.3043738), (47.6591000, -122.3043000)),  # Central area
            ((47.6588000, -122.3045000), (47.6593000, -122.3040000)),  # Engineering to Union
            ((47.6585000, -122.3050000), (47.6595000, -122.3035000)),  # Science to Admin
            ((47.6583000, -122.3055000), (47.6597000, -122.3030000)),  # Arts to Sports
            ((47.6580000, -122.3060000), (47.6600000, -122.3025000)),  # Parking to North
            ((47.6575000, -122.3065000), (47.6605000, -122.3020000)),  # South to Research
            ((47.6570000, -122.3070000), (47.6610000, -122.3015000)),  # Dorm to Conference
            ((47.6565000, -122.3075000), (47.6590651, -122.3043738)),  # Medical to Central
            
            # Reverse routes for testing bidirectionality
            ((47.6591000, -122.3043000), (47.6590651, -122.3043738)),  # Central area reverse
            ((47.6593000, -122.3040000), (47.6588000, -122.3045000)),  # Union to Engineering
            ((47.6595000, -122.3035000), (47.6585000, -122.3050000)),  # Admin to Science
            ((47.6597000, -122.3030000), (47.6583000, -122.3055000)),  # Sports to Arts
            
            # Longer distance routes across campus
            ((47.6565000, -122.3075000), (47.6610000, -122.3015000)),  # Medical to Conference
            ((47.6570000, -122.3070000), (47.6600000, -122.3025000)),  # Dorm to North Gate
            ((47.6575000, -122.3065000), (47.6597000, -122.3030000)),  # South to Sports
            ((47.6580000, -122.3060000), (47.6605000, -122.3020000)),  # Parking to Research
            
            # Cross-campus diagonal routes
            ((47.6565000, -122.3075000), (47.6605000, -122.3020000)),  # SW to NE
            ((47.6570000, -122.3070000), (47.6597000, -122.3030000)),  # SW to NE
            ((47.6610000, -122.3015000), (47.6575000, -122.3065000)),  # NE to SW
            ((47.6600000, -122.3025000), (47.6580000, -122.3060000)),  # N to S
        ]
    
    def setup_engine(self) -> bool:
        """Initialize the GraphServer engine with OSM providers."""
        print(f"🏗️  Loading OSM data from {self.osm_file}...")
        
        try:
            start_time = time.time()
            
            # Create walking profile optimized for campus routing
            walking_profile = WalkingProfile(
                base_speed_ms=1.3,           # Realistic walking speed
                avoid_stairs=False,          # Allow stairs on campus
                avoid_busy_roads=True,       # Prefer pedestrian paths
                max_detour_factor=1.4        # Allow reasonable detours
            )
            
            # Initialize OSM providers
            self.network_provider = OSMNetworkProvider(
                self.osm_file,
                walking_profile=walking_profile
            )
            
            self.access_provider = OSMAccessProvider(
                self.network_provider.parser,
                walking_profile=walking_profile,
                search_radius_m=200.0,       # Larger radius for campus
                max_nearby_nodes=8           # More options for better routing
            )
            
            load_time = time.time() - start_time
            
            print(f"✅ OSM data loaded in {load_time:.2f} seconds")
            print(f"   Network: {self.network_provider.node_count:,} nodes, "
                  f"{self.network_provider.way_count:,} ways")
            
            # Create engine with optimized configuration
            self.engine = Engine(enable_edge_caching=True)  # Enable caching for performance
            
            # Register providers
            self.engine.register_provider("osm_network", self.network_provider)
            self.engine.register_provider("osm_access", self.access_provider)
            
            print("🔧 Engine configured with OSM providers and caching enabled")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up engine: {e}")
            return False
    
    def run_single_route(self, start_coords: Tuple[float, float], 
                        goal_coords: Tuple[float, float]) -> Tuple[bool, float, Dict[str, Any]]:
        """Run a single routing scenario and collect performance metrics."""
        start_lat, start_lon = start_coords
        goal_lat, goal_lon = goal_coords
        
        route_start_time = time.time()
        
        try:
            # Create vertices
            start_vertex = Vertex({"lat": start_lat, "lon": start_lon})
            goal_vertex = Vertex({"lat": goal_lat, "lon": goal_lon})
            
            # Link vertices to OSM network
            self.access_provider.link(start_vertex, start_lat, start_lon)
            self.access_provider.link(goal_vertex, goal_lat, goal_lon)
            
            # Get connected OSM nodes
            start_edges = self.access_provider.out_edges(start_vertex)
            goal_edges = self.access_provider.out_edges(goal_vertex)
            
            route_found = False
            best_result = None
            best_cost = float('inf')
            
            if start_edges and goal_edges:
                # Try different combinations to find best route
                for start_osm_vertex, start_edge in start_edges[:3]:  # Limit for performance
                    for goal_osm_vertex, goal_edge in goal_edges[:3]:
                        try:
                            # This is where the core C routing happens
                            osm_result = self.engine.plan(
                                start=start_osm_vertex, 
                                goal=goal_osm_vertex
                            )
                            
                            if osm_result and len(osm_result) > 0:
                                total_cost = (start_edge.cost + 
                                            osm_result.total_cost + 
                                            goal_edge.cost)
                                            
                                if total_cost < best_cost:
                                    best_result = osm_result
                                    best_cost = total_cost
                                    route_found = True
                                    break
                        except Exception:
                            continue
                    if route_found:
                        break
            
            route_time = time.time() - route_start_time
            
            # Get engine statistics (this reflects C-level performance)
            engine_stats = self.engine.get_stats()
            
            # Clear links to avoid interference
            self.access_provider.clear_links()
            
            metrics = {
                'route_time': route_time,
                'path_length': len(best_result) if best_result else 0,
                'total_cost': best_cost if route_found else 0,
                'vertices_expanded': engine_stats.vertices_expanded,
                'edges_generated': engine_stats.edges_generated,
                'cache_hits': engine_stats.cache_hits,
                'cache_misses': engine_stats.cache_misses,
                'providers_called': engine_stats.providers_called
            }
            
            return route_found, route_time, metrics
            
        except Exception as e:
            print(f"⚠️  Route failed: {e}")
            return False, time.time() - route_start_time, {}
    
    def profile_routing_scenarios(self, num_routes: int = 20, repetitions: int = 3):
        """Profile multiple routing scenarios with repetitions."""
        print(f"\n🎯 Profiling {num_routes} routes × {repetitions} repetitions = "
              f"{num_routes * repetitions} total routing operations")
        print("="*70)
        
        # Track memory usage
        tracemalloc.start()
        
        total_start_time = time.time()
        
        for rep in range(repetitions):
            print(f"\n📊 Repetition {rep + 1}/{repetitions}")
            rep_start_time = time.time()
            
            rep_successful = 0
            rep_total_time = 0.0
            
            for i, (start_coords, goal_coords) in enumerate(self.campus_routes[:num_routes]):
                print(f"  Route {i+1:2d}: "
                      f"({start_coords[0]:.4f},{start_coords[1]:.4f}) → "
                      f"({goal_coords[0]:.4f},{goal_coords[1]:.4f})", end=" ")
                
                success, route_time, metrics = self.run_single_route(start_coords, goal_coords)
                
                if success:
                    rep_successful += 1
                    self.successful_routes += 1
                    print(f"✅ {route_time:.3f}s ({metrics.get('path_length', 0)} edges)")
                    
                    # Track metrics
                    self.total_vertices_expanded += metrics.get('vertices_expanded', 0)
                    self.total_edges_generated += metrics.get('edges_generated', 0)
                else:
                    print(f"❌ {route_time:.3f}s")
                
                self.route_times.append(route_time)
                rep_total_time += route_time
                
                # Memory snapshot every 10 routes
                if (i + 1) % 10 == 0:
                    current, peak = tracemalloc.get_traced_memory()
                    self.memory_usage.append(peak)
            
            rep_time = time.time() - rep_start_time
            print(f"  Repetition {rep+1} summary: {rep_successful}/{num_routes} successful "
                  f"in {rep_time:.2f}s (avg: {rep_total_time/num_routes:.3f}s per route)")
        
        total_time = time.time() - total_start_time
        
        # Final memory measurement
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self._print_performance_summary(num_routes, repetitions, total_time, peak)
        
        return {
            'total_routes': num_routes * repetitions,
            'successful_routes': self.successful_routes,
            'total_time': total_time,
            'route_times': self.route_times,
            'total_vertices_expanded': self.total_vertices_expanded,
            'total_edges_generated': self.total_edges_generated,
            'peak_memory_mb': peak / 1024 / 1024
        }
    
    def _print_performance_summary(self, num_routes: int, repetitions: int, 
                                 total_time: float, peak_memory: int):
        """Print comprehensive performance analysis."""
        print(f"\n" + "="*70)
        print("🔍 CORE ROUTING ALGORITHM PERFORMANCE ANALYSIS")
        print("="*70)
        
        total_operations = num_routes * repetitions
        success_rate = (self.successful_routes / total_operations) * 100
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Total routing operations: {total_operations}")
        print(f"  Successful routes: {self.successful_routes} ({success_rate:.1f}%)")
        print(f"  Total execution time: {total_time:.2f} seconds")
        print(f"  Average time per route: {sum(self.route_times)/len(self.route_times):.3f} seconds")
        print(f"  Throughput: {total_operations/total_time:.1f} routes/second")
        
        print(f"\n🧠 Core Algorithm Performance:")
        print(f"  Total vertices expanded: {self.total_vertices_expanded:,}")
        print(f"  Total edges generated: {self.total_edges_generated:,}")
        print(f"  Avg vertices per route: {self.total_vertices_expanded/self.successful_routes:.1f}")
        print(f"  Avg edges per route: {self.total_edges_generated/self.successful_routes:.1f}")
        print(f"  Peak memory usage: {peak_memory/1024/1024:.1f} MB")
        
        # Timing analysis
        if self.route_times:
            min_time = min(self.route_times)
            max_time = max(self.route_times)
            avg_time = sum(self.route_times) / len(self.route_times)
            
            print(f"\n⏱️  Timing Analysis:")
            print(f"  Fastest route: {min_time:.3f} seconds")
            print(f"  Slowest route: {max_time:.3f} seconds")
            print(f"  Average route: {avg_time:.3f} seconds")
            print(f"  Timing variance: {max_time/min_time:.1f}x")
        
        # Cache performance (if available)
        if self.engine:
            stats = self.engine.get_stats()
            total_cache_ops = stats.cache_hits + stats.cache_misses
            hit_rate = (stats.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
            
            print(f"\n💾 Cache Performance:")
            print(f"  Cache hits: {stats.cache_hits:,}")
            print(f"  Cache misses: {stats.cache_misses:,}")
            print(f"  Hit rate: {hit_rate:.1f}%")
            print(f"  Provider calls: {stats.providers_called:,}")
        
        print(f"\n🎯 Performance Assessment:")
        if avg_time < 0.050:
            print("  ✅ EXCELLENT: Very fast routing performance")
        elif avg_time < 0.100:
            print("  ✅ GOOD: Acceptable routing performance")
        elif avg_time < 0.200:
            print("  ⚠️  MODERATE: Consider optimization for better performance")
        else:
            print("  ❌ SLOW: Performance optimization recommended")
            
        if success_rate >= 90:
            print("  ✅ HIGH SUCCESS RATE: Excellent route connectivity")
        elif success_rate >= 70:
            print("  ⚠️  MODERATE SUCCESS RATE: Some routes not found")
        else:
            print("  ❌ LOW SUCCESS RATE: Check network connectivity")


def run_cprofile_analysis(profiler: RoutingProfiler, num_routes: int, repetitions: int):
    """Run cProfile analysis focusing on C-level function calls."""
    print(f"\n🔬 Running detailed cProfile analysis...")
    
    # Create a profiler instance
    pr = cProfile.Profile()
    
    # Profile the routing operations
    pr.enable()
    results = profiler.profile_routing_scenarios(num_routes, repetitions)
    pr.disable()
    
    # Generate profile report
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    
    print(f"\n📈 Top functions by cumulative time:")
    stats.print_stats(20)  # Top 20 functions
    
    # Save detailed profile
    profile_file = "routing_profile.prof"
    stats.dump_stats(profile_file)
    print(f"\n💾 Detailed profile saved to: {profile_file}")
    print(f"   View with: python -m pstats {profile_file}")
    
    return results


def main():
    """Main profiling script entry point."""
    parser = argparse.ArgumentParser(
        description="Profile GraphServer core routing algorithm with UW Campus OSM data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python profile_osm_routing.py                    # Default: 20 routes, 3 repetitions
  python profile_osm_routing.py 30                 # 30 routes, 3 repetitions  
  python profile_osm_routing.py 50 5               # 50 routes, 5 repetitions
  python profile_osm_routing.py --cprofile 25 2    # Detailed cProfile analysis
        """
    )
    
    parser.add_argument(
        "num_routes", 
        type=int, 
        nargs="?", 
        default=20,
        help="Number of different routes to test (default: 20, max: 20)"
    )
    
    parser.add_argument(
        "repetitions", 
        type=int, 
        nargs="?", 
        default=3,
        help="Number of repetitions per route (default: 3)"
    )
    
    parser.add_argument(
        "--osm-file",
        type=str,
        default="python/examples/uw_campus.osm",
        help="Path to OSM file (default: python/examples/uw_campus.osm)"
    )
    
    parser.add_argument(
        "--cprofile",
        action="store_true",
        help="Run detailed cProfile analysis (slower but more detailed)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.num_routes < 1 or args.num_routes > 20:
        print(f"❌ Number of routes must be between 1 and 20 (got {args.num_routes})")
        sys.exit(1)
    
    if args.repetitions < 1 or args.repetitions > 10:
        print(f"❌ Repetitions must be between 1 and 10 (got {args.repetitions})")
        sys.exit(1)
    
    # Check OSM file exists
    osm_file = Path(args.osm_file)
    if not osm_file.exists():
        print(f"❌ OSM file not found: {osm_file}")
        print("   Expected UW Campus OSM data at: python/examples/uw_campus.osm")
        sys.exit(1)
    
    print("🚀 GraphServer Core Routing Algorithm Profiler")
    print("==============================================")
    print(f"📁 OSM file: {osm_file}")
    print(f"🗺️  Routes to test: {args.num_routes}")
    print(f"🔄 Repetitions: {args.repetitions}")
    print(f"📊 Analysis mode: {'Detailed cProfile' if args.cprofile else 'Standard timing'}")
    
    # Initialize profiler
    profiler = RoutingProfiler(osm_file)
    
    if not profiler.setup_engine():
        sys.exit(1)
    
    # Run profiling
    try:
        if args.cprofile:
            results = run_cprofile_analysis(profiler, args.num_routes, args.repetitions)
        else:
            results = profiler.profile_routing_scenarios(args.num_routes, args.repetitions)
        
        print(f"\n🎉 Profiling completed successfully!")
        print(f"   Results focus on core C routing algorithm performance")
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Profiling interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Profiling error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()