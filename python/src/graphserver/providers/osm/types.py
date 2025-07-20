"""OSM Data Types and Structures

This module defines data structures for representing OpenStreetMap entities
and their relationships in the context of pedestrian pathfinding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OSMNode:
    """Represents an OSM node with geographic coordinates and attributes."""

    id: int
    lat: float
    lon: float
    tags: dict[str, str]

    def __post_init__(self) -> None:
        """Validate node data after initialization."""
        if not (-90.0 <= self.lat <= 90.0):
            msg = f"Invalid latitude: {self.lat}"
            raise ValueError(msg)
        if not (-180.0 <= self.lon <= 180.0):
            msg = f"Invalid longitude: {self.lon}"
            raise ValueError(msg)


@dataclass
class OSMWay:
    """Represents an OSM way with node references and attributes."""

    id: int
    node_refs: list[int]
    tags: dict[str, str]

    def __post_init__(self) -> None:
        """Validate way data after initialization."""
        if len(self.node_refs) < 2:
            msg = f"Way {self.id} must have at least 2 nodes"
            raise ValueError(msg)

    def is_walkable(self) -> bool:
        """Check if this way is suitable for pedestrian routing."""
        highway = self.tags.get("highway", "")

        # Explicitly walkable highway types
        walkable_highways = {
            "footway",
            "path",
            "steps",
            "pedestrian",
            "living_street",
            "residential",
            "unclassified",
            "service",
            "track",
        }

        if highway in walkable_highways:
            # Check for access restrictions
            foot = self.tags.get("foot", "")
            access = self.tags.get("access", "")

            return not (foot == "no" or access == "no")

        # Some primary/secondary roads may be walkable if they have sidewalks
        if highway in {"primary", "secondary", "tertiary"}:
            sidewalk = self.tags.get("sidewalk", "")
            return sidewalk in {"both", "left", "right", "yes"}

        return False

    def get_walking_speed(self) -> float:
        """Get appropriate walking speed for this way type in m/s."""
        highway = self.tags.get("highway", "")

        # Walking speeds in meters per second (roughly 1.4 m/s = 5 km/h baseline)
        speed_map = {
            "footway": 1.4,
            "path": 1.2,  # Slightly slower on unpaved paths
            "steps": 0.8,  # Much slower on stairs
            "pedestrian": 1.4,
            "living_street": 1.3,
            "residential": 1.3,
            "unclassified": 1.3,
            "service": 1.3,
            "track": 1.1,  # Slower on rough tracks
        }

        return speed_map.get(highway, 1.2)  # Default moderate speed


@dataclass
class OSMEdge:
    """Represents a walkable edge between two OSM nodes."""

    from_node_id: int
    to_node_id: int
    way_id: int
    distance_m: float
    duration_s: float
    tags: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate edge data after initialization."""
        if self.distance_m <= 0:
            msg = f"Distance must be positive: {self.distance_m}"
            raise ValueError(msg)
        if self.duration_s <= 0:
            msg = f"Duration must be positive: {self.duration_s}"
            raise ValueError(msg)


class WalkingProfile:
    """Configuration for pedestrian routing preferences."""

    def __init__(
        self,
        *,
        base_speed_ms: float = 1.4,  # 5 km/h in m/s
        avoid_stairs: bool = False,
        avoid_busy_roads: bool = True,
        max_detour_factor: float = 1.5,
    ) -> None:
        """Initialize walking profile.

        Args:
            base_speed_ms: Base walking speed in meters per second
            avoid_stairs: Whether to avoid stairs/steps
            avoid_busy_roads: Whether to avoid roads without dedicated pedestrian
                infrastructure
            max_detour_factor: Maximum detour factor compared to straight-line distance
        """
        self.base_speed_ms = base_speed_ms
        self.avoid_stairs = avoid_stairs
        self.avoid_busy_roads = avoid_busy_roads
        self.max_detour_factor = max_detour_factor

    def get_edge_cost(self, edge: OSMEdge, way: OSMWay) -> float:
        """Calculate cost for an edge based on walking profile preferences."""
        base_cost = edge.duration_s

        # Apply penalties based on preferences
        highway = way.tags.get("highway", "")

        if self.avoid_stairs and highway == "steps":
            base_cost *= 3.0  # Heavy penalty for stairs

        if self.avoid_busy_roads and highway in {"primary", "secondary", "tertiary"}:
            sidewalk = way.tags.get("sidewalk", "")
            if sidewalk not in {"both", "left", "right", "yes"}:
                base_cost *= 2.0  # Penalty for roads without sidewalks

        return base_cost
