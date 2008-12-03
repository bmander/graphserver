import transitfeed
import time
from pytz import timezone
import pytz
import sys
import datetime
sys.path.append("../../..")
from graphserver.core import Graph, Street, ServicePeriod, TripHopSchedule, ServiceCalendar, State, Timezone, Wait, TripHop, Headway, TimezonePeriod
from graphserver.util import TimeHelpers
import csv
import calendar
import os
from datetime import date, timedelta

if [int(x) for x in transitfeed.__version__.split('.')] < [1,1,6]:
    raise Exception("transitfeed.__version__ < 1.1.6")

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

        service_ids = [x.encode("ascii") for x in get_service_ids( sched, currdate )]

        this_day_begins = timezone.normalize( local_dt + timedelta(seconds=day_start) )
        this_day_ends = timezone.normalize( local_dt + timedelta(seconds=day_end)  )

        cal.add_period( TimeHelpers.datetime_to_unix(this_day_begins), TimeHelpers.datetime_to_unix(this_day_ends), service_ids )

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
        print "adding stop vertices"
        for stop in sched.GetStopList():
            self.add_vertex(prefix+stop.stop_id)

        self.numagencies = len(sched.GetAgencyList())

        for agency, i in zip( sched.GetAgencyList(), range(len(sched.GetAgencyList())) ):
            self._load_agency(sched, agency, i, prefix)

    def _load_agency(self, sched, agency, agency_int, prefix):
        cal = schedule_to_service_calendar(sched, agency.agency_id)

        gs_tz = Timezone.generate(agency.agency_timezone)

        for stop in sched.GetStopList():
            print "loading stop %s for agency %s"%(stop.stop_id, agency.agency_id)
            rawtriphopschedules = self._raw_triphopschedules_from_stop(sched, stop, agency)

            for rawtriphopschedule in rawtriphopschedules:
                #hops = [(fromv.departure_secs, tov.arrival_secs, trip.trip_id.encode("ascii")) for trip,fromv,tov in rawtriphopschedule]
                hops =[]
                service_id = rawtriphopschedule[0][0].service_id.encode("ascii")
                for trip,fromv,tov in rawtriphopschedule:
                  trip_id = trip.trip_id.encode("ascii")
                  if len(trip.GetHeadwayPeriodTuples())!=0:
                    for start_time, end_time, headway_secs in trip.GetHeadwayPeriodTuples():
                      hw = Headway( start_time, end_time, headway_secs, (tov.arrival_secs - fromv.departure_secs), trip_id, cal, gs_tz, agency_int, service_id )
                      e = self.add_edge( prefix+fromv.stop_id, prefix+tov.stop_id, hw )
                  else:
                    hops.append( (fromv.departure_secs, tov.arrival_secs, trip_id) )

                if hops!=[]:
                  ths = TripHopSchedule( hops, service_id, cal, gs_tz, agency_int )
                  e = self.add_edge( prefix+fromv.stop_id, prefix+tov.stop_id, ths )

    def load_gtfs_dag(self, sched_or_datadir, stops_timezone_name, prefix="gtfs"):

        if type(sched_or_datadir)==str:
            sched = transitfeed.Loader(sched_or_datadir).Load()
        else:
            sched = sched_or_datadir

        stz = Timezone.generate( stops_timezone_name )

        tzs = dict( [(agency.agency_id, Timezone.generate(agency.agency_timezone)) for agency in sched.GetAgencyList()] )
        scs = dict( [(agency.agency_id, schedule_to_service_calendar(sched, agency.agency_id)) for agency in sched.GetAgencyList()] )
        agints = dict( zip([x.agency_id for x in sched.GetAgencyList()], range(len(sched.GetAgencyList())) ))

        stop_times = dict( [(x.stop_id, set()) for x in sched.GetStopList()] )

        for route in sched.GetRouteList():
            print "adding all triphops for route %s"%route.route_id

            for trip in route.trips:
                agency_id = route_for_trip(trip).agency_id
                stops = trip.GetTimeInterpolatedStops()

                for (fromst_time,fromst_st,fromst_timed), (tost_time,tost_st,tost_timed) in cons(stops):
                    fromst_name = "%s@%s"%(fromst_st.stop.stop_id,fromst_time)
                    tost_name = "%s@%s"%(tost_st.stop.stop_id,tost_time)

                    self.add_vertex(fromst_name)
                    self.add_vertex(tost_name)

                    sc = scs[agency_id]
                    th = TripHop(fromst_time, tost_time, trip.trip_id, sc, tzs[agency_id], agints[agency_id], trip.service_id.encode("ascii"))

                    self.add_edge(fromst_name, tost_name, th)

                    stop_times[fromst_st.stop.stop_id].add(fromst_time)
                    stop_times[tost_st.stop.stop_id].add(tost_time)

        for stop_id, times in stop_times.iteritems():
            print "laying down beanstock for %s"%stop_id
            times = list(times)
            times.sort()

            self.add_vertex(stop_id)

            for time in times:
                self.add_edge( stop_id, "%s@%s"%(stop_id,time), Wait(time, stz) )
                self.add_edge( "%s@%s"%(stop_id,time), stop_id, Wait(time, stz) )

            for fromtime, totime in cons(times):
                self.add_edge( "%s@%s"%(stop_id,fromtime), "%s@%s"%(stop_id,totime), Wait(totime, stz) )

