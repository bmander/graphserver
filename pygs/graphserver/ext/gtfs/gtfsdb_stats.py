from gtfsdb import GTFSDatabase
import sys

if __name__=='__main__':
  if len(sys.argv) < 2:
    print "usage: python gtfsdb_stats.py gtfsdb_filename"
    exit() 
 
  db = GTFSDatabase( sys.argv[1] )
  print "extent: %s"%(db.extent(),)
  print "stop count: %d"%db.count_stops()
   
  print "date range: %s"%(db.date_range(),)