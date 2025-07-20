#!/usr/bin/env python3
"""Minimal pathfinding test to debug search progression"""

import tempfile
from pathlib import Path

from graphserver import Engine, Vertex
from graphserver.providers.osm import OSMNetworkProvider, OSMAccessProvider
from graphserver.providers.osm.types import WalkingProfile

# Simple OSM data: single road from (0,0) to (0,0.001)
SIMPLE_OSM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="debug">
  <node id="1" lat="0.0" lon="0.0"/>
  <node id="2" lat="0.0" lon="0.001"/>
  <way id="100" version="1">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="footway"/>
  </way>
</osm>"""


def minimal_pathfinding_test():
    print("🔬 Minimal Pathfinding Test")
    print("=" * 40)

    # Create temporary OSM file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".osm", delete=False) as f:
        f.write(SIMPLE_OSM_XML)
        f.flush()
        osm_file = Path(f.name)

    try:
        # Create providers
        walking_profile = WalkingProfile(base_speed_ms=1.0)

        network_provider = OSMNetworkProvider(osm_file, walking_profile=walking_profile)
        access_provider = OSMAccessProvider(
            parser=network_provider.parser,
            walking_profile=walking_profile,
            search_radius_m=1000.0,
            max_nearby_nodes=5,
            build_index=True,
        )

        # Register with engine
        engine = Engine()
        engine.register_provider("osm_network", network_provider)
        engine.register_provider("osm_access", access_provider)

        # Define coordinates
        start_coords = Vertex({"lat": 0.0001, "lon": 0.0001})  # Near node 1
        goal_coords = Vertex({"lat": 0.0001, "lon": 0.0011})  # Near node 2

        print(f"Start: {start_coords._data}")
        print(f"Goal:  {goal_coords._data}")
        print()

        # Execute pathfinding with C-level debug output
        print("🚀 Starting pathfinding...")
        try:
            result = engine.plan(start=start_coords, goal=goal_coords)
            print(f"✅ SUCCESS! Found {len(result)} edges")
        except Exception as e:
            print(f"❌ FAILED: {e}")

    finally:
        osm_file.unlink()


if __name__ == "__main__":
    minimal_pathfinding_test()
