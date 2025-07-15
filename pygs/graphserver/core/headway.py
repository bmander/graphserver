from .edgepayload import EdgePayload
from ..gsdll import c_int, c_void_p, cproperty, lgs
from .servicecalendar import ServiceCalendar
from .timezone import Timezone
from .util import ServiceIdType


class Headway(EdgePayload):
    begin_time = cproperty(lgs.headwayBeginTime, c_int)
    end_time = cproperty(lgs.headwayEndTime, c_int)
    wait_period = cproperty(lgs.headwayWaitPeriod, c_int)
    transit = cproperty(lgs.headwayTransit, c_int)

    @property
    def trip_id(self):
        self.check_destroyed()
        raw_trip_id = lgs.headwayTripId(c_void_p(self.soul))
        if raw_trip_id:
            if isinstance(raw_trip_id, bytes):
                return raw_trip_id.decode("utf-8")
            return raw_trip_id
        return None

    calendar = cproperty(lgs.headwayCalendar, c_void_p, ServiceCalendar)
    timezone = cproperty(lgs.headwayTimezone, c_void_p, Timezone)
    agency = cproperty(lgs.headwayAgency, c_int)
    int_service_id = cproperty(lgs.headwayServiceId, c_int)

    def __init__(
        self,
        begin_time,
        end_time,
        wait_period,
        transit,
        trip_id,
        calendar,
        timezone,
        agency,
        service_id,
    ):
        if not isinstance(service_id, str):
            raise TypeError("service_id is supposed to be a string")

        int_sid = calendar.get_service_id_int(service_id)

        self.soul = lgs.headwayNew(
            begin_time,
            end_time,
            wait_period,
            transit,
            trip_id.encode("ascii"),
            calendar.soul,
            timezone.soul,
            c_int(agency),
            ServiceIdType(int_sid),
        )

    @property
    def service_id(self):
        return self.calendar.get_service_id_string(self.int_service_id)

    def to_xml(self):
        return (
            "<Headway begin_time='%d' end_time='%d' wait_period='%d' transit='%d' trip_id='%s' agency='%d' int_service_id='%d' />"
            % (
                self.begin_time,
                self.end_time,
                self.wait_period,
                self.transit,
                self.trip_id,
                self.agency,
                self.int_service_id,
            )
        )

    def __getstate__(self):
        return (
            self.begin_time,
            self.end_time,
            self.wait_period,
            self.transit,
            self.trip_id,
            self.calendar.soul,
            self.timezone.soul,
            self.agency,
            self.calendar.get_service_id_string(self.int_service_id),
        )


EdgePayload.register_subclass(7, Headway)
