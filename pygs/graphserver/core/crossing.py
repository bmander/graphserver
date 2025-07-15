from ..gsdll import lgs
from .edgepayload import EdgePayload


class Crossing(EdgePayload):
    def __init__(self):
        self.soul = self._cnew()

    def add_crossing_time(self, trip_id, crossing_time):
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        lgs.crAddCrossingTime(self.soul, trip_id, crossing_time)

    def get_crossing_time(self, trip_id):
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        ret = lgs.crGetCrossingTime(self.soul, trip_id)
        if ret == -1:
            return None
        return ret

    def get_crossing(self, i):
        trip_id = lgs.crGetCrossingTimeTripIdByIndex(self.soul, i)
        crossing_time = lgs.crGetCrossingTimeByIndex(self.soul, i)

        if crossing_time == -1:
            return None

        if isinstance(trip_id, bytes):
            trip_id = trip_id.decode("utf-8")

        return (trip_id, crossing_time)

    @property
    def size(self):
        return lgs.crGetSize(self.soul)

    def get_all_crossings(self):
        for i in range(self.size):
            yield self.get_crossing(i)

    def to_xml(self):
        return '<Crossing size="%d"/>' % self.size

    def __getstate__(self):
        return list(self.get_all_crossings())

    @classmethod
    def reconstitute(cls, state, resolver):
        ret = Crossing()

        for trip_id, crossing_time in state:
            ret.add_crossing_time(trip_id, crossing_time)

        return ret

    def expound(self):
        ret = []

        ret.append("Crossing")

        for trip_id, crossing_time in self.get_all_crossings():
            ret.append("%s: %s" % (trip_id, crossing_time))

        return "\n".join(ret)

    def __repr__(self):
        return "<Crossing %s>" % list(self.get_all_crossings())


Crossing._cnew = lgs.crNew
Crossing._cdel = lgs.crDestroy

EdgePayload.register_subclass(9, Crossing)
