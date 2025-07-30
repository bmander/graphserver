from collections.abc import Sequence

class Location:
    lat: float
    lon: float

class Tag:
    k: str
    v: str

class NodeRef:
    ref: int

class Node:
    id: int
    location: Location
    tags: Sequence[Tag]

class Way:
    id: int
    tags: Sequence[Tag]
    nodes: Sequence[NodeRef]

class Relation:
    id: int
    tags: Sequence[Tag]

class SimpleHandler:
    def node(self, n: Node) -> None: ...
    def way(self, w: Way) -> None: ...
    def relation(self, r: Relation) -> None: ...
    def apply_file(self, filename: str) -> None: ...

def apply(handler: SimpleHandler, filename: str) -> None: ...
