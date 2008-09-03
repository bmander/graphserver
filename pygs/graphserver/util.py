# What the HELL people

import calendar
class TimeHelpers:
    
    @classmethod
    def unix_time(self,year,month,day,hour,minute,second,offset=0):
        """When it is midnight in London, it is 4PM in Seattle: The offset is eight hours. In order
           to find the unix time of a local time in Seattle, take the unix time for the time in London.
           Then, increase the unix time by eight hours. At this time, it is 4PM in Seattle. Because
           Seattle is "behind" London, you will need to subtract the negative number in order to obtain
           the unix time of the local number. Thus:
           
           unix_time(local_time,offset) = london_unix_time(hours(local_time))-offset"""
        return calendar.timegm( (year,month,day,hour,minute,second) ) - offset
        
if __name__=='__main__':
    print TimeHelpers.unix_time(2008,8,27,12,0,0,-8*3600)