#!/usr/bin/env python3
"""Download OSM Data from Overpass API

This script downloads OpenStreetMap data for testing the OSM provider.
It fetches pedestrian-friendly ways from a specified bounding box.

Usage:
    python download_osm_data.py [lat_min] [lon_min] [lat_max] [lon_max] [output_file]

Example:
    python download_osm_data.py 47.653 -122.315 47.657 -122.305 campus.osm
"""

import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


def download_osm_data(
    lat_min: float, lon_min: float, lat_max: float, lon_max: float, output_file: str
) -> None:
    """Download OSM data from Overpass API for pedestrian routing.

    Args:
        lat_min: Minimum latitude (south)
        lon_min: Minimum longitude (west)
        lat_max: Maximum latitude (north)
        lon_max: Maximum longitude (east)
        output_file: Output OSM XML file path
    """

    # Overpass query to get pedestrian-friendly ways
    overpass_query = f"""
    [out:xml][timeout:60];
    (
      way[highway~"^(footway|path|steps|pedestrian|residential|living_street|unclassified|service)$"]({lat_min},{lon_min},{lat_max},{lon_max});
      way[highway="primary"][sidewalk~"^(both|left|right|yes)$"]({lat_min},{lon_min},{lat_max},{lon_max});
      way[highway="secondary"][sidewalk~"^(both|left|right|yes)$"]({lat_min},{lon_min},{lat_max},{lon_max});
      way[highway="tertiary"][sidewalk~"^(both|left|right|yes)$"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    (._;>;);
    out;
    """.strip()

    # URL encode the query
    encoded_query = quote(overpass_query)
    url = f"https://overpass-api.de/api/interpreter?data={encoded_query}"

    print("Downloading OSM data for bounding box:")
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
    """Main function with example locations."""
    if len(sys.argv) == 6:
        # Custom bounding box provided
        try:
            lat_min = float(sys.argv[1])
            lon_min = float(sys.argv[2])
            lat_max = float(sys.argv[3])
            lon_max = float(sys.argv[4])
            output_file = sys.argv[5]
        except ValueError:
            print("Error: Invalid coordinates provided")
            sys.exit(1)
    else:
        # Use default location (University of Washington campus area)
        print("No coordinates provided, using default location (UW Campus, Seattle)")
        print(
            "Usage: python download_osm_data.py [lat_min] [lon_min] [lat_max] [lon_max] [output_file]"
        )
        print()

        # University of Washington campus area - good pedestrian infrastructure
        lat_min, lon_min = 47.649542342421846, -122.3146476835271  # South-West
        lat_max, lon_max = 47.661035800431776, -122.30256914707921  # North-East
        output_file = "uw_campus.osm"

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

    download_osm_data(lat_min, lon_min, lat_max, lon_max, output_file)

    print()
    print("Next steps:")
    print(f"  python osm_routing_example.py {output_file}")
    print("Or test the provider directly:")
    print(
        f"  python -c \"from graphserver.providers.osm import OSMProvider; p = OSMProvider('{output_file}'); print(f'Loaded {{p.node_count}} nodes, {{p.way_count}} ways')\""
    )


if __name__ == "__main__":
    main()
