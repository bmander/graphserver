from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable, Any
from collections.abc import Callable, Iterator, Mapping, Sequence

# Import will be available after C extension is built
try:
    import _graphserver  # type: ignore[import-untyped]
except ImportError:
    # Graceful handling during development
    _graphserver = None

# Type aliases for clarity
VertexData = Mapping[str, Any]
EdgeData = Mapping[str, Any]
Cost = float

@runtime_checkable
class EdgeProvider(Protocol):
    """Protocol for edge provider functions."""
    
    def __call__(self, vertex: VertexData) -> Sequence[EdgeData]:
        """Generate edges from a vertex.
        
        Args:
            vertex: Dictionary containing vertex state data
            
        Returns:
            List of edge dictionaries with 'target', 'cost', and optional 'metadata'
        """
        ...

class Engine:
    """Graphserver planning engine with Python edge provider support.
    
    This class provides a modern Python interface to the high-performance
    C-based Graphserver planning engine. Edge providers can be written in
    Python for maximum flexibility.
    """
    
    def __init__(self, *, config: Mapping[str, Any] | None = None) -> None:
        """Create new planning engine.
        
        Args:
            config: Optional engine configuration parameters
            
        Raises:
            RuntimeError: If C extension is not available or engine creation fails
        """
        if _graphserver is None:
            raise RuntimeError("C extension not available - ensure package is properly built")
        
        self._engine = _graphserver.create_engine()
        self._providers: dict[str, EdgeProvider] = {}
        self._config = dict(config) if config else {}
    
    def register_provider(
        self, 
        name: str, 
        provider: EdgeProvider
    ) -> None:
        """Register a Python function as an edge provider.
        
        Args:
            name: Unique name for the provider
            provider: Callable that generates edges from vertices
            
        Raises:
            ValueError: If provider is not callable
            RuntimeError: If registration fails
        """
        if not callable(provider):
            raise ValueError("Provider must be callable")
        
        if _graphserver is None:
            raise RuntimeError("C extension not available")
        
        _graphserver.register_provider(self._engine, name, provider)
        self._providers[name] = provider
    
    def plan(
        self, 
        *,
        start: VertexData, 
        goal: VertexData, 
        planner: str = "dijkstra"
    ) -> PathResult:
        """Execute pathfinding from start to goal.
        
        Args:
            start: Starting vertex state as dictionary
            goal: Goal vertex state as dictionary  
            planner: Planning algorithm to use
            
        Returns:
            PathResult containing the found path
            
        Raises:
            ValueError: If start or goal are invalid
            RuntimeError: If planning fails
        """
        if not isinstance(start, Mapping):
            raise ValueError("Start must be a mapping (dict-like)")
        if not isinstance(goal, Mapping):
            raise ValueError("Goal must be a mapping (dict-like)")
        
        if _graphserver is None:
            raise RuntimeError("C extension not available")
        
        # Phase 1: placeholder - actual implementation in Phase 2
        result_data = _graphserver.plan(self._engine, dict(start), dict(goal), planner)
        return PathResult(result_data)
    
    @property
    def providers(self) -> Mapping[str, EdgeProvider]:
        """Get read-only view of registered providers."""
        return self._providers.copy()

class PathResult:
    """Result of a pathfinding operation.
    
    Provides convenient access to path data with proper type annotations.
    """
    
    def __init__(self, path_data: Sequence[EdgeData]) -> None:
        """Initialize path result.
        
        Args:
            path_data: Sequence of edge dictionaries from C extension
        """
        self._edges = list(path_data)
    
    def __len__(self) -> int:
        """Get number of edges in path."""
        return len(self._edges)
    
    def __iter__(self) -> Iterator[EdgeData]:
        """Iterate over edges in path."""
        return iter(self._edges)
    
    def __getitem__(self, index: int) -> EdgeData:
        """Get edge at index."""
        return self._edges[index]
    
    @property
    def total_cost(self) -> Cost:
        """Calculate total cost of the path."""
        return sum(edge.get("cost", 0.0) for edge in self._edges)
    
    @property 
    def edges(self) -> Sequence[EdgeData]:
        """Get read-only view of path edges."""
        return self._edges.copy()
    
    def __repr__(self) -> str:
        """String representation of path."""
        return f"PathResult(edges={len(self._edges)}, cost={self.total_cost})"