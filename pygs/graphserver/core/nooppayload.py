class NoOpPyPayload(GenericPyPayload):
    def __init__(self, num):
        self.num = num
        super(NoOpPyPayload, self).__init__()

    """ Dummy class."""

    def walk_impl(self, state, walkopts):
        print("%s walking..." % self)

    def walk_back_impl(self, state, walkopts):
        print("%s walking back..." % self)

    def to_xml(self):
        return "<NoOpPyPayload type='%s' num='%s'/>" % (self.type, self.num)
