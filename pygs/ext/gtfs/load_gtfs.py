import transitfeed
import time
from pytz import timezone
import sys
import datetime
from pygs.graphserver import Graph, Street, CalendarDay, TripHopSchedule, Calendar, State
import csv
import calendar
import os

if transitfeed.__version__ != "1.1.5":
    raise Exception("transitfeed.__version__ != 1.1.5")

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

    def _raw_calendar(self, calendarfile, exceptionsfile):
        rawdays = {} #hash of date to service_id lists
        
        # regular calendar
        reader = csv.reader(open(calendarfile,"r"))
        reader.next() #skip the header
        
        # for each service id
        for service_id, mon,tue,wed,thu,fri,sat,sun,service_start,service_end in reader:
            dows = dict( zip(range(0,7), [ x=="1" for x in [mon,tue,wed,thu,fri,sat,sun] ] ) )
            
            #get date range
            service_start = datetime.date(int(service_start[0:4]),int(service_start[4:6]),int(service_start[6:]))
            service_end   = datetime.date(int(service_end[0:4]),int(service_end[4:6]),int(service_end[6:]))
            
            #apply that service_id to every date in the range which matches a weekday where the service_id is valid
            for i in range( service_start.toordinal(), service_end.toordinal()+1 ):
                if i not in rawdays:
                    rawdays[i] = []
                
                if dows[ datetime.date.fromordinal(i).weekday() ]:
                    rawdays[i].append( service_id )
        
        # exceptions
        reader = csv.reader(open(exceptionsfile, "r"))
        reader.next() #skip the header
        
        #for each exception
        for service_id, exceptdate, exceptiontype in reader:
            exceptdate = datetime.date(int(exceptdate[0:4]),int(exceptdate[4:6]),int(exceptdate[6:]))
            
            if exceptiontype == "1":
                rawdays[exceptdate.toordinal()].append(service_id)
            elif exceptiontype == "2":
                rawdays[exceptdate.toordinal()].remove(service_id)
                
        #convert days to list and order
        rawdays = [ (datetime.date.fromordinal(x),y) for x,y in rawdays.items() ]
        rawdays.sort(lambda x,y: cmp(x[0],y[0]))
        
        #for rawday in rawdays:
        #    print rawday
        
        return rawdays
        
    def _date_to_secs(self, adate):
        return calendar.timegm( (adate.year,adate.month,adate.day,0,0,0,0,0,0) )
        
    def _is_dst(self, adate):
        return time.localtime( time.mktime((adate.year,adate.month,adate.day,0,0,0,0,0,-1)) )[-1]

    def load_gtfs(self, datadir, sched=None, prefix="gtfs", authority=0):
        
        if sched is None:
            sched = transitfeed.Loader(datadir).Load()

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

        rawcalendar = self._raw_calendar( os.path.join(datadir, "calendar.txt"), os.path.join(datadir, "calendar_dates.txt") )

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
                    
                str_service_id = rawtriphopschedule[0][0].service_id #servic_id in string form
                service_id = cal.service_id_directory[str_service_id]
                    
                ths = TripHopSchedule( hops, service_id, cal.head, -time.timezone, authority )
                e = self.add_edge( prefix+fromv.stop_id, prefix+tov.stop_id, ths )


