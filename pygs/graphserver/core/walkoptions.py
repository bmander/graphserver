from ctypes import c_float, c_int

from ..gsdll import CShadow, cproperty, instantiate, lgs


class WalkOptions(CShadow):
    def __init__(self):
        self.soul = self._cnew()

    def destroy(self):
        self.check_destroyed()

        self._cdel(self.soul)
        self.soul = None

    @classmethod
    def from_pointer(cls, ptr):
        """Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None
        ret = instantiate(cls)
        ret.soul = ptr
        return ret

    transfer_penalty = cproperty(
        lgs.woGetTransferPenalty, c_int, setter=lgs.woSetTransferPenalty
    )
    turn_penalty = cproperty(lgs.woGetTurnPenalty, c_int, setter=lgs.woSetTurnPenalty)
    walking_speed = cproperty(
        lgs.woGetWalkingSpeed, c_float, setter=lgs.woSetWalkingSpeed
    )
    walking_reluctance = cproperty(
        lgs.woGetWalkingReluctance, c_float, setter=lgs.woSetWalkingReluctance
    )
    uphill_slowness = cproperty(
        lgs.woGetUphillSlowness, c_float, setter=lgs.woSetUphillSlowness
    )
    downhill_fastness = cproperty(
        lgs.woGetDownhillFastness, c_float, setter=lgs.woSetDownhillFastness
    )
    hill_reluctance = cproperty(
        lgs.woGetHillReluctance, c_float, setter=lgs.woSetHillReluctance
    )
    max_walk = cproperty(lgs.woGetMaxWalk, c_int, setter=lgs.woSetMaxWalk)
    walking_overage = cproperty(
        lgs.woGetWalkingOverage, c_float, setter=lgs.woSetWalkingOverage
    )


WalkOptions._cnew = lgs.woNew
WalkOptions._cdel = lgs.woDestroy
