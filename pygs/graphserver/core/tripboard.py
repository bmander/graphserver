from ctypes import c_int, c_long, py_object, pythonapi

from ..gsdll import c_void_p, cproperty, lgs
from .edgepayload import EdgePayload
from .servicecalendar import ServiceCalendar
from .timezone import Timezone
from .util import indent, unparse_secs


class TripBoard(EdgePayload):
    calendar = cproperty(lgs.tbGetCalendar, c_void_p, ServiceCalendar)
    timezone = cproperty(lgs.tbGetTimezone, c_void_p, Timezone)
    agency = cproperty(lgs.tbGetAgency, c_int)
    int_service_id = cproperty(lgs.tbGetServiceId, c_int)
    num_boardings = cproperty(lgs.tbGetNumBoardings, c_int)
    overage = cproperty(lgs.tbGetOverage, c_int)

    def __init__(self, service_id, calendar, timezone, agency):
        service_id = (
            service_id
            if isinstance(service_id, int)
            else calendar.get_service_id_int(service_id)
        )

        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)

    @property
    def service_id(self):
        return self.calendar.get_service_id_string(self.int_service_id)

    def add_boarding(self, trip_id, depart, stop_sequence):
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        self._cadd_boarding(self.soul, trip_id, depart, stop_sequence)

    def get_boarding(self, i):
        trip_id = lgs.tbGetBoardingTripId(self.soul, c_int(i))
        depart = lgs.tbGetBoardingDepart(self.soul, c_int(i))
        stop_sequence = lgs.tbGetBoardingStopSequence(self.soul, c_int(i))

        if trip_id is None:
            raise IndexError("Index %d out of bounds" % i)

        if isinstance(trip_id, bytes):
            trip_id = trip_id.decode("utf-8")

        return (trip_id, depart, stop_sequence)

    def get_boarding_by_trip_id(self, trip_id):
        # Encode string to bytes for ctypes compatibility in Python 3
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        boarding_index = lgs.tbGetBoardingIndexByTripId(self.soul, trip_id)

        if boarding_index == -1:
            return None

        return self.get_boarding(boarding_index)

    def search_boardings_list(self, time):
        return lgs.tbSearchBoardingsList(self.soul, c_int(time))

    def get_next_boarding_index(self, time):
        return lgs.tbGetNextBoardingIndex(self.soul, c_int(time))

    def get_next_boarding(self, time):
        i = self.get_next_boarding_index(time)

        if i == -1:
            return None
        else:
            return self.get_boarding(i)

    def to_xml(self):
        return "<TripBoard />"

    def __repr__(self):
        return (
            "<TripBoard int_sid=%d sid=%s agency=%d calendar=%s timezone=%s boardings=%s>"
            % (
                self.int_service_id,
                self.calendar.get_service_id_string(self.int_service_id),
                self.agency,
                hex(self.calendar.soul),
                hex(self.timezone.soul),
                [self.get_boarding(i) for i in range(self.num_boardings)],
            )
        )

    def __getstate__(self):
        state = {}
        state["calendar"] = self.calendar.soul
        state["timezone"] = self.timezone.soul
        state["agency"] = self.agency
        state["int_sid"] = self.int_service_id
        boardings = []
        for i in range(self.num_boardings):
            boardings.append(self.get_boarding(i))
        state["boardings"] = boardings
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

        ret = TripBoard(int_sid, calendar, timezone, agency)

        for trip_id, depart, stop_sequence in state["boardings"]:
            ret.add_boarding(trip_id, depart, stop_sequence)

        return ret

    def expound(self):
        boardingstrs = []

        for i in range(self.num_boardings):
            trip_id, departure_secs, stop_sequence = self.get_boarding(i)
            boardingstrs.append(
                "on trip id='%s' at %s, stop sequence %s"
                % (trip_id, unparse_secs(departure_secs), stop_sequence)
            )

        ret = """TripBoard
   agency (internal id): %d
   service_id (internal id): %d
   calendar:
%s
   timezone:
%s
   boardings:
%s""" % (
            self.agency,
            self.int_service_id,
            indent(self.calendar.expound("America/Chicago"), 6),
            indent(self.timezone.expound(), 6),
            indent("\n".join(boardingstrs), 6),
        )

        return ret


TripBoard._cnew = lgs.tbNew
TripBoard._cdel = lgs.tbDestroy
TripBoard._cadd_boarding = lgs.tbAddBoarding
TripBoard._cwalk = lgs.epWalk

EdgePayload.register_subclass(8, TripBoard)
