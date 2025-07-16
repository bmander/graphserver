from ..gsdll import c_long, c_void_p, cproperty, lgs
from .edgepayload import EdgePayload


class ElapseTime(EdgePayload):
    seconds = cproperty(lgs.elapseTimeGetSeconds, c_long)

    def __init__(self, seconds):
        self.soul = self._cnew(seconds)

    def to_xml(self):
        self.check_destroyed()

        return "<ElapseTime seconds='%ld' />" % (self.seconds)

    def __getstate__(self):
        return self.seconds

    @classmethod
    def reconstitute(cls, state, resolver):
        return cls(state)


ElapseTime._cnew = lgs.elapseTimeNew
ElapseTime._cdel = lgs.elapseTimeDestroy
ElapseTime._cwalk = lgs.elapseTimeWalk
ElapseTime._cwalk_back = lgs.elapseTimeWalkBack

EdgePayload.register_subclass(14, ElapseTime)
