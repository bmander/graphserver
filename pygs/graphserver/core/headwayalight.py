from .edgepayload import EdgePayload
from ..gsdll import c_int, c_void_p, cproperty, lgs
from .servicecalendar import ServiceCalendar
from .timezone import Timezone


class HeadwayAlight(EdgePayload):
    calendar = cproperty(lgs.haGetCalendar, c_void_p, ServiceCalendar)
    timezone = cproperty(lgs.haGetTimezone, c_void_p, Timezone)
    agency = cproperty(lgs.haGetAgency, c_int)
    int_service_id = cproperty(lgs.haGetServiceId, c_int)

    @property
    def trip_id(self):
        self.check_destroyed()
        raw_trip_id = lgs.haGetTripId(c_void_p(self.soul))
        if raw_trip_id:
            if isinstance(raw_trip_id, bytes):
                return raw_trip_id.decode("utf-8")
            return raw_trip_id
        return None

    start_time = cproperty(lgs.haGetStartTime, c_int)
    end_time = cproperty(lgs.haGetEndTime, c_int)
    headway_secs = cproperty(lgs.haGetHeadwaySecs, c_int)

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

        # Encode string to bytes for ctypes compatibility in Python 3
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
            '<HeadwayAlight calendar=%s timezone=%s agency=%d service_id=%d trip_id="%s" start_time=%d end_time=%d headway_secs=%d>'
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

        ret = HeadwayAlight(
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


HeadwayAlight._cnew = lgs.haNew
HeadwayAlight._cdel = lgs.haDestroy
HeadwayAlight._cwalk = lgs.epWalk

EdgePayload.register_subclass(13, HeadwayAlight)
