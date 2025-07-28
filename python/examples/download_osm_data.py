#!/usr/bin/env python3
"""Download OSM Data from Overpass API

This script downloads OpenStreetMap data for testing the OSM provider.
It supports different profiles for filtering the downloaded data.

Usage:
    python download_osm_data.py --profile walking [--bbox lat_min lon_min lat_max lon_max] [--output output_file]
    python download_osm_data.py --profile all [--bbox lat_min lon_min lat_max lon_max] [--output output_file]

Examples:
    python download_osm_data.py --profile walking --bbox 47.653 -122.315 47.657 -122.305 --output campus.osm
    python download_osm_data.py --profile travel --output travel_data.osm
    python download_osm_data.py --profile all --output all_data.osm
"""

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


def get_overpass_query(profile: str, lat_min: float, lon_min: float, lat_max: float, lon_max: float) -> str:
    """Generate Overpass query based on profile.
    
    Args:
        profile: Query profile ("walking", "travel", or "all")
        lat_min: Minimum latitude (south)
        lon_min: Minimum longitude (west)
        lat_max: Maximum latitude (north)
        lon_max: Maximum longitude (east)
        
    Returns:
        Overpass query string
    """
    bbox = f"({lat_min},{lon_min},{lat_max},{lon_max})"
    
    if profile == "walking":
        # Pedestrian-friendly ways
        return f"""
        [out:xml][timeout:60];
        (
          way[highway~"^(footway|path|steps|pedestrian|residential|living_street|unclassified|service)$"]{bbox};
          way[highway="primary"][sidewalk~"^(both|left|right|yes)$"]{bbox};
          way[highway="secondary"][sidewalk~"^(both|left|right|yes)$"]{bbox};
          way[highway="tertiary"][sidewalk~"^(both|left|right|yes)$"]{bbox};
        );
        (._;>;);
        out;
        """.strip()
    elif profile == "travel":
        # All travelable ways (highways, paths, footways, etc.)
        return f"""
        [out:xml][timeout:60];
        (
          way[highway~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|track|footway|path|steps|pedestrian|cycleway|bridleway)$"]{bbox};
          way[highway="motorway_link"]{bbox};
          way[highway="trunk_link"]{bbox};
          way[highway="primary_link"]{bbox};
          way[highway="secondary_link"]{bbox};
          way[highway="tertiary_link"]{bbox};
        );
        (._;>;);
        out;
        """.strip()
    elif profile == "all":
        # All ways
        return f"""
        [out:xml][timeout:60];
        (
          way{bbox};
        );
        (._;>;);
        out;
        """.strip()
    else:
        raise ValueError(f"Unknown profile: {profile}")


def download_osm_data(
    lat_min: float, lon_min: float, lat_max: float, lon_max: float, output_file: str, profile: str = "walking"
) -> None:
    """Download OSM data from Overpass API.

    Args:
        lat_min: Minimum latitude (south)
        lon_min: Minimum longitude (west)
        lat_max: Maximum latitude (north)
        lon_max: Maximum longitude (east)
        output_file: Output OSM XML file path
        profile: Data profile ("walking" or "all")
    """

    # Get the appropriate Overpass query
    overpass_query = get_overpass_query(profile, lat_min, lon_min, lat_max, lon_max)

    # URL encode the query
    encoded_query = quote(overpass_query)
    url = f"https://overpass-api.de/api/interpreter?data={encoded_query}"

    print(f"Downloading OSM data with profile '{profile}' for bounding box:")
    print(f"  South-West: ({lat_min}, {lon_min})")
    print(f"  North-East: ({lat_max}, {lon_max})")
    print(f"  Output file: {output_file}")
    print(f"  Query size: {len(overpass_query)} characters")
    print()

    try:
        print("Sending request to Overpass API...")
        start_time = time.time()

        with urlopen(url) as response:
            if response.status != 200:
                print(f"Error: HTTP {response.status}")
                sys.exit(1)

            print("Request successful, downloading data...")
            data = response.read()

        download_time = time.time() - start_time

        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(data)

        print(f"✅ Download completed in {download_time:.2f} seconds")
        print(f"✅ Saved {len(data):,} bytes to {output_file}")

        # Basic validation
        if data.startswith(b"<?xml") and b"</osm>" in data:
            # Count some basic elements
            way_count = data.count(b"<way ")
            node_count = data.count(b"<node ")
            print(f"✅ File appears valid: {node_count} nodes, {way_count} ways")
        else:
            print("⚠️  Warning: File may not be valid OSM XML")
            print(f"First 200 bytes: {data[:200]}")

    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        sys.exit(1)


def main() -> None:
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Download OSM data from Overpass API with different profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --profile walking --bbox 47.653 -122.315 47.657 -122.305 --output campus.osm
  %(prog)s --profile travel --output travel_data.osm
  %(prog)s --profile all --output all_data.osm
  %(prog)s --profile walking  # Uses default bbox and filename
        """
    )
    
    parser.add_argument(
        "--profile", 
        choices=["walking", "travel", "all"], 
        default="walking",
        help="Data profile: 'walking' for pedestrian-friendly ways (default), 'travel' for all travelable ways, 'all' for all ways"
    )
    
    parser.add_argument(
        "--bbox", 
        nargs=4, 
        metavar=("LAT_MIN", "LON_MIN", "LAT_MAX", "LON_MAX"),
        type=float,
        help="Bounding box coordinates (lat_min lon_min lat_max lon_max)"
    )
    
    parser.add_argument(
        "--output", 
        help="Output OSM XML file path"
    )
    
    args = parser.parse_args()
    
    # Set defaults if not provided
    if args.bbox:
        lat_min, lon_min, lat_max, lon_max = args.bbox
    else:
        print("No bounding box provided, using default location (UW Campus, Seattle)")
        # University of Washington campus area - good pedestrian infrastructure
        lat_min, lon_min = 47.649542342421846, -122.3146476835271  # South-West
        lat_max, lon_max = 47.661035800431776, -122.30256914707921  # North-East
    
    if args.output:
        output_file = args.output
    else:
        if args.profile == "walking":
            output_file = "uw_campus_walking.osm"
        elif args.profile == "travel":
            output_file = "uw_campus_travel.osm"
        else:
            output_file = "uw_campus_all.osm"

    # Validate bounding box
    if lat_min >= lat_max:
        print("Error: lat_min must be less than lat_max")
        sys.exit(1)
    if lon_min >= lon_max:
        print("Error: lon_min must be less than lon_max")
        sys.exit(1)

    # Check if area is reasonable (not too large)
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    area_deg2 = lat_diff * lon_diff

    if area_deg2 > 0.01:  # About 1km x 1km at mid-latitudes
        print(f"Warning: Large area requested ({area_deg2:.4f} deg²)")
        print("This may take a long time or fail. Consider a smaller area.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            sys.exit(0)

    download_osm_data(lat_min, lon_min, lat_max, lon_max, output_file, args.profile)

    print()
    print("Next steps:")
    print(f"  python osm_routing_example.py {output_file}")
    print("Or test the provider directly:")
    print(
        f"  python -c \"from graphserver.providers.osm import OSMProvider; p = OSMProvider('{output_file}'); print(f'Loaded {{p.node_count}} nodes, {{p.way_count}} ways')\""
    )


if __name__ == "__main__":
    main()
