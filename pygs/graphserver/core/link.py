from ..gsdll import c_void_p, cproperty, lgs
from .edgepayload import EdgePayload


class Link(EdgePayload):
    @property
    def name(self):
        self.check_destroyed()
        raw_name = lgs.linkGetName(c_void_p(self.soul))
        if raw_name:
            if isinstance(raw_name, bytes):
                return raw_name.decode("utf-8")
            return raw_name
        return None

    def __init__(self):
        self.soul = self._cnew()

    def to_xml(self):
        self.check_destroyed()

        return "<Link name='%s'/>" % (self.name)

    def __getstate__(self):
        return tuple([])

    def __setstate__(self, state):
        self.__init__()

    @classmethod
    def reconstitute(self, state, resolver):
        return Link()


Link._cnew = lgs.linkNew
Link._cdel = lgs.linkDestroy
Link._cwalk = lgs.epWalk
Link._cwalk_back = lgs.linkWalkBack

EdgePayload.register_subclass(3, Link)
