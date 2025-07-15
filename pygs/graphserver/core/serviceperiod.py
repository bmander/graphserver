from ctypes import POINTER, byref, c_int, c_long, cast

from ..gsdll import CShadow, ccast, cproperty, lgs
from .util import ServiceIdType


class ServicePeriod(CShadow):
    begin_time = cproperty(lgs.spBeginTime, c_long)
    end_time = cproperty(lgs.spEndTime, c_long)

    def __init__(self, begin_time, end_time, service_ids):
        n, sids = ServicePeriod._py2c_service_ids(service_ids)
        self.soul = self._cnew(begin_time, end_time, n, sids)

    @property
    def service_ids(self):
        count = c_int()
        ptr = lgs.spServiceIds(self.soul, byref(count))
        ptr = cast(ptr, POINTER(ServiceIdType))
        ids = []
        for i in range(count.value):
            ids.append(ptr[i])
        return ids

    @property
    def previous(self):
        return self._cprev(self.soul)

    @property
    def next(self):
        return self._cnext(self.soul)

    def rewind(self):
        return self._crewind(self.soul)

    def fast_forward(self):
        return self._cfast_forward(self.soul)

    def __str__(self):
        return self.to_xml()

    def to_xml(self, cal=None):
        if cal is not None:
            sids = [cal.get_service_id_string(x) for x in self.service_ids]
        else:
            sids = [str(x) for x in self.service_ids]

        return "<ServicePeriod begin_time='%d' end_time='%d' service_ids='%s'/>" % (
            self.begin_time,
            self.end_time,
            ",".join(sids),
        )

    def datum_midnight(self, timezone_offset):
        return lgs.spDatumMidnight(self.soul, timezone_offset)

    def normalize_time(self, timezone_offset, time):
        return lgs.spNormalizeTime(self.soul, timezone_offset, time)

    def __getstate__(self):
        return (self.begin_time, self.end_time, self.service_ids)

    def __setstate__(self, state):
        self.__init__(*state)

    def __repr__(self):
        return "(%s %s->%s)" % (self.service_ids, self.begin_time, self.end_time)

    @staticmethod
    def _py2c_service_ids(service_ids):
        ns = len(service_ids)
        asids = (ServiceIdType * ns)()
        for i in range(ns):
            asids[i] = ServiceIdType(service_ids[i])
        return (ns, asids)


ServicePeriod._cnew = lgs.spNew
ServicePeriod._crewind = ccast(lgs.spRewind, ServicePeriod)
ServicePeriod._cfast_forward = ccast(lgs.spFastForward, ServicePeriod)
ServicePeriod._cnext = ccast(lgs.spNextPeriod, ServicePeriod)
ServicePeriod._cprev = ccast(lgs.spPreviousPeriod, ServicePeriod)
