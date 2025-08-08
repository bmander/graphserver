"""OSM Data Source

This module provides the OSMDataSource class for parsing and managing
OpenStreetMap data to be shared across multiple providers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    ProgressCallback = Callable[[str], None] | None

try:
    import osmium
except ImportError as e:
    msg = "PyOsmium is required for OSM parsing. Install with: pip install osmium"
    raise ImportError(msg) from e


from .spatial import SpatialIndex
from .types import MIN_WAY_NODES, OSMNode, OSMWay, WalkingProfile

logger = logging.getLogger(__name__)


class OSMHandler(osmium.SimpleHandler):
    """PyOsmium handler for extracting pedestrian-relevant OSM data."""

    def __init__(self, progress_callback: ProgressCallback = None) -> None:
        """Initialize the OSM handler."""
        super().__init__()
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}
        self._node_count = 0
        self._way_count = 0
        self._walkable_way_count = 0
        self._progress_callback = progress_callback
        self._total_estimates = {"nodes": 0, "ways": 0}  # Will be updated as we parse

        # Track bounds during parsing for efficient lookups
        self.min_lat: float | None = None
        self.max_lat: float | None = None
        self.min_lon: float | None = None
        self.max_lon: float | None = None

    def node(self, n: osmium.Node) -> None:
        """Process an OSM node."""
        self._node_count += 1

        # Convert tags to dictionary
        tags = {tag.k: tag.v for tag in n.tags}

        # Store all nodes - we'll filter later based on way references
        lat, lon = n.location.lat, n.location.lon
        node = OSMNode(id=n.id, lat=lat, lon=lon, tags=tags)
        self.nodes[n.id] = node

        # Update bounds during parsing for efficient caching
        if self.min_lat is None:
            self.min_lat = self.max_lat = lat
            self.min_lon = self.max_lon = lon
        else:
            self.min_lat = min(self.min_lat, lat)
            self.max_lat = max(self.max_lat, lat)
            self.min_lon = min(self.min_lon, lon)
            self.max_lon = max(self.max_lon, lon)

        # Report progress every 1,000 nodes
        if self._node_count % 1000 == 0:
            if self._progress_callback:
                # We don't know total nodes in advance, so use count for progress
                self._progress_callback(
                    f"Processing nodes... ({self._node_count:,} processed)"
                )
            logger.debug("Processed %d nodes", self._node_count)

    def way(self, w: osmium.Way) -> None:
        """Process an OSM way."""
        self._way_count += 1

        # Convert tags to dictionary
        tags = {tag.k: tag.v for tag in w.tags}

        # Extract node references
        node_refs = [node.ref for node in w.nodes]

        if len(node_refs) < MIN_WAY_NODES:
            return  # Skip ways with insufficient nodes

        way = OSMWay(id=w.id, node_refs=node_refs, tags=tags)

        # Only store walkable ways
        if way.is_walkable():
            self.ways[w.id] = way
            self._walkable_way_count += 1

        # Report progress every 1,000 ways
        if self._way_count % 1000 == 0:
            if self._progress_callback:
                msg = (
                    f"Processing ways... ({self._way_count:,} processed, "
                    f"{self._walkable_way_count:,} walkable)"
                )
                self._progress_callback(msg)
            logger.debug(
                "Processed %d ways (%d walkable)",
                self._way_count,
                self._walkable_way_count,
            )

    def relation(self, r: osmium.Relation) -> None:
        """Process an OSM relation (currently ignored for pedestrian routing)."""
        # For now, we ignore relations as they're not essential for basic
        # pedestrian routing
        # In the future, we could handle route relations or access restrictions


class OSMDataSource:
    """OSM data source for parsing and managing raw OSM data.

    This class handles parsing of OSM files and provides shared access
    to the raw parsed data (nodes and ways) and spatial indexing for multiple
    providers. Edge generation is handled by the individual providers.
    """

    def __init__(
        self,
        osm_file: str | Path,
        *,
        walking_profile: WalkingProfile | None = None,
        build_spatial_index: bool = True,
        progress_callback: ProgressCallback = None,
    ) -> None:
        """Initialize OSM data source from an OSM file.

        Args:
            osm_file: Path to OSM XML or PBF file
            walking_profile: Configuration for pedestrian routing preferences
            build_spatial_index: Whether to build spatial index (recommended for
                performance)
            progress_callback: Optional callback for progress updates during parsing

        Raises:
            FileNotFoundError: If OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        self.osm_file = Path(osm_file)
        self.walking_profile = walking_profile or WalkingProfile()
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}
        # Index for O(1) lookup of ways containing a node and position indices
        self.node_way_index: dict[int, list[tuple[OSMWay, int]]] = {}
        # Cached bounds for efficient map initialization
        self.bounds: dict | None = None

        # Parse OSM data
        logger.info("Initializing OSM data source from %s", self.osm_file)
        self._parse_file(self.osm_file, progress_callback)

        # Build spatial index for efficient coordinate-based queries
        self.spatial_index: SpatialIndex | None = None
        if build_spatial_index:
            self._build_spatial_index()

        logger.info(
            "OSM data source ready: %d nodes, %d ways",
            len(self.nodes),
            len(self.ways),
        )

    def _parse_file(
        self, osm_file: str | Path, progress_callback: ProgressCallback = None
    ) -> None:
        """Parse an OSM file and extract pedestrian network data.

        Args:
            osm_file: Path to OSM XML or PBF file
            progress_callback: Optional callback for progress updates

        Raises:
            FileNotFoundError: If the OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        osm_path = Path(osm_file)
        if not osm_path.exists():
            msg = f"OSM file not found: {osm_path}"
            raise FileNotFoundError(msg)

        logger.info("Parsing OSM file: %s", osm_path)

        try:
            # Parse the OSM file
            handler = OSMHandler(progress_callback)
            if progress_callback:
                progress_callback("Starting OSM file parsing...")
            handler.apply_file(str(osm_path))

            logger.info(
                "Parsed %d nodes, %d walkable ways",
                len(handler.nodes),
                len(handler.ways),
            )

            # Store parsed data
            self.nodes = handler.nodes
            self.ways = handler.ways

            # Calculate and cache bounds from parsed data
            self._calculate_bounds_from_handler(handler)

            # Filter nodes to only those referenced by walkable ways
            self._filter_referenced_nodes()

        except Exception as e:
            msg = f"Failed to parse OSM file: {e}"
            raise RuntimeError(msg) from e

    def _filter_referenced_nodes(self) -> None:
        """Filter nodes to only include those referenced by walkable ways."""
        referenced_node_ids = set()

        # Build node-way index while collecting referenced nodes
        self.node_way_index = {}
        for way in self.ways.values():
            for position_index, node_id in enumerate(way.node_refs):
                referenced_node_ids.add(node_id)
                if node_id not in self.node_way_index:
                    self.node_way_index[node_id] = []
                self.node_way_index[node_id].append((way, position_index))

        # Keep only referenced nodes
        filtered_nodes = {
            node_id: node
            for node_id, node in self.nodes.items()
            if node_id in referenced_node_ids
        }

        self.nodes = filtered_nodes
        logger.info(
            "Filtered to %d referenced nodes with way index for %d nodes",
            len(self.nodes),
            len(self.node_way_index),
        )

    def _calculate_bounds_from_handler(self, handler: OSMHandler) -> None:
        """Calculate and cache bounds from parsed OSM handler data.

        Args:
            handler: OSM handler with parsed bounds information
        """
        if (
            handler.min_lat is not None
            and handler.max_lat is not None
            and handler.min_lon is not None
            and handler.max_lon is not None
        ):
            # Add a small buffer around the bounds (10% of range)
            lat_range = handler.max_lat - handler.min_lat
            lon_range = handler.max_lon - handler.min_lon
            lat_buffer = lat_range * 0.1 if lat_range > 0 else 0.01
            lon_buffer = lon_range * 0.1 if lon_range > 0 else 0.01

            self.bounds = {
                "south": handler.min_lat - lat_buffer,
                "west": handler.min_lon - lon_buffer,
                "north": handler.max_lat + lat_buffer,
                "east": handler.max_lon + lon_buffer,
            }
        else:
            # No bounds could be calculated
            self.bounds = None

    def get_bounds(self) -> dict:
        """Get cached geographic bounds for map initialization.

        Returns:
            Dict with south, west, north, east bounds
        """
        if self.bounds is not None:
            return self.bounds

        # Fallback: calculate from current filtered nodes if no cached bounds
        if not self.nodes:
            return self._default_bounds()

        lats = [node.lat for node in self.nodes.values()]
        lons = [node.lon for node in self.nodes.values()]

        # Add buffer
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        lat_buffer = lat_range * 0.1 if lat_range > 0 else 0.01
        lon_buffer = lon_range * 0.1 if lon_range > 0 else 0.01

        return {
            "south": min(lats) - lat_buffer,
            "west": min(lons) - lon_buffer,
            "north": max(lats) + lat_buffer,
            "east": max(lons) + lon_buffer,
        }

    def _default_bounds(self) -> dict:
        """Return default bounds (Seattle area) if no data available."""
        return {"south": 47.6, "west": -122.4, "north": 47.7, "east": -122.2}

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM nodes")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.nodes)

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes."""
        return len(self.nodes)

    @property
    def way_count(self) -> int:
        """Get number of walkable OSM ways."""
        return len(self.ways)

    def get_nearby_nodes(
        self, lat: float, lon: float, radius_m: float = 100.0
    ) -> list[OSMNode]:
        """Get OSM nodes within a given radius of coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters

        Returns:
            List of nearby OSM nodes sorted by distance
        """
        # Use spatial index if available for efficient search
        if self.spatial_index is not None:
            # spatial index returns (node, distance) tuples already sorted by distance
            results = self.spatial_index.find_nearest_nodes(
                lat, lon, radius_m, max_results=1000
            )
            return [node for node, _ in results]

        # Fallback to linear search if no spatial index
        from .spatial import calculate_distance

        nearby_nodes = []
        for node in self.nodes.values():
            distance = calculate_distance(lat, lon, node.lat, node.lon)
            if distance <= radius_m:
                nearby_nodes.append(node)

        # Sort by distance
        nearby_nodes.sort(key=lambda n: calculate_distance(lat, lon, n.lat, n.lon))
        return nearby_nodes

    def get_ways_for_node(self, node_id: int) -> list[OSMWay]:
        """Get all walkable ways that reference a specific node.

        Args:
            node_id: OSM node ID

        Returns:
            List of OSMWay objects that reference the given node
        """
        if node_id not in self.node_way_index:
            return []

        # Use precomputed index for O(1) lookup
        ways = []
        way_ids_seen = set()  # Avoid duplicates if node appears multiple times
        for way, _ in self.node_way_index[node_id]:
            if way.id not in way_ids_seen:
                ways.append(way)
                way_ids_seen.add(way.id)

        return ways

    def get_node_positions_in_way(self, node_id: int, way: OSMWay) -> list[int]:
        """Get all position indices where a node appears in a specific way.

        Args:
            node_id: OSM node ID
            way: OSMWay object to search within

        Returns:
            List of position indices where the node appears in the way
        """
        if node_id not in self.node_way_index:
            return []

        # Find all positions for this node in the specific way
        positions = []
        for way_obj, position_index in self.node_way_index[node_id]:
            if way_obj.id == way.id:
                positions.append(position_index)

        return positions
