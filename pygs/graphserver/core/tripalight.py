from .edgepayload import EdgePayload


class TripAlight(EdgePayload):
    calendar = cproperty(lgs.alGetCalendar, c_void_p, ServiceCalendar)
    timezone = cproperty(lgs.alGetTimezone, c_void_p, Timezone)
    agency = cproperty(lgs.alGetAgency, c_int)
    int_service_id = cproperty(lgs.alGetServiceId, c_int)
    num_alightings = cproperty(lgs.alGetNumAlightings, c_int)
    overage = cproperty(lgs.tbGetOverage, c_int)

    def __init__(self, service_id, calendar, timezone, agency):
        service_id = (
            service_id
            if isinstance(service_id, int)
            else calendar.get_service_id_int(service_id)
        )

        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)

    def add_alighting(self, trip_id, arrival, stop_sequence):
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        lgs.alAddAlighting(self.soul, trip_id, arrival, stop_sequence)

    def get_alighting(self, i):
        trip_id = lgs.alGetAlightingTripId(self.soul, c_int(i))
        arrival = lgs.alGetAlightingArrival(self.soul, c_int(i))
        stop_sequence = lgs.alGetAlightingStopSequence(self.soul, c_int(i))

        if trip_id is None:
            raise IndexError("Index %d out of bounds" % i)

        if isinstance(trip_id, bytes):
            trip_id = trip_id.decode("utf-8")

        return (trip_id, arrival, stop_sequence)

    @property
    def alightings(self):
        for i in range(self.num_alightings):
            yield self.get_alighting(i)

    def search_alightings_list(self, time):
        return lgs.alSearchAlightingsList(self.soul, c_int(time))

    def get_last_alighting_index(self, time):
        return lgs.alGetLastAlightingIndex(self.soul, c_int(time))

    def get_last_alighting(self, time):
        i = self.get_last_alighting_index(time)

        if i == -1:
            return None
        else:
            return self.get_alighting(i)

    def get_alighting_by_trip_id(self, trip_id):
        # Encode string to bytes for ctypes compatibility in Python 3
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        alighting_index = lgs.alGetAlightingIndexByTripId(self.soul, trip_id)

        if alighting_index == -1:
            return None

        return self.get_alighting(alighting_index)

    def to_xml(self):
        return "<TripAlight/>"

    def __repr__(self):
        return (
            "<TripAlight int_sid=%d agency=%d calendar=%s timezone=%s alightings=%s>"
            % (
                self.int_service_id,
                self.agency,
                hex(self.calendar.soul),
                hex(self.timezone.soul),
                [self.get_alighting(i) for i in range(self.num_alightings)],
            )
        )

    def __getstate__(self):
        state = {}
        state["calendar"] = self.calendar.soul
        state["timezone"] = self.timezone.soul
        state["agency"] = self.agency
        state["int_sid"] = self.int_service_id
        alightings = []
        for i in range(self.num_alightings):
            alightings.append(self.get_alighting(i))
        state["alightings"] = alightings
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

        ret = TripAlight(int_sid, calendar, timezone, agency)

        for trip_id, arrival, stop_sequence in state["alightings"]:
            ret.add_alighting(trip_id, arrival, stop_sequence)

        return ret

    def expound(self):
        alightingstrs = []

        for i in range(self.num_alightings):
            trip_id, arrival_secs, stop_sequence = self.get_alighting(i)
            alightingstrs.append(
                "on trip id='%s' at %s, stop sequence %s"
                % (trip_id, unparse_secs(arrival_secs), stop_sequence)
            )

        ret = """TripAlight
   agency (internal id): %d
   service_id (internal id): %d
   calendar:
%s
   timezone:
%s
   alightings:
%s""" % (
            self.agency,
            self.int_service_id,
            indent(self.calendar.expound("America/Chicago"), 6),
            indent(self.timezone.expound(), 6),
            indent("\n".join(alightingstrs), 6),
        )

        return ret


TripAlight._cnew = lgs.alNew
TripAlight._cdel = lgs.alDestroy

EdgePayload.register_subclass(10, TripAlight)
