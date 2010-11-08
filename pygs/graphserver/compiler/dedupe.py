# eliminate duplicate service periods from a GTFS database

from graphserver.ext.gtfs.gtfsdb import GTFSDatabase

import sys
from optparse import OptionParser

def main():
    usage = """usage: python dedupe.py <graphdb_filename>"""
    parser = OptionParser(usage=usage)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.print_help()
        exit(-1)
        
    graphdb_filename = args[0]    
    
    gtfsdb = GTFSDatabase( graphdb_filename )

    query = """
    SELECT count(*), monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date 
    FROM calendar
    GROUP BY monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date"""

    duped_periods = gtfsdb.execute( query )

    equivilants = []

    for count, m,t,w,th,f,s,su,start_date,end_date in duped_periods:
        # no need to check for dupes if there's only one
        if count==1:
            continue
        
        #print count, m, t, w, th, f, s, su, start_date, end_date
        
        # get service_ids for this dow/start_date/end_date combination
        service_ids = [x[0] for x in list(  gtfsdb.execute( "SELECT service_id FROM calendar where monday=? and tuesday=? and wednesday=? and thursday=? and friday=? and saturday=? and sunday=? and start_date=? and end_date=?", (m,t,w,th,f,s,su,start_date,end_date) ) ) ]
        
        # group by service periods with the same set of exceptions
        exception_set_grouper = {}
        for service_id in service_ids:
            exception_set = list(gtfsdb.execute( "SELECT date, exception_type FROM calendar_dates WHERE service_id=?", (service_id,) ) )
            exception_set.sort()
            exception_set = tuple(exception_set)
            
            exception_set_grouper[exception_set] = exception_set_grouper.get(exception_set,[])
            exception_set_grouper[exception_set].append( service_id )
        
        # extend list of equivilants
        for i, exception_set_group in enumerate( exception_set_grouper.values() ):
            equivilants.append( ("%d%d%d%d%d%d%d-%s-%s-%d"%(m,t,w,th,f,s,su,start_date,end_date,i), exception_set_group) )
        
    for new_name, old_names in equivilants:
        for old_name in old_names:
            print old_name, new_name
            
            c = gtfsdb.conn.cursor()
            
            c.execute( "UPDATE calendar SET service_id=? WHERE service_id=?", (new_name, old_name) )
            c.execute( "UPDATE calendar_dates SET service_id=? WHERE service_id=?", (new_name, old_name) )
            c.execute( "UPDATE trips SET service_id=? WHERE service_id=?", (new_name, old_name) )

            gtfsdb.conn.commit()
            
            c.close()
            
if __name__=='__main__':
    main()
    
