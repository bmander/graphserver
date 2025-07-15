from ..gsdll import c_long, c_void_p, cproperty, lgs, CShadow

class TimezonePeriod(CShadow):
    begin_time = cproperty(lgs.tzpBeginTime, c_long)
    end_time = cproperty(lgs.tzpEndTime, c_long)
    utc_offset = cproperty(lgs.tzpUtcOffset, c_long)

    def __init__(self, begin_time, end_time, utc_offset):
        self.soul = lgs.tzpNew(begin_time, end_time, utc_offset)

    @property
    def next_period(self):
        return TimezonePeriod.from_pointer(lgs.tzpNextPeriod(self.soul))

    def time_since_midnight(self, time):
        return lgs.tzpTimeSinceMidnight(self.soul, c_long(int(time)))

    def __getstate__(self):
        return (self.begin_time, self.end_time, self.utc_offset)

    def __setstate__(self, state):
        self.__init__(*state)


class Timezone(CShadow):
    head = cproperty(lgs.tzHead, c_void_p, TimezonePeriod)

    def __init__(self):
        self.soul = lgs.tzNew()

    def destroy(self):
        self.check_destroyed()

        self._cdel(self.soul)
        self.soul = None

    def add_period(self, timezone_period):
        lgs.tzAddPeriod(self.soul, timezone_period.soul)

    def period_of(self, time):
        tzpsoul = lgs.tzPeriodOf(self.soul, time)
        return TimezonePeriod.from_pointer(tzpsoul)

    def utc_offset(self, time):
        ret = lgs.tzUtcOffset(self.soul, time)

        if ret == -360000:
            raise IndexError("%d lands within no timezone period" % time)

        return ret

    def time_since_midnight(self, time):
        ret = lgs.tzTimeSinceMidnight(self.soul, c_long(int(time)))

        if ret == -1:
            raise IndexError("%d lands within no timezone period" % time)

        return ret

    @classmethod
    def generate(cls, timezone_string):
        ret = Timezone()

        timezone = pytz.timezone(timezone_string)
        tz_periods = zip(
            timezone._utc_transition_times[:-1], timezone._utc_transition_times[1:]
        )

        # exclude last transition_info entry, as it corresponds with the last utc_transition_time, and not the last period as defined by the last two entries
        for tz_period, (utcoffset, dstoffset, periodname) in zip(
            tz_periods, timezone._transition_info[:-1]
        ):
            period_begin, period_end = [
                calendar.timegm((x.year, x.month, x.day, x.hour, x.minute, x.second))
                for x in tz_period
            ]
            period_end -= 1  # period_end is the last second the period is active, not the first second it isn't
            utcoffset = utcoffset.days * 24 * 3600 + utcoffset.seconds

            ret.add_period(TimezonePeriod(period_begin, period_end, utcoffset))

        return ret

    def __getstate__(self):
        ret = []
        curs = self.head
        while curs:
            ret.append(curs.__getstate__())
            curs = curs.next_period
        return ret

    def __setstate__(self, state):
        self.__init__()
        for tzpargs in state:
            self.add_period(TimezonePeriod(*tzpargs))

    def expound(self):
        return "Timezone"


Timezone._cdel = lgs.tzDestroy
