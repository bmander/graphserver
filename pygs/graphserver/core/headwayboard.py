from ctypes import c_char_p

from ..gsdll import c_int, c_void_p, cproperty, lgs
from .edgepayload import EdgePayload
from .servicecalendar import ServiceCalendar
from .timezone import Timezone


class HeadwayBoard(EdgePayload):
    calendar = cproperty(lgs.hbGetCalendar, c_void_p, ServiceCalendar)
    timezone = cproperty(lgs.hbGetTimezone, c_void_p, Timezone)
    agency = cproperty(lgs.hbGetAgency, c_int)
    int_service_id = cproperty(lgs.hbGetServiceId, c_int)
    _trip_id = cproperty(lgs.hbGetTripId, c_char_p)
    start_time = cproperty(lgs.hbGetStartTime, c_int)
    end_time = cproperty(lgs.hbGetEndTime, c_int)
    headway_secs = cproperty(lgs.hbGetHeadwaySecs, c_int)

    @property
    def trip_id(self):
        raw_trip_id = self._trip_id
        if isinstance(raw_trip_id, bytes):
            return raw_trip_id.decode("utf-8")
        return raw_trip_id

    def __init__(
        self,
        service_id,
        calendar,
        timezone,
        agency,
        trip_id,
        start_time,
        end_time,
        headway_secs,
    ):
        service_id = (
            service_id
            if isinstance(service_id, int)
            else calendar.get_service_id_int(service_id)
        )

        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")

        self.soul = self._cnew(
            service_id,
            calendar.soul,
            timezone.soul,
            agency,
            trip_id,
            start_time,
            end_time,
            headway_secs,
        )

    def __repr__(self):
        return (
            '<HeadwayBoard calendar=%s timezone=%s agency=%d service_id=%d trip_id="%s" start_time=%d end_time=%d headway_secs=%d>'
            % (
                hex(self.calendar.soul),
                hex(self.timezone.soul),
                self.agency,
                self.int_service_id,
                self.trip_id,
                self.start_time,
                self.end_time,
                self.headway_secs,
            )
        )

    @property
    def service_id(self):
        return self.calendar.get_service_id_string(self.int_service_id)

    def __getstate__(self):
        state = {}
        state["calendar"] = self.calendar.soul
        state["timezone"] = self.timezone.soul
        state["agency"] = self.agency
        state["int_sid"] = self.int_service_id
        state["trip_id"] = self.trip_id
        state["start_time"] = self.start_time
        state["end_time"] = self.end_time
        state["headway_secs"] = self.headway_secs
        return state

    def __resources__(self):
        return (
            (str(self.calendar.soul), self.calendar),
            (str(self.timezone.soul), self.timezone),
        )

    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve(state["calendar"])
        timezone = resolver.resolve(state["timezone"])
        int_sid = state["int_sid"]
        agency = state["agency"]
        trip_id = state["trip_id"]
        start_time = state["start_time"]
        end_time = state["end_time"]
        headway_secs = state["headway_secs"]

        ret = HeadwayBoard(
            int_sid,
            calendar,
            timezone,
            agency,
            trip_id,
            start_time,
            end_time,
            headway_secs,
        )

        return ret


HeadwayBoard._cnew = lgs.hbNew
HeadwayBoard._cdel = lgs.hbDestroy
HeadwayBoard._cwalk = lgs.epWalk

EdgePayload.register_subclass(11, HeadwayBoard)
