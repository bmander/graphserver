#!/usr/bin/env python3
"""Download OSM Data from Overpass API

This script downloads OpenStreetMap data for testing the OSM provider.
It supports different profiles for filtering the downloaded data and
predefined locations for convenience.

Usage:
    python download_osm_data.py --profile walking [--location LOCATION] [--output output_file]
    python download_osm_data.py --profile all [--bbox lat_min lon_min lat_max lon_max] [--output output_file]
    python download_osm_data.py --list-locations

Examples:
    python download_osm_data.py --profile walking --location uw-campus --output campus.osm
    python download_osm_data.py --profile travel --location downtown-seattle
    python download_osm_data.py --profile all --location capitol-hill
    python download_osm_data.py --list-locations
    python download_osm_data.py --profile walking --bbox 47.653 -122.315 47.657 -122.305
"""

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

# HTTP and area constants
HTTP_OK = 200
MAX_AREA_DEG_SQUARED = 0.01  # About 1km x 1km at mid-latitudes
MB_SIZE = 1024 * 1024  # 1 MB in bytes

# Predefined locations with their bounding boxes
PREDEFINED_LOCATIONS = {
    "uw-campus": (
        47.649542342421846,
        -122.3146476835271,
        47.661035800431776,
        -122.30256914707921,
    ),
    "downtown-seattle": (47.595, -122.345, 47.615, -122.315),
    "capitol-hill": (47.610, -122.325, 47.625, -122.305),
    "fremont": (47.645, -122.360, 47.660, -122.340),
    "ballard": (47.660, -122.390, 47.675, -122.370),
    "west-seattle": (47.560, -122.390, 47.580, -122.370),
    "seattle-metro": (47.500, -122.500, 47.798185, -121.977277),
}


def get_overpass_query(
    profile: str, lat_min: float, lon_min: float, lat_max: float, lon_max: float
) -> str:
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
    if profile == "travel":
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
    if profile == "all":
        # All ways
        return f"""
        [out:xml][timeout:60];
        (
          way{bbox};
        );
        (._;>;);
        out;
        """.strip()
    error_msg = f"Unknown profile: {profile}"
    raise ValueError(error_msg)


def download_osm_data(
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    output_file: str,
    profile: str = "walking",
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
            if response.status != HTTP_OK:
                print(f"Error: HTTP {response.status}")
                sys.exit(1)

            print("Request successful, downloading data...")

            # Get content length if available for percentage progress

            # Download with progress feedback using larger chunks
            data = b""
            chunk_size = MB_SIZE
            last_update = start_time
            last_size = 0

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                data += chunk

                # Update progress every 0.5 seconds
                current_time = time.time()
                if current_time - last_update >= 0.5:
                    size_mb = len(data) / MB_SIZE

                    # Calculate rate based on data downloaded since last update
                    downloaded_since_last = len(data) - last_size
                    time_since_last = current_time - last_update
                    rate_mbps = (
                        (downloaded_since_last / MB_SIZE) / time_since_last
                        if time_since_last > 0
                        else 0
                    )

                    print(
                        f"\r  Downloaded: {size_mb:.1f} MB, Rate: {rate_mbps:.1f} MB/s",
                        end="",
                        flush=True,
                    )

                    last_update = current_time
                    last_size = len(data)

        download_time = time.time() - start_time
        print()  # New line after progress updates

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
  %(prog)s --profile walking --location uw-campus --output campus.osm
  %(prog)s --profile travel --location downtown-seattle
  %(prog)s --profile all --location capitol-hill
  %(prog)s --list-locations
  %(prog)s --profile walking --bbox 47.653 -122.315 47.657 -122.305 --output campus.osm
        """,
    )

    parser.add_argument(
        "--profile",
        choices=["walking", "travel", "all"],
        default="walking",
        help="Data profile: 'walking' for pedestrian-friendly ways (default), "
        "'travel' for all travelable ways, 'all' for all ways",
    )

    parser.add_argument(
        "--bbox",
        nargs=4,
        metavar=("LAT_MIN", "LON_MIN", "LAT_MAX", "LON_MAX"),
        type=float,
        help="Bounding box coordinates (lat_min lon_min lat_max lon_max)",
    )

    parser.add_argument(
        "--location",
        help="Use predefined location (e.g., 'uw-campus', 'downtown-seattle'). "
        "Use --list-locations to see all available locations.",
    )

    parser.add_argument(
        "--list-locations",
        action="store_true",
        help="List all available predefined locations and exit",
    )

    parser.add_argument("--output", help="Output OSM XML file path")

    args = parser.parse_args()

    # Handle --list-locations first
    if args.list_locations:
        print("Available predefined locations:")
        print()
        for key, bbox in PREDEFINED_LOCATIONS.items():
            lat_min, lon_min, lat_max, lon_max = bbox
            print(f"  {key}: ({lat_min}, {lon_min}) to ({lat_max}, {lon_max})")
        sys.exit(0)

    # Validate mutually exclusive arguments
    if args.bbox and args.location:
        print("Error: --bbox and --location are mutually exclusive")
        sys.exit(1)

    # Set coordinates based on arguments
    if args.bbox:
        lat_min, lon_min, lat_max, lon_max = args.bbox
    elif args.location:
        location_key = args.location.lower()
        if location_key not in PREDEFINED_LOCATIONS:
            print(f"Error: Unknown location '{args.location}'")
            print("Use --list-locations to see available locations")
            sys.exit(1)

        lat_min, lon_min, lat_max, lon_max = PREDEFINED_LOCATIONS[location_key]
        print(f"Using predefined location: {location_key}")
    else:
        print("No location or bounding box specified.")
        print("Available predefined locations:")
        print()
        for key, bbox in PREDEFINED_LOCATIONS.items():
            lat_min, lon_min, lat_max, lon_max = bbox
            print(f"  {key}: ({lat_min}, {lon_min}) to ({lat_max}, {lon_max})")
        print()
        print("Use --location <location_name> or --bbox <coords> to specify an area.")
        sys.exit(0)

    if args.output:
        output_file = args.output
    else:
        output_file = "out.osm"

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

    if area_deg2 > MAX_AREA_DEG_SQUARED:  # About 1km x 1km at mid-latitudes
        print(f"Warning: Large area requested ({area_deg2:.4f} deg²)")
        print("This may take a long time or fail. Consider a smaller area.")

    download_osm_data(lat_min, lon_min, lat_max, lon_max, output_file, args.profile)

    print()
    print("Next steps:")
    print(f"  python osm_routing_example.py {output_file}")
    print("Or test the provider directly:")
    print(
        f'  python -c "from graphserver.providers.osm import OSMDataSource; '
        f"data = OSMDataSource('{output_file}'); "
        f"print(f'Loaded {{data.node_count}} nodes, {{data.way_count}} ways')\""
    )


if __name__ == "__main__":
    main()
