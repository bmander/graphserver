from graphserver.ext.osm.osmdb import OSMDB
from elevation.elevation import ElevationPile, GridFloat, BIL
from graphserver.ext.osm.profiledb import ProfileDB

OSMDB_NAME = "./data/osm/map2.osmdb"
ELEV_BASENAME = "./data/83892907/83892907"
PROFILEDB_NAME = "profile.db"

def populate_profile_db( osmdb_name, profiledb_name, dem_basenames ):


    ddb = OSMDB( osmdb_name )
    elevs = ElevationPile()
    for dem_basename in dem_basenames:
        elevs.add( dem_basename )
    pdb = ProfileDB( profiledb_name, overwrite=True )

    n = ddb.count_edges()
    print "Profiling %d way segments"%n
    
    for i, (id, parent_id, node1, node2, dist, geom, tags) in enumerate( ddb.edges() ):
        if i%1000==0: print "%d/%d"%(i,n)
        
        raw_profile = elevs.profile( geom )
        profile = []
        
        tunnel = tags.get('tunnel')
        bridge = tags.get('bridge')
        if tunnel == 'yes' or tunnel == 'true' or bridge == 'yes' or bridge == 'true':
            if len(raw_profile) > 0:
                ss, ee = raw_profile[0]
                if ee is not None: profile.append( (ss,ee) )
            if len(raw_profile) > 1:
                ss, ee = raw_profile[-1]
                if ee is not None: profile.append( (ss,ee) )
        else:
            for ss, ee in raw_profile:
                if ee is not None: profile.append( (ss,ee) )
                
        pdb.store( id, profile )
        
    pdb.conn.commit()

from sys import argv
if __name__ == '__main__':

    usage = "python profile.py osmdb_name profiledb_name dem_basename "
    if len(argv) < 4:
        print usage
        exit()

    osmdb_name = argv[1]
    profiledb_name = argv[2]
    dem_basenames = argv[3:]
    
    populate_profile_db(osmdb_name, profiledb_name, dem_basenames)
