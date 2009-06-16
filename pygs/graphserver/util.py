import pytz
from datetime import datetime
import time

import calendar

SECS_IN_MINUTE = 60
SECS_IN_HOURS = 60*SECS_IN_MINUTE
SECS_IN_DAYS = 24*SECS_IN_HOURS

class TimeHelpers:
    
    @classmethod
    def unix_time(cls,year,month,day,hour,minute,second,offset=0):
        """When it is midnight in London, it is 4PM in Seattle: The offset is eight hours. In order
           to find the unix time of a local time in Seattle, take the unix time for the time in London.
           Then, increase the unix time by eight hours. At this time, it is 4PM in Seattle. Because
           Seattle is "behind" London, you will need to subtract the negative number in order to obtain
           the unix time of the local number. Thus:
           
           unix_time(local_time,offset) = london_unix_time(hours(local_time))-offset"""
        return calendar.timegm( (year,month,day,hour,minute,second) ) - offset
        
    @classmethod
    def localtime_to_unix(cls,year,month,day,hour,minute,second,timezone):
        dt = pytz.timezone(timezone).localize(datetime(year,month,day,hour,minute,second)).astimezone(pytz.utc)
        return calendar.timegm( (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) )
        
    @classmethod
    def datetime_to_unix(cls, dt):
        dt = dt.astimezone(pytz.utc)
        return calendar.timegm( (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) )
        
    @classmethod
    def create_localtime(cls,year,month,day,hour,minute,second,timezone):
        return pytz.timezone(timezone).localize(datetime(year,month,day,hour,minute,second))
        
    @classmethod
    def unix_to_localtime(cls,unixtime, timezone):
        tt = time.gmtime( unixtime )
        dt = pytz.utc.localize(datetime(tt[0],tt[1],tt[2],tt[3],tt[4],tt[5]))
        return dt.astimezone( pytz.timezone(timezone) )
        
    @classmethod
    def timedelta_to_seconds(cls,td):
        return td.days*SECS_IN_DAYS+td.seconds+td.microseconds/1000000.0
        
    @classmethod
    def unixtime_to_daytimes(cls,unixtime,timezone):
        dt = cls.unix_to_localtime(unixtime,timezone)
        ret = dt.hour*3600+dt.minute*60+dt.second
        return ret, ret+24*3600, ret+2*24*3600
        
        
def main_test():
    print TimeHelpers.localtime_to_unix(2008,10,12,6,0,0,"Europe/Paris")
    print TimeHelpers.unix_to_localtime(1199181360, "America/New_York") 
    print TimeHelpers.unixtime_to_daytimes(1219834260, "America/Los_Angeles")
    print TimeHelpers.unix_to_localtime(1221459000, "America/Chicago")
    print TimeHelpers.unixtime_to_daytimes(1230354000, "America/Chicago")
    assert TimeHelpers.unix_time(2008,8,27,12,0,0,-7*3600) == 1219863600
    assert TimeHelpers.localtime_to_unix(2008,8,27,12,0,0,"America/Los_Angeles") == 1219863600
    assert str(TimeHelpers.unix_to_localtime(1219863600, "America/Los_Angeles")) == "2008-08-27 12:00:00-07:00"

if __name__=='__main__':
    main_test()