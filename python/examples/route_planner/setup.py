#!/usr/bin/env python3
"""Setup script for Route Planner example application.

This script downloads and sets up the required JavaScript libraries
for the Route Planner web application.
"""

import sys
import urllib.request
import urllib.error
from pathlib import Path


def download_file(url: str, dest_path: Path, description: str) -> bool:
    """Download a file from URL to destination path.

    Args:
        url: URL to download from
        dest_path: Local path to save file
        description: Human-readable description of the file

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Downloading {description}...")
        urllib.request.urlretrieve(url, dest_path)
        print(f"  ✓ Saved to {dest_path}")
        return True
    except urllib.error.URLError as e:
        print(f"  ✗ Failed to download {description}: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error downloading {description}: {e}")
        return False


def setup_leaflet(base_dir: Path) -> bool:
    """Download and setup Leaflet.js library.

    Args:
        base_dir: Base directory of the route_planner application

    Returns:
        True if successful, False otherwise
    """
    leaflet_dir = base_dir / "static" / "lib" / "leaflet"
    images_dir = leaflet_dir / "images"

    # Create directories
    leaflet_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Leaflet version to download
    version = "1.9.4"
    base_url = f"https://unpkg.com/leaflet@{version}/dist"

    # Files to download
    files = [
        {
            "url": f"{base_url}/leaflet.css",
            "path": leaflet_dir / "leaflet.css",
            "description": "Leaflet CSS",
        },
        {
            "url": f"{base_url}/leaflet.js",
            "path": leaflet_dir / "leaflet.js",
            "description": "Leaflet JavaScript",
        },
        {
            "url": f"{base_url}/images/marker-icon.png",
            "path": images_dir / "marker-icon.png",
            "description": "Leaflet marker icon",
        },
        {
            "url": f"{base_url}/images/marker-shadow.png",
            "path": images_dir / "marker-shadow.png",
            "description": "Leaflet marker shadow",
        },
        {
            "url": f"{base_url}/images/marker-icon-2x.png",
            "path": images_dir / "marker-icon-2x.png",
            "description": "Leaflet marker icon (high-DPI)",
        },
    ]

    print(f"Setting up Leaflet.js v{version}...")

    success_count = 0
    for file_info in files:
        if download_file(file_info["url"], file_info["path"], file_info["description"]):
            success_count += 1

    if success_count == len(files):
        print(f"\n✅ Leaflet.js v{version} setup complete!")
        return True
    else:
        print(
            f"\n⚠️  Leaflet.js setup partially failed ({success_count}/{len(files)} files downloaded)"
        )
        return False


def verify_setup(base_dir: Path) -> bool:
    """Verify that all required files are present.

    Args:
        base_dir: Base directory of the route_planner application

    Returns:
        True if all files are present, False otherwise
    """
    required_files = [
        "static/lib/leaflet/leaflet.css",
        "static/lib/leaflet/leaflet.js",
        "static/lib/leaflet/images/marker-icon.png",
        "static/lib/leaflet/images/marker-shadow.png",
        "static/app.js",
        "static/index.html",
        "static/style.css",
    ]

    print("\nVerifying setup...")
    missing_files = []

    for file_path in required_files:
        full_path = base_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✓ {file_path}")

    if missing_files:
        print(f"\n⚠️  Missing files:")
        for file_path in missing_files:
            print(f"  ✗ {file_path}")
        return False
    else:
        print(f"\n✅ All required files are present!")
        return True


def main() -> int:
    """Main setup function.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("Route Planner Setup Script")
    print("=" * 40)

    # Get the directory where this script is located
    script_dir = Path(__file__).parent.resolve()

    print(f"Setting up Route Planner in: {script_dir}")

    # Check if we're in the right directory
    if not (script_dir / "server.py").exists():
        print("✗ Error: This script must be run from the route_planner directory")
        print("  Expected to find server.py in the current directory")
        return 1

    success = True

    # Setup Leaflet.js
    if not setup_leaflet(script_dir):
        success = False

    # Verify setup
    if not verify_setup(script_dir):
        success = False

    if success:
        print("\n🎉 Route Planner setup completed successfully!")
        print("\nNext steps:")
        print("1. Run the application:")
        print("   export PYTHONPATH=python")
        print("   python -m examples.route_planner --osm your_file.osm")
        print("2. Open http://localhost:8080 in your browser")
        print("3. Click on the map to set route points!")
        return 0
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        print("\nTroubleshooting:")
        print("- Ensure you have internet connection for downloading files")
        print("- Check that you have write permissions in this directory")
        print("- Try running the script again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
