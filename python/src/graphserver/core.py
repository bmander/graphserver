from __future__ import annotations

from collections.abc import ItemsView, Iterator, KeysView, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# Type alias for graphserver vertex data values
GraphserverDataType = str | int | float

# Import will be available after C extension is built
try:
    from . import _graphserver  # type: ignore[attr-defined]
except ImportError:
    try:
        import _graphserver
    except ImportError:
        # Graceful handling during development
        _graphserver = None


class Vertex:
    """Immutable vertex object representing a state in the planning graph.

    Provides dictionary-like read-only access with square bracket syntax for
    getting vertex attributes. Once created, vertex data cannot be modified.
    """

    def __init__(
        self, data: Mapping[str, Any] | None = None, *, hash_value: int | None = None
    ) -> None:
        """Initialize immutable vertex with optional data and hash.

        Args:
            data: Initial vertex attributes as key-value pairs
            hash_value: Optional pre-computed hash value for this vertex
        """
        # Extract _hash from data if present and hash_value not explicitly provided
        if data and "_hash" in data and hash_value is None:
            data_dict = dict(data)
            hash_value = data_dict.pop("_hash")
            self._data: dict[str, Any] = data_dict
        else:
            self._data = dict(data) if data else {}

        self._custom_hash: int | None = hash_value

    def __getitem__(self, key: str) -> Any:
        """Get vertex attribute using square bracket syntax.

        Args:
            key: Attribute name

        Returns:
            Attribute value

        Raises:
            KeyError: If attribute doesn't exist
        """
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Vertex is immutable - setting attributes is not allowed.

        Raises:
            TypeError: Always, since vertices are immutable
        """
        msg = "Vertex objects are immutable"
        raise TypeError(msg)

    def __contains__(self, key: str) -> bool:
        """Check if vertex has attribute."""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get vertex attribute with optional default.

        Args:
            key: Attribute name
            default: Default value if attribute doesn't exist

        Returns:
            Attribute value or default
        """
        return self._data.get(key, default)

    def keys(self) -> KeysView[str]:
        """Get all attribute names."""
        return self._data.keys()

    def items(self) -> ItemsView[str, Any]:
        """Get all attribute name-value pairs."""
        return self._data.items()

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain dictionary.

        Returns:
            Copy of vertex data as dictionary, including _hash if present
        """
        result = self._data.copy()
        if self._custom_hash is not None:
            result["_hash"] = self._custom_hash
        return result

    def __repr__(self) -> str:
        """String representation of vertex."""
        return f"Vertex({self._data!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another vertex."""
        if not isinstance(other, Vertex):
            return NotImplemented
        return self._data == other._data

    def __hash__(self) -> int:
        """Hash value for vertex based on its data or custom hash."""
        if self._custom_hash is not None:
            return self._custom_hash
        return hash(tuple(sorted(self._data.items())))


class Edge:
    """Edge object representing a transition between vertices.

    Contains cost information and optional metadata.
    """

    def __init__(
        self, cost: float | Sequence[float], metadata: Mapping[str, Any] | None = None
    ) -> None:
        """Initialize edge with cost and optional metadata.

        Args:
            cost: Edge cost (single value or multi-objective vector)
            metadata: Optional edge metadata as key-value pairs
        """
        self._cost = cost
        self._metadata: dict[str, Any] = dict(metadata) if metadata else {}

    @property
    def cost(self) -> float | Sequence[float]:
        """Edge cost (single value or multi-objective vector)."""
        return self._cost

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Read-only view of edge metadata."""
        return self._metadata.copy()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value with optional default.

        Args:
            key: Metadata key
            default: Default value if key doesn't exist

        Returns:
            Metadata value or default
        """
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self._metadata[key] = value

    def __repr__(self) -> str:
        """String representation of edge."""
        if self._metadata:
            return f"Edge(cost={self._cost!r}, metadata={self._metadata!r})"
        return f"Edge(cost={self._cost!r})"


# Type aliases for the new interface
VertexEdgePair = tuple[Vertex, Edge]


@runtime_checkable
class EdgeProvider(Protocol):
    """Protocol for edge provider functions."""

    def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate outgoing edges from a vertex.

        Args:
            vertex: Vertex object containing state data

        Returns:
            List of (target_vertex, edge) tuples for outgoing edges

        Raises:
            NotImplementedError: If provider does not support outgoing edges
        """
        ...

    def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate incoming edges to a vertex.

        Args:
            vertex: Vertex object containing state data

        Returns:
            List of (source_vertex, edge) tuples for incoming edges

        Raises:
            NotImplementedError: If provider does not support incoming edges
        """
        ...


@dataclass(frozen=True)
class EngineStats:
    """Engine statistics including cache performance metrics.

    This immutable dataclass contains comprehensive statistics about
    the planning engine's performance, including cache effectiveness.
    """

    vertices_expanded: int
    """Number of vertices expanded during planning."""

    edges_generated: int
    """Number of edges generated by providers."""

    providers_called: int
    """Number of provider calls made."""

    peak_memory_usage: int
    """Peak memory usage during planning in bytes."""

    cache_hits: int
    """Number of successful cache lookups."""

    cache_misses: int
    """Number of cache misses."""

    cache_puts: int
    """Number of entries stored in cache."""

    @property
    def total_cache_operations(self) -> int:
        """Total cache operations (hits + misses + puts)."""
        return self.cache_hits + self.cache_misses + self.cache_puts

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage (0.0-100.0), or 0.0 if no cache operations."""
        total_lookups = self.cache_hits + self.cache_misses
        if total_lookups == 0:
            return 0.0
        return (self.cache_hits / total_lookups) * 100.0


class Engine:
    """Graphserver planning engine with Python edge provider support.

    This class provides a modern Python interface to the high-performance
    C-based Graphserver planning engine. Edge providers can be written in
    Python for maximum flexibility.
    """

    def __init__(
        self,
        *,
        config: Mapping[str, Any] | None = None,
        enable_edge_caching: bool = False,
    ) -> None:
        """Create new planning engine.

        Args:
            config: Optional engine configuration parameters
            enable_edge_caching: Enable edge caching for improved performance

        Raises:
            RuntimeError: If C extension is not available or engine creation fails
        """
        if _graphserver is None:
            msg = "C extension not available - ensure package is properly built"
            raise RuntimeError(msg)

        # Merge config parameters with cache setting
        merged_config = dict(config) if config else {}
        merged_config["enable_edge_caching"] = enable_edge_caching

        self._engine = _graphserver.create_engine(
            enable_edge_caching=enable_edge_caching
        )
        self._providers: dict[str, EdgeProvider] = {}
        self._config = merged_config

    def register_provider(self, name: str, provider: EdgeProvider) -> None:
        """Register a Python edge provider.

        Args:
            name: Unique name for the provider
            provider: EdgeProvider implementing out_edges and in_edges methods

        Raises:
            TypeError: If provider doesn't implement required methods
            RuntimeError: If registration fails
        """
        # Validate that provider has required methods
        if not hasattr(provider, "out_edges") or not callable(
            getattr(provider, "out_edges")
        ):
            msg = "Provider must implement out_edges method"
            raise TypeError(msg)

        if not hasattr(provider, "in_edges") or not callable(
            getattr(provider, "in_edges")
        ):
            msg = "Provider must implement in_edges method"
            raise TypeError(msg)

        if _graphserver is None:
            msg = "C extension not available"
            raise RuntimeError(msg)

        # Pass the provider object directly to the C extension
        # The C extension now supports bidirectional providers
        _graphserver.register_provider(self._engine, name, provider)
        self._providers[name] = provider

    def plan(
        self, *, start: Vertex, goal: Vertex, planner: str = "dijkstra"
    ) -> PathResult:
        """Execute pathfinding from start to goal.

        Args:
            start: Starting vertex object
            goal: Goal vertex object
            planner: Planning algorithm to use

        Returns:
            PathResult containing the found path

        Raises:
            TypeError: If start or goal are not Vertex objects
            RuntimeError: If planning fails
        """
        if not isinstance(start, Vertex):
            msg = "Start must be a Vertex object"
            raise TypeError(msg)
        if not isinstance(goal, Vertex):
            msg = "Goal must be a Vertex object"
            raise TypeError(msg)

        if _graphserver is None:
            msg = "C extension not available"
            raise RuntimeError(msg)

        result_data = _graphserver.plan(
            self._engine,
            start,
            goal,
            planner,
        )
        return PathResult(result_data)

    @property
    def providers(self) -> Mapping[str, EdgeProvider]:
        """Get read-only view of registered providers."""
        return self._providers.copy()

    def get_stats(self) -> EngineStats:
        """Get engine statistics including cache performance metrics.

        Returns:
            EngineStats containing comprehensive engine performance metrics:
            - vertices_expanded: Number of vertices expanded during planning
            - edges_generated: Number of edges generated by providers
            - providers_called: Number of provider calls made
            - peak_memory_usage: Peak memory usage in bytes
            - cache_hits: Number of cache hits (if caching enabled)
            - cache_misses: Number of cache misses (if caching enabled)
            - cache_puts: Number of cache storage operations (if caching enabled)

            Plus computed properties:
            - total_cache_operations: Sum of hits, misses, and puts
            - cache_hit_rate: Hit rate as percentage (0.0-100.0)

        Raises:
            RuntimeError: If C extension is not available or stats cannot be retrieved
        """
        if _graphserver is None:
            msg = "C extension not available"
            raise RuntimeError(msg)

        return _graphserver.get_engine_stats(self._engine)  # type: ignore[no-any-return]

    @property
    def cache_enabled(self) -> bool:
        """Check if edge caching is enabled for this engine.

        Returns:
            True if edge caching is enabled, False otherwise
        """
        return bool(self._config.get("enable_edge_caching", False))

    def precache_subgraph(
        self,
        *,
        provider_name: str,
        seed_vertices: Sequence[Vertex],
        max_depth: int = 0,
        max_vertices: int = 0,
    ) -> None:
        """Pre-cache a subgraph using breadth-first discovery.

        This method performs a breadth-first search starting from the given seed
        vertices, caching all discovered edges up to the specified limits.

        Args:
            provider_name: Name of the provider to cache from
            seed_vertices: Sequence of vertices to start discovery from
            max_depth: Maximum depth to traverse (0 = unlimited)
            max_vertices: Maximum vertices to discover (0 = unlimited)

        Raises:
            ValueError: If no seed vertices provided, provider not found,
                       or caching is disabled
            RuntimeError: If C extension is not available or precaching fails
            TypeError: If seed_vertices contains non-Vertex objects

        Example:
            >>> engine = Engine(enable_edge_caching=True)
            >>> engine.register_provider("grid", grid_provider)
            >>> seeds = [Vertex({"x": 0, "y": 0}), Vertex({"x": 10, "y": 10})]
            >>> engine.precache_subgraph(
            ...     provider_name="grid",
            ...     seed_vertices=seeds,
            ...     max_depth=5,
            ...     max_vertices=1000
            ... )
        """
        if not seed_vertices:
            msg = "At least one seed vertex is required"
            raise ValueError(msg)

        if not self.cache_enabled:
            msg = "Edge caching must be enabled to use precaching"
            raise ValueError(msg)

        # Validate that all seeds are Vertex objects
        for i, vertex in enumerate(seed_vertices):
            if not isinstance(vertex, Vertex):
                msg = f"Seed vertex at index {i} must be a Vertex object"
                raise TypeError(msg)

        if _graphserver is None:
            msg = "C extension not available"
            raise RuntimeError(msg)

        _graphserver.precache_subgraph(
            engine=self._engine,
            provider_name=provider_name,
            seed_vertices=seed_vertices,
            max_depth=max_depth,
            max_vertices=max_vertices,
        )


class PathResult:
    """Result of a pathfinding operation.

    Provides convenient access to path data with proper type annotations.
    """

    def __init__(self, path_data: Sequence[tuple[Edge | None, Vertex]]) -> None:
        """Initialize path result.

        Args:
            path_data: Sequence of (Edge|None, Vertex) tuples from C extension
        """
        # Convert (Edge|None, Vertex) tuples to PathEdge objects
        self._edges: list[PathEdge] = []

        # Skip the first tuple which is (None, start_vertex) and process the rest
        for i, (edge, target_vertex) in enumerate(path_data):
            if i == 0:
                # First tuple is (None, start_vertex) - skip it as PathResult
                # represents the edges taken, not the vertices visited
                continue

            # For all other tuples, edge should not be None
            if edge is None:
                msg = f"Edge at index {i} cannot be None (except for start vertex)"
                raise ValueError(msg)

            self._edges.append(PathEdge(target=target_vertex, edge=edge))

    def __len__(self) -> int:
        """Get number of edges in path."""
        return len(self._edges)

    def __iter__(self) -> Iterator[PathEdge]:
        """Iterate over edges in path."""
        return iter(self._edges)

    def __getitem__(self, index: int) -> PathEdge:
        """Get edge at index."""
        return self._edges[index]

    @property
    def total_cost(self) -> float:
        """Calculate total cost of the path."""
        total = 0.0
        for path_edge in self._edges:
            cost = path_edge.edge.cost
            if isinstance(cost, int | float):
                total += float(cost)
            elif isinstance(cost, Sequence):
                # For multi-objective costs, use first component
                total += float(cost[0]) if cost else 0.0
        return total

    @property
    def edges(self) -> Sequence[PathEdge]:
        """Get read-only view of path edges."""
        return self._edges.copy()

    def __repr__(self) -> str:
        """String representation of path."""
        return f"PathResult(edges={len(self._edges)}, cost={self.total_cost})"


class PathEdge:
    """Edge in a path result, containing target vertex and edge information."""

    def __init__(self, target: Vertex, edge: Edge) -> None:
        """Initialize path edge.

        Args:
            target: Target vertex of the edge
            edge: Edge object with cost and metadata
        """
        self.target = target
        self.edge = edge

    def __repr__(self) -> str:
        """String representation of path edge."""
        return f"PathEdge(target={self.target!r}, edge={self.edge!r})"
