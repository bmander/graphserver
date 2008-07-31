import transitfeed
import time
from pytz import timezone
import sys
import datetime
sys.path.append("../../..")
from graphserver.core import Graph, Street, CalendarDay, TripHopSchedule, Calendar, State
import csv
import calendar
import os
from datetime import date, timedelta

if transitfeed.__version__ != "1.1.5":
    raise Exception("transitfeed.__version__ != 1.1.5")
    
def parse_date(date):
    return (int(date[0:4]), int(date[4:6]), int(date[6:8]))

def get_service_ids(sched, date):
    sids = []
    
    if type(date)==datetime.date:
        date = "%0.4d%0.2d%0.2d"%(date.year,date.month,date.day)
        
    for sp in sched.GetServicePeriodList():
        start_date, end_date = sp.GetDateRange()
        
        # if date is in the service_period's date range
        if int(date) <= int(end_date) and int(date) >= int(start_date):
            runs = sp.day_of_week[ calendar.weekday( *parse_date(date) ) ]
            
            if date in sp.date_exceptions:
                if sp.date_exceptions[date]==1:
                    runs = True
                elif sp.date_exceptions[date]==2:
                    runs = False
                    
            if runs:
                sids.append( sp.service_id )
                
    return sids
    
def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)

class GTFSLoadable:
    def _triphops_from_stop(self, stop):
        ret = []
        
        for trip,ix in stop.trip_index:
            stoptimes = trip.GetStopTimes()
            if ix != len(stoptimes)-1:
                ret.append( (trip, stoptimes[ix], stoptimes[ix+1], trip.route_id ) )
            
        return ret
        
    def _group_triphops(self, raw_triphops):
        """Takes a bunch of tuples of (trip,stoptime,stoptime). Returns them grouped by trip.trip_id && trip.service_id"""
        
        #Get dictionary with keys corresponding to a destination stop_id,service_id pair, and initialize to []
        trip_ids = dict.fromkeys( ["%s+%s+%s"%(tov.stop.stop_id,trip.service_id,routeid) for trip,fromv,tov,routeid in raw_triphops] )
        for k in trip_ids.keys():
            trip_ids[k] = []
        
        #Sort the triphops into their buckets
        for trip,fromv,tov,routeid in raw_triphops:
            trip_ids["%s+%s+%s"%(tov.stop.stop_id,trip.service_id,routeid)].append( (trip,fromv,tov) )
            
        #Convert dict to list
        thss = trip_ids.values()
        
        #Sort each triphopschedule by trihop departure time
        for ths in thss:
            ths.sort(lambda x,y: cmp(x[1].departure_time,y[1].departure_time))
            
        return thss
        
    def _raw_triphopschedules_from_stop(self, stop):
        triphops = self._triphops_from_stop(stop)
        thss = self._group_triphops(triphops)
        
        return thss

    def _raw_calendar(self, sched):
        startdate, enddate = [ date( *parse_date(x) ) for x in sched.GetDateRange() ]
        
        return [ (currdate, get_service_ids( sched, currdate )) for currdate in iter_dates(startdate, enddate) ]
        
    def _date_to_secs(self, adate):
        return calendar.timegm( (adate.year,adate.month,adate.day,0,0,0,0,0,0) )
        
    def _is_dst(self, adate):
        return time.localtime( time.mktime((adate.year,adate.month,adate.day,0,0,0,0,0,-1)) )[-1]

    def load_gtfs(self, sched_or_datadir, prefix="gtfs", authority=0):
        
        if type(sched_or_datadir)==str:
            sched = transitfeed.Loader(sched_or_datadir).Load()
        else:
            sched = sched_or_datadir

        # get timezone offset for all agencies
        agency_offsets = {}
        for agency in sched.GetAgencyList():
            td = timezone(agency.agency_timezone).utcoffset(None)
            agency_offsets[agency.agency_id] = td.days*3600*24 + td.seconds

        #just set the local timezone from a random entry in the agency list
        import os
        agencytz = sched.GetAgencyList()[0].agency_timezone
        os.environ['TZ'] = agencytz
        time.tzset()
        dst_offset = 3600 #KNOWN BUG: the daylight savings time offset is not always an hour

        # create calendar

        #get service bounds
        sid_start = min( [trip.GetStartTime() for trip in sched.GetTripList()] )
        sid_end   = max( [trip.GetEndTime() for trip in sched.GetTripList()] )

        rawcalendar = self._raw_calendar( sched )

        cal = Calendar()
        for day, service_ids in rawcalendar:
            local_daystart = self._date_to_secs(day)+time.timezone
            #if daylight savings is in effect
            if self._is_dst(day):
                local_daystart -= dst_offset
                daylight_savings = dst_offset
            else:
                daylight_savings = 0

            cal.add_day( local_daystart+sid_start, local_daystart+sid_end, service_ids, daylight_savings )

        #add all vertices
        for stop in sched.GetStopList():
            self.add_vertex(prefix+stop.stop_id)

        #add all tripstops
        for stop in sched.GetStopList():
            rawtriphopschedules = self._raw_triphopschedules_from_stop(stop)
            
            for rawtriphopschedule in rawtriphopschedules:
                hops = [(fromv.departure_secs, tov.arrival_secs, trip.trip_id.encode("ascii")) for trip,fromv,tov in rawtriphopschedule]
                    
                str_service_id = rawtriphopschedule[0][0].service_id #service_id in string form
                service_id = cal.service_id_directory[str_service_id]
                    
                ths = TripHopSchedule( hops, service_id, cal.head, -time.timezone, authority )
                e = self.add_edge( prefix+fromv.stop_id, prefix+tov.stop_id, ths )


