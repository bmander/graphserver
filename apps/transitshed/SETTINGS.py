GRAPHDB_FILENAME = None
OSMDB_FILENAME = None
CENTER = None 

if GRAPHDB_FILENAME is None or \
   OSMDB_FILENAME is None or \
   CENTER is None:
   raise Exception( "You need to set the settings." )
