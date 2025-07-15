from ..gsdll import c_double, c_void_p, ccast, cproperty, lgs
from .edgepayload import EdgePayload


class Egress(EdgePayload):
    length = cproperty(lgs.egressGetLength, c_double)

    @property
    def name(self):
        self.check_destroyed()
        raw_name = lgs.egressGetName(c_void_p(self.soul))
        if raw_name:
            if isinstance(raw_name, bytes):
                return raw_name.decode("utf-8")
            return raw_name
        return None

    def __init__(self, name, length):
        # Encode string to bytes for ctypes compatibility in Python 3
        if isinstance(name, str):
            name = name.encode("utf-8")
        self.soul = self._cnew(name, length)

    def to_xml(self):
        self.check_destroyed()

        return "<Egress name='%s' length='%f' />" % (self.name, self.length)

    def __getstate__(self):
        return (self.name, self.length)

    def __setstate__(self, state):
        self.__init__(*state)

    def __repr__(self):
        return "<Egress name='%s' length=%f>" % (self.name, self.length)

    @classmethod
    def reconstitute(self, state, resolver):
        return Egress(*state)


Egress._cnew = lgs.egressNew
Egress._cdel = lgs.egressDestroy
Egress._cwalk = lgs.egressWalk
Egress._cwalk_back = lgs.egressWalkBack

EdgePayload.register_subclass(12, Egress)
