"""Spatial Indexing and Distance Calculations

This module provides spatial indexing capabilities using R-tree and accurate
geodesic distance calculations using PyProj for the OSM provider.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

try:
    from rtree import index
except ImportError as e:
    msg = "Rtree is required for spatial indexing. Install with: pip install rtree"
    raise ImportError(msg) from e

try:
    from pyproj import Geod
    from shapely.geometry import Point
except ImportError as e:
    msg = "PyProj and Shapely are required for distance calculations. Install with: pip install pyproj shapely"
    raise ImportError(msg) from e

from .types import OSMNode

logger = logging.getLogger(__name__)

# Global geodesic calculator for WGS84
_GEOD = Geod(ellps="WGS84")


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance between two points on WGS84 ellipsoid.

    Args:
        lat1: Latitude of first point in degrees
        lon1: Longitude of first point in degrees
        lat2: Latitude of second point in degrees
        lon2: Longitude of second point in degrees

    Returns:
        Distance in meters
    """
    # Use PyProj for accurate geodesic distance calculation
    _, _, distance = _GEOD.inv(lon1, lat1, lon2, lat2)
    return abs(distance)


def create_point_from_coords(lat: float, lon: float) -> Point:
    """Create a Shapely Point from latitude/longitude coordinates.

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees

    Returns:
        Shapely Point geometry
    """
    return Point(lon, lat)  # Note: Shapely uses (x, y) = (lon, lat) order


class SpatialIndex:
    """R-tree spatial index for efficient nearest neighbor queries on OSM nodes."""

    def __init__(self) -> None:
        """Initialize the spatial index."""
        # Create R-tree index
        # Using Property to set leaf capacity for better performance with point data
        p = index.Property()
        p.leaf_capacity = 1000  # Optimize for many points
        p.fill_factor = 0.9
        self.rtree = index.Index(properties=p)

        # Keep reference to node data
        self.nodes: dict[int, OSMNode] = {}
        self._indexed_count = 0

    def add_node(self, node: OSMNode) -> None:
        """Add an OSM node to the spatial index.

        Args:
            node: OSM node to add to the index
        """
        # R-tree expects (minx, miny, maxx, maxy) bounding box
        # For points, min and max are the same
        bbox = (node.lon, node.lat, node.lon, node.lat)

        # Insert into R-tree with node ID as the object identifier
        self.rtree.insert(node.id, bbox)

        # Store node data
        self.nodes[node.id] = node
        self._indexed_count += 1

        if self._indexed_count % 10000 == 0:
            logger.debug("Indexed %d nodes", self._indexed_count)

    def add_nodes(self, nodes: dict[int, OSMNode]) -> None:
        """Add multiple OSM nodes to the spatial index.

        Args:
            nodes: Dictionary of node ID to OSMNode objects
        """
        logger.info("Adding %d nodes to spatial index", len(nodes))

        for node in nodes.values():
            self.add_node(node)

        logger.info("Spatial index created with %d nodes", len(self.nodes))

    def find_nearest_nodes(
        self, lat: float, lon: float, radius_m: float = 100.0, max_results: int = 10
    ) -> list[tuple[OSMNode, float]]:
        """Find OSM nodes near the given coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters
            max_results: Maximum number of results to return

        Returns:
            List of (node, distance) tuples sorted by distance
        """
        # Convert radius from meters to approximate degrees
        # This is a rough approximation for the R-tree query
        # 1 degree ≈ 111,320 meters at the equator
        radius_deg = radius_m / 111320.0

        # Create bounding box for R-tree query
        min_lon = lon - radius_deg
        max_lon = lon + radius_deg
        min_lat = lat - radius_deg
        max_lat = lat + radius_deg

        # Query R-tree for nodes in bounding box
        candidate_ids = list(
            self.rtree.intersection((min_lon, min_lat, max_lon, max_lat))
        )

        # Calculate exact distances and filter by radius
        results = []
        for node_id in candidate_ids:
            if node_id not in self.nodes:
                continue

            node = self.nodes[node_id]
            distance = calculate_distance(lat, lon, node.lat, node.lon)

            if distance <= radius_m:
                results.append((node, distance))

        # Sort by distance and limit results
        results.sort(key=lambda x: x[1])
        return results[:max_results]

    def find_nearest_node(
        self, lat: float, lon: float, radius_m: float = 1000.0
    ) -> OSMNode | None:
        """Find the single nearest OSM node to the given coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Maximum search radius in meters

        Returns:
            Nearest OSM node or None if no node found within radius
        """
        results = self.find_nearest_nodes(lat, lon, radius_m, max_results=1)
        return results[0][0] if results else None

    def get_nodes_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> Iterator[OSMNode]:
        """Get all nodes within a bounding box.

        Args:
            min_lat: Minimum latitude
            min_lon: Minimum longitude
            max_lat: Maximum latitude
            max_lon: Maximum longitude

        Yields:
            OSM nodes within the bounding box
        """
        node_ids = self.rtree.intersection((min_lon, min_lat, max_lon, max_lat))

        for node_id in node_ids:
            if node_id in self.nodes:
                yield self.nodes[node_id]

    def __len__(self) -> int:
        """Get the number of indexed nodes."""
        return len(self.nodes)


class BoundingBox:
    """Helper class for bounding box operations."""

    def __init__(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> None:
        """Initialize bounding box.

        Args:
            min_lat: Minimum latitude
            min_lon: Minimum longitude
            max_lat: Maximum latitude
            max_lon: Maximum longitude
        """
        self.min_lat = min_lat
        self.min_lon = min_lon
        self.max_lat = max_lat
        self.max_lon = max_lon

    @classmethod
    def from_center_radius(cls, lat: float, lon: float, radius_m: float) -> BoundingBox:
        """Create bounding box from center point and radius.

        Args:
            lat: Center latitude in degrees
            lon: Center longitude in degrees
            radius_m: Radius in meters

        Returns:
            BoundingBox instance
        """
        # Approximate conversion from meters to degrees
        radius_deg = radius_m / 111320.0

        return cls(
            min_lat=lat - radius_deg,
            min_lon=lon - radius_deg,
            max_lat=lat + radius_deg,
            max_lon=lon + radius_deg,
        )

    def contains_point(self, lat: float, lon: float) -> bool:
        """Check if a point is within the bounding box.

        Args:
            lat: Point latitude
            lon: Point longitude

        Returns:
            True if point is within bounding box
        """
        return (
            self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon
        )

    def area_km2(self) -> float:
        """Calculate approximate area of bounding box in square kilometers.

        Returns:
            Area in square kilometers
        """
        # Approximate calculation - not accounting for Earth curvature
        lat_diff = self.max_lat - self.min_lat
        lon_diff = self.max_lon - self.min_lon

        # Convert degrees to kilometers (approximate)
        lat_km = lat_diff * 111.32
        lon_km = (
            lon_diff
            * 111.32
            * abs(math.cos(math.radians((self.min_lat + self.max_lat) / 2)))
        )

        return lat_km * lon_km
