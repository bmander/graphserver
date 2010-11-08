from graphserver.core import ServiceCalendar
import pytz
from datetime import timedelta, datetime, time
from graphserver.util import TimeHelpers

def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)
    
def service_calendar_from_timezone(gtfsdb, timezone_name):

    MAX_CALENDAR_SIZE = 1024
    sc_count = list(gtfsdb.execute( "SELECT DISTINCT count(*) FROM (SELECT service_id FROM calendar_dates UNION SELECT service_id FROM calendar )" ))[0][0]
    if sc_count > MAX_CALENDAR_SIZE:
        raise Exception( "Service period count %d is greater than the maximum of %d"%(sc_count, MAX_CALENDAR_SIZE) )
    
    timezone = pytz.timezone( timezone_name )

    # grab date, day service bounds
    start_date, end_date = gtfsdb.date_range()

    # init empty calendar
    cal = ServiceCalendar()

    # for each day in service range, inclusive
    for currdate in iter_dates(start_date, end_date):
        
        # get and encode in utf-8 the service_ids of all service periods running thos date
        service_ids = [x.encode('utf8') for x in gtfsdb.service_periods( currdate )]
        
        # figure datetime.datetime bounds of this service day
        currdate_start = datetime.combine(currdate, time(0))
        currdate_local_start = timezone.localize(currdate_start)
        service_period_begins = timezone.normalize( currdate_local_start )
        service_period_ends = timezone.normalize( currdate_local_start + timedelta(hours=24)  )

        # enter as entry in service calendar
        cal.add_period( TimeHelpers.datetime_to_unix(service_period_begins), TimeHelpers.datetime_to_unix(service_period_ends), service_ids )

    return cal

