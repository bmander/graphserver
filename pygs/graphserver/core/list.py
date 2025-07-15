from ..gsdll import CShadow, ccast, lgs


class ListNode(CShadow):
    def data(self, edgeclass):
        return edgeclass.from_pointer(lgs.liGetData(self.soul))

    @property
    def next(self):
        return self._cnext(self.soul)


ListNode._cnext = ccast(lgs.liGetNext, ListNode)
