import transitfeed
import time
from pytz import timezone
import pytz
import sys
import datetime
sys.path.append("../../..")
from graphserver.core import Graph, Street, ServicePeriod, TripHopSchedule, ServiceCalendar, State, Timezone, Wait, TripHop, TimezonePeriod
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
    #try getting agency by agency_id. If that fails, try getting by agency name
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
    
def group(ary, groupfunc=lambda x:x):
    clumper = {}
    for item in ary:
        grouplabel = groupfunc(item)
        if grouplabel not in clumper:
            clumper[grouplabel] = []
        clumper[grouplabel].append( item )
        
    return clumper.values()
    
def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)
        
def stoptimes_from_stoptimetrips(stts):
    """return transitfeed StopTime objects from the tuple list returned from stop.GetStopTimeTrips()"""
    
    for time,(trip,trindex),is_tp in stts:
        yield trip.GetStopTimes()[trindex]
        
def eventtimes_from_stoptimetrips(stts):
    """return all events (arrivals and departures) that occur at this stop, given this stop's stop.GetStopTimeTrips() list of tuples"""
    
    for stoptime in stoptimes_from_stoptimetrips(stts):
        yield stoptime.arrival_secs
        yield stoptime.departure_secs

def distinct(ary):
    """eliminate duplicate items from list"""
    return list(set(ary))

def unique_eventtimes_from_stoptimetrips(stts):
    """return a sorted list of all departure and arrival times occurring at this stop, given the stops's stop.GetStopTimeTrips() list of tuples"""
    eventtimes = distinct(eventtimes_from_stoptimetrips(stts))
    eventtimes.sort()
    return eventtimes
    
def cons(ary):
    """return all pairs of consecutive elements"""
    for x,y in zip(ary[:-1],ary[1:]):
        yield (x,y)
        
def route_for_trip(trip):
    return trip._schedule.routes[ trip.route_id ]

class GTFSLoadable:
    def _triphops_from_stop(self, sched, stop, agency):
        ret = []
        
        for time, (trip,ix), is_timepoint in stop.GetStopTimeTrips():
            route = sched.routes[trip.route_id]
            
            stoptimes = trip.GetStopTimes()
            if ix != len(stoptimes)-1 and route.agency_id == agency.agency_id:
                ret.append( (trip, stoptimes[ix], stoptimes[ix+1], trip.route_id ) )
            
        return ret
        
    def _group_triphops(self, raw_triphops):
        """Takes a bunch of tuples of (trip,stoptime,stoptime). Returns them grouped by trip,fromv,tov,routeid"""
        
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
        
    def _raw_triphopschedules_from_stop(self, sched, stop, agency):
        triphops = self._triphops_from_stop(sched, stop, agency)
        thss = self._group_triphops(triphops)
        
        return thss

    def load_gtfs(self, sched_or_datadir, prefix="gtfs"):
        
        if type(sched_or_datadir)==str:
            sched = transitfeed.Loader(sched_or_datadir).Load()
        else:
            sched = sched_or_datadir

        #add all vertices
        for stop in sched.GetStopList():
            self.add_vertex(prefix+stop.stop_id)
            
        self.numagencies = len(sched.GetAgencyList())

        for agency, i in zip( sched.GetAgencyList(), range(len(sched.GetAgencyList())) ):
            self._load_agency(sched, agency, i, prefix)
                    
    def _load_agency(self, sched, agency, agency_int, prefix):
        cal = schedule_to_service_calendar(sched, agency.agency_id)

        gs_tz = Timezone.generate(agency.agency_timezone)

        for stop in sched.GetStopList():
            rawtriphopschedules = self._raw_triphopschedules_from_stop(sched, stop, agency)
            
            for rawtriphopschedule in rawtriphopschedules:
                hops = [(fromv.departure_secs, tov.arrival_secs, trip.trip_id.encode("ascii")) for trip,fromv,tov in rawtriphopschedule]
                    
                str_service_id = rawtriphopschedule[0][0].service_id #service_id in string form
                service_id = cal.service_id_directory[str_service_id]
                    
                ths = TripHopSchedule( hops, service_id, cal, gs_tz, agency_int )
                e = self.add_edge( prefix+fromv.stop_id, prefix+tov.stop_id, ths )
                
    def load_gtfs_dag(self, sched_or_datadir, stops_timezone_name, prefix="gtfs"):
        
        if type(sched_or_datadir)==str:
            sched = transitfeed.Loader(sched_or_datadir).Load()
        else:
            sched = sched_or_datadir

        gs_tz = Timezone.generate(stops_timezone_name)

        #add all vertices
        for stop in sched.GetStopList():
            print "laying down beanstock for stop %s"%stop.stop_id
            self.add_vertex(prefix+stop.stop_id)
            
            stts = stop.GetStopTimeTrips()
            eventtimes = list(unique_eventtimes_from_stoptimetrips(stts))
            for eventtime in eventtimes:
                self.add_vertex( "%s@%s"%(stop.stop_id,eventtime) )
                self.add_edge( prefix+stop.stop_id, "%s@%s"%(stop.stop_id,eventtime), Wait(eventtime, gs_tz) )
                self.add_edge( "%s@%s"%(stop.stop_id,eventtime), prefix+stop.stop_id, Wait(eventtime, gs_tz) )
                
            for startwait,endwait in cons(eventtimes):
                self.add_edge( "%s@%s"%(stop.stop_id,startwait), "%s@%s"%(stop.stop_id,endwait), Wait(endwait, gs_tz) )
            
        self.numagencies = len(sched.GetAgencyList())

        for agency, i in zip( sched.GetAgencyList(), range(len(sched.GetAgencyList())) ):
            self._load_agency_dag(sched, agency, i, prefix)
            
    def _load_agency_dag(self, sched, agency, agency_int, prefix):
        cal = schedule_to_service_calendar(sched, agency.agency_id)
        
        gs_tz = Timezone.generate(agency.agency_timezone)

        for stop in sched.GetStopList():
            print "adding triphops leaving stop %s for agency %s"%(stop.stop_id, agency.agency_id)
            
            stts = stop.GetStopTimeTrips()
            
            # for each trip touching this stop
            for time,(trip,trindex),is_st in stts:
                
                # the trip's route must be of the current agency
                if route_for_trip(trip).agency_id != agency.agency_id:
                    continue
                
                stoptimes = trip.GetStopTimes()
                
                # there is no outbound triphop if this is the last stoptime on the route
                if trindex == len(stoptimes)-1:
                    continue
                    
                fromst = stoptimes[trindex]
                tost = stoptimes[trindex+1]
                
                th = TripHop(fromst.departure_secs, tost.arrival_secs, trip.trip_id.encode("ascii"), cal, gs_tz, agency_int, cal.int_sid(trip.service_id))
                self.add_edge( "%s@%s"%(fromst.stop.stop_id, fromst.departure_secs), "%s@%s"%(tost.stop.stop_id, tost.arrival_secs), th )

