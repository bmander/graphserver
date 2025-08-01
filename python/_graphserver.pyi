from collections.abc import Sequence

from graphserver.core import Edge, EdgeProvider, Engine, EngineStats, Vertex

__version__: str


def create_engine(*, enable_edge_caching: bool = False) -> Engine: ...


def register_provider(engine: Engine, name: str, provider: EdgeProvider) -> None: ...


def plan(
    engine: Engine,
    start: Vertex,
    goal: Vertex,
    planner: str = "dijkstra",
) -> Sequence[tuple[Edge | None, Vertex]]: ...


def get_engine_stats(engine: Engine) -> EngineStats: ...


def precache_subgraph(
    *,
    engine: Engine,
    provider_name: str,
    seed_vertices: Sequence[Vertex],
    max_depth: int,
    max_vertices: int,
) -> None: ...
