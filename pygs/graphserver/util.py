import pytz
from datetime import datetime
import time
import sys

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
        
def withProgress(seq, modValue=100):
    c = -1

    for c, v in enumerate(seq):
        if (c+1) % modValue == 0: 
            sys.stdout.write("%s\r" % (c+1)) 
            sys.stdout.flush()
        yield v

    print("\nCompleted %s" % (c+1))
