import transitfeed
import time
from pytz import timezone
import pytz
import sys
import datetime
sys.path.append("../../..")
from graphserver.core import Graph, Street, ServicePeriod, TripHopSchedule, ServiceCalendar, State
from graphserver.util import TimeHelpers
import csv
import calendar
import os
from datetime import date, timedelta

if transitfeed.__version__ != "1.1.6":
    raise Exception("transitfeed.__version__ != 1.1.6")
    
def parse_date(date):
    return (int(date[0:4]), int(date[4:6]), int(date[6:8]))

def get_service_ids(sched, date):
    if type(date)==datetime.date or type(date)==datetime.datetime:
        date = "%0.4d%0.2d%0.2d"%(date.year,date.month,date.day)
        
    return [sp.service_id for sp in filter(lambda x:x.IsActiveOn(date), sched.GetServicePeriodList())]
        
def timezone_from_agency(sched, agency_id):
    #try getting agency by agency_id. If that fails, try getting by agency nama
    try:
        agency = sched.GetAgency(agency_id)
    except KeyError:
        agency = filter(lambda x:x.agency_name==agency_id, sched.GetAgencyList())[0]
        
    return pytz.timezone( agency.agency_timezone )
    
def day_bounds_from_sched(sched):
    sid_start = min( [trip.GetStartTime() for trip in sched.GetTripList()] )
    sid_end   = max( [trip.GetEndTime() for trip in sched.GetTripList()] )
        
    return (sid_start, sid_end)

def schedule_to_service_calendar(sched, agency_id):
    timezone = timezone_from_agency(sched, agency_id)
    
    day_start, day_end = day_bounds_from_sched(sched)
    
    startdate, enddate = [ datetime.datetime( *parse_date(x) ) for x in sched.GetDateRange() ]
     
    cal = ServiceCalendar()
     
    for currdate in iter_dates(startdate, enddate):
        local_dt = timezone.localize(currdate)
        
        service_ids = get_service_ids( sched, currdate )
    
        this_day_begins = timezone.normalize( local_dt + timedelta(seconds=day_start) )
        this_day_ends = timezone.normalize( local_dt + timedelta(seconds=day_end)  )
    
        cal.add_period( ServicePeriod( TimeHelpers.datetime_to_unix(this_day_begins), TimeHelpers.datetime_to_unix(this_day_ends), cal.int_sids(service_ids) ) )
        
    return cal
    
def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)

class GTFSLoadable:
    def _triphops_from_stop(self, stop, agency):
        ret = []
        
        for time, (trip,ix), is_timepoint in stop.GetStopTimeTrips():
            
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
        
    def _raw_triphopschedules_from_stop(self, stop, agency):
        triphops = self._triphops_from_stop(stop, agency)
        thss = self._group_triphops(triphops)
        
        return thss

    def load_gtfs(self, sched_or_datadir, is_dst=False, prefix="gtfs"):
        
        if type(sched_or_datadir)==str:
            sched = transitfeed.Loader(sched_or_datadir).Load()
        else:
            sched = sched_or_datadir

        #add all vertices
        for stop in sched.GetStopList():
            self.add_vertex(prefix+stop.stop_id)

        for agency, i in zip( sched.GetAgencyList(), range(len(sched.GetAgencyList())) ):
            self._load_agency(sched, agency, i, is_dst, prefix)
                    
    def _load_agency(self, sched, agency, agency_int, is_dst, prefix):
        cal = schedule_to_service_calendar(sched, agency.agency_id)

        timezone = timezone_from_agency( sched, agency.agency_id )
        dt = timezone._utcoffset
        offset = dt.days*24*3600 + dt.seconds
        if is_dst:
            offset += 3600

        for stop in sched.GetStopList():
            rawtriphopschedules = self._raw_triphopschedules_from_stop(stop, agency)
            
            for rawtriphopschedule in rawtriphopschedules:
                hops = [(fromv.departure_secs, tov.arrival_secs, trip.trip_id.encode("ascii")) for trip,fromv,tov in rawtriphopschedule]
                    
                str_service_id = rawtriphopschedule[0][0].service_id #service_id in string form
                service_id = cal.service_id_directory[str_service_id]
                    
                ths = TripHopSchedule( hops, service_id, cal, offset, agency_int )
                e = self.add_edge( prefix+fromv.stop_id, prefix+tov.stop_id, ths )


