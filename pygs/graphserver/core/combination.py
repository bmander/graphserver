from functools import reduce
from typing import TYPE_CHECKING, Any, Generator

from ..gsdll import c_int, c_void_p, ccast, cproperty, lgs
from .edgepayload import EdgePayload

if TYPE_CHECKING:
    from ..graphdb import GraphDatabase


class Combination(EdgePayload):
    n = cproperty(lgs.comboN, c_int)

    def __init__(self, cap: int) -> None:
        self.soul = self._cnew(cap)

    def add(self, ep: EdgePayload) -> None:
        lgs.comboAdd(self.soul, ep.soul)

    def get(self, i: int) -> EdgePayload:
        return EdgePayload.from_pointer(lgs.comboGet(self.soul, i))

    def to_xml(self) -> str:
        self.check_destroyed()
        return "<Combination n=%d />" % self.n

    def __getstate__(self) -> list[Any]:
        return [self.get(i).soul for i in range(self.n)]

    @classmethod
    def reconstitute(cls, state: list[Any], graphdb: "GraphDatabase") -> "Combination":
        components = [graphdb.get_edge_payload(epid) for epid in state]

        ret = Combination(len(components))

        for component in components:
            ret.add(component)

        return ret

    @property
    def components(self) -> Generator[EdgePayload, None, None]:
        for i in range(self.n):
            yield self.get(i)

    def unpack(self) -> list[EdgePayload]:
        components_unpacked = []
        for component_to_unpack in self.components:
            if component_to_unpack.__class__ == Combination:
                components_unpacked.append(component_to_unpack.unpack())
            else:
                components_unpacked.append([component_to_unpack])
        return reduce(lambda x, y: x + y, components_unpacked)

    def expound(self) -> str:
        return "\n".join([str(x) for x in self.unpack()])


Combination._cnew = lgs.comboNew
Combination._cdel = lgs.comboDestroy
Combination._cwalk = lgs.comboWalk
Combination._cwalk_back = lgs.comboWalkBack

EdgePayload.register_subclass(15, Combination)
