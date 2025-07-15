from ..gsdll import c_double, c_float, c_long, c_void_p, ccast, cproperty, lgs
from .edgepayload import EdgePayload


class Street(EdgePayload):
    length = cproperty(lgs.streetGetLength, c_double)

    @property
    def name(self):
        self.check_destroyed()
        raw_name = lgs.streetGetName(c_void_p(self.soul))
        if raw_name:
            if isinstance(raw_name, bytes):
                return raw_name.decode("utf-8")
            return raw_name
        return None

    rise = cproperty(lgs.streetGetRise, c_float, setter=lgs.streetSetRise)
    fall = cproperty(lgs.streetGetFall, c_float, setter=lgs.streetSetFall)
    slog = cproperty(lgs.streetGetSlog, c_float, setter=lgs.streetSetSlog)
    way = cproperty(lgs.streetGetWay, c_long, setter=lgs.streetSetWay)

    def __init__(self, name, length, rise=0, fall=0, reverse_of_source=False):
        # Encode string to bytes for ctypes compatibility in Python 3
        if isinstance(name, str):
            name = name.encode("utf-8")
        self.soul = self._cnew(name, length, rise, fall, reverse_of_source)

    def to_xml(self):
        self.check_destroyed()

        return (
            "<Street name='%s' length='%f' rise='%f' fall='%f' way='%ld' reverse='%s'/>"
            % (
                self.name,
                self.length,
                self.rise,
                self.fall,
                self.way,
                self.reverse_of_source,
            )
        )

    def __getstate__(self):
        return (
            self.name,
            self.length,
            self.rise,
            self.fall,
            self.slog,
            self.way,
            self.reverse_of_source,
        )

    def __setstate__(self, state):
        name, length, rise, fall, slog, way, reverse_of_source = state
        self.__init__(name, length, rise, fall, reverse_of_source)
        self.slog = slog
        self.way = way

    def __repr__(self):
        return "<Street name='%s' length=%f rise=%f fall=%f way=%ld reverse=%s>" % (
            self.name,
            self.length,
            self.rise,
            self.fall,
            self.way,
            self.reverse_of_source,
        )

    @classmethod
    def reconstitute(self, state, resolver):
        name, length, rise, fall, slog, way, reverse_of_source = state
        ret = Street(name, length, rise, fall, reverse_of_source)
        ret.slog = slog
        ret.way = way
        return ret

    @property
    def reverse_of_source(self):
        return lgs.streetGetReverseOfSource(self.soul) == 1


Street._cnew = lgs.streetNewElev
Street._cdel = lgs.streetDestroy
Street._cwalk = lgs.streetWalk
Street._cwalk_back = lgs.streetWalkBack

EdgePayload.register_subclass(0, Street)
