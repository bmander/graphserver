from ctypes import c_int, c_void_p

from ..gsdll import CShadow, ccast, cproperty, lgs
from ..util import TimeHelpers
from .serviceperiod import ServicePeriod


class ServiceCalendar(CShadow):
    """Calendar provides a set of convient methods for dealing with the wrapper class ServicePeriod, which
    wraps a single node in the doubly linked list that represents a calendar in Graphserver.
    """

    head = cproperty(lgs.scHead, c_void_p, ServicePeriod)

    def __init__(self):
        self.soul = lgs.scNew()

    def destroy(self):
        self.check_destroyed()

        self._cdel(self.soul)
        self.soul = None

    def get_service_id_int(self, service_id):
        if not isinstance(service_id, str):
            raise TypeError("service_id is supposed to be a string")

        if isinstance(service_id, str):
            service_id = service_id.encode("utf-8")

        return lgs.scGetServiceIdInt(self.soul, service_id)

    def get_service_id_string(self, service_id):
        if not isinstance(service_id, int):
            raise TypeError("service_id is supposed to be an int, in this case")

        raw_result = lgs.scGetServiceIdString(self.soul, service_id)
        if raw_result:
            if isinstance(raw_result, bytes):
                return raw_result.decode("utf-8")
            return raw_result
        return None

    def add_period(self, begin_time, end_time, service_ids):
        sp = ServicePeriod(
            begin_time, end_time, [self.get_service_id_int(x) for x in service_ids]
        )

        lgs.scAddPeriod(self.soul, sp.soul)

    def period_of_or_after(self, time):
        soul = lgs.scPeriodOfOrAfter(self.soul, time)
        return ServicePeriod.from_pointer(soul)

    def period_of_or_before(self, time):
        soul = lgs.scPeriodOfOrBefore(self.soul, time)
        return ServicePeriod.from_pointer(soul)

    @property
    def periods(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next

    def to_xml(self):
        ret = ["<ServiceCalendar>"]
        for period in self.periods:
            ret.append(period.to_xml(self))
        ret.append("</ServiceCalendar>")
        return "".join(ret)

    def __getstate__(self):
        ret = []
        max_sid = -1
        curs = self.head
        while curs:
            start, end, sids = curs.__getstate__()
            for sid in sids:
                max_sid = max(max_sid, sid)
            sids = [self.get_service_id_string(sid) for sid in sids]

            ret.append((start, end, sids))
            curs = curs.next
        sids_list = [self.get_service_id_string(sid) for sid in range(max_sid + 1)]
        return (sids_list, ret)

    def __setstate__(self, state):
        self.__init__()
        sids_list, periods = state
        for sid in sids_list:
            self.get_service_id_int(sid)

        for p in periods:
            self.add_period(*p)

    def __repr__(self):
        return "<ServiceCalendar periods=%s>" % repr(list(self.periods))

    def expound(self, timezone_name):
        periodstrs = []

        for period in self.periods:
            begin_time = TimeHelpers.unix_to_localtime(period.begin_time, timezone_name)
            end_time = TimeHelpers.unix_to_localtime(period.end_time, timezone_name)
            service_ids = dict(
                [(id, self.get_service_id_string(id)) for id in period.service_ids]
            )
            periodstrs.append(
                "sids:%s active from %d (%s) to %d (%s)"
                % (
                    service_ids,
                    period.begin_time,
                    begin_time,
                    period.end_time,
                    end_time,
                )
            )

        return "\n".join(periodstrs)
