from ctypes import c_char_p, c_double, c_int, c_long
from time import time as now

from ..gsdll import CShadow, ccast, cproperty, lgs
from .serviceperiod import ServicePeriod


class State(CShadow):
    def __init__(self, n_agencies, time=None):
        if time is None:
            time = now()
        self.soul = self._cnew(n_agencies, int(time))

    def service_period(self, agency):
        soul = lgs.stateServicePeriod(self.soul, agency)
        return ServicePeriod.from_pointer(soul)

    def set_service_period(self, agency, sp):
        if agency > self.num_agencies - 1:
            raise Exception("Agency index %d out of bounds" % agency)

        lgs.stateSetServicePeriod(self.soul, c_int(agency), sp.soul)

    def destroy(self):
        self.check_destroyed()

        self._cdel(self.soul)
        self.soul = None

    def __copy__(self):
        self.check_destroyed()

        return self._ccopy(self.soul)

    def clone(self):
        self.check_destroyed()

        return self.__copy__()

    def __str__(self):
        self.check_destroyed()

        return self.to_xml()

    def to_xml(self):
        self.check_destroyed()

        ret = (
            "<state time='%d' weight='%s' dist_walked='%s' "
            "num_transfers='%s' trip_id='%s' stop_sequence='%s'>"
            % (
                self.time,
                self.weight,
                self.dist_walked,
                self.num_transfers,
                self.trip_id,
                self.stop_sequence,
            )
        )
        for i in range(self.num_agencies):
            if self.service_period(i) is not None:
                ret += self.service_period(i).to_xml()
        return ret + "</state>"

    # the state does not keep ownership of the trip_id, so the state
    # may not live longer than whatever object set its trip_id
    def dangerous_set_trip_id(self, trip_id):
        if isinstance(trip_id, str):
            trip_id = trip_id.encode("utf-8")
        lgs.stateDangerousSetTripId(self.soul, trip_id)

    time = cproperty(lgs.stateGetTime, c_long, setter=lgs.stateSetTime)
    weight = cproperty(lgs.stateGetWeight, c_long, setter=lgs.stateSetWeight)
    dist_walked = cproperty(
        lgs.stateGetDistWalked, c_double, setter=lgs.stateSetDistWalked
    )
    num_transfers = cproperty(
        lgs.stateGetNumTransfers, c_int, setter=lgs.stateSetNumTransfers
    )

    def _get_prev_edge(self):
        from .edgepayload import EdgePayload

        return EdgePayload.from_pointer(lgs.stateGetPrevEdge(self.soul))

    def _set_prev_edge(self, value):
        lgs.stateSetPrevEdge(self.soul, value.soul if hasattr(value, "soul") else value)

    prev_edge = property(_get_prev_edge, _set_prev_edge)
    num_agencies = cproperty(lgs.stateGetNumAgencies, c_int)
    trip_id = cproperty(lgs.stateGetTripId, c_char_p)
    stop_sequence = cproperty(lgs.stateGetStopSequence, c_int)


State._cnew = lgs.stateNew
State._cdel = lgs.stateDestroy
State._ccopy = ccast(lgs.stateDup, State)
