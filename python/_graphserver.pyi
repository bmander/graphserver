from collections.abc import Sequence
from typing import Any

from graphserver.core import Edge, EngineStats, Vertex

__version__: str

def create_engine(*, enable_edge_caching: bool = False) -> Any: ...
def register_provider(engine: Any, name: str, provider: Any) -> None: ...
def plan(
    engine: Any,
    start: Vertex,
    goal: Vertex,
    planner: str = "dijkstra",
) -> Sequence[tuple[Edge | None, Vertex]]: ...
def get_engine_stats(engine: Any) -> EngineStats: ...
def precache_subgraph(
    *,
    engine: Any,
    provider_name: str,
    seed_vertices: Sequence[Vertex],
    max_depth: int,
    max_vertices: int,
) -> None: ...
