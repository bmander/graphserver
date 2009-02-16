from gtfsdb import GTFSDatabase
import sys

if __name__=='__main__':
  if len(sys.argv) < 3:
    print "Converts GTFS file to GTFS-DB, which is super handy\nusage: python process_gtfs.py gtfs_filename, gtfsdb_filename"
    exit()

  gtfsdb_filename = sys.argv[2]
  gtfs_filename = sys.argv[1]
 
  gtfsdb = GTFSDatabase( gtfsdb_filename, overwrite=True )
  gtfsdb.load_gtfs( gtfs_filename, reporter=sys.stdout )

