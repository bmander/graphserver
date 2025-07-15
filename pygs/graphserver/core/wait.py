from .edgepayload import EdgePayload


class Wait(EdgePayload):
    end = cproperty(lgs.waitGetEnd, c_long)
    timezone = cproperty(lgs.waitGetTimezone, c_void_p, Timezone)

    def __init__(self, end, timezone):
        self.soul = self._cnew(end, timezone.soul)

    def to_xml(self):
        self.check_destroyed()

        return "<Wait end='%ld' />" % (self.end)

    def __getstate__(self):
        return (self.end, self.timezone.soul)


Wait._cnew = lgs.waitNew
Wait._cdel = lgs.waitDestroy
Wait._cwalk = lgs.waitWalk
Wait._cwalk_back = lgs.waitWalkBack

EdgePayload.register_subclass(6, Wait)
