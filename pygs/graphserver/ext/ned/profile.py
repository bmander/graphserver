from graphserver.ext.osm.osmdb import OSMDB
from elevation.elevation import ElevationPile, GridFloat, BIL
from graphserver.ext.osm.profiledb import ProfileDB

OSMDB_NAME = "./data/osm/map2.osmdb"
ELEV_BASENAME = "./data/83892907/83892907"
PROFILEDB_NAME = "profile.db"

def compress(ary, ratio):
    yield ary[0]
    for i in range(1, len(ary)-1, ratio):
        yield ary[i]
    yield ary[-1]

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

class Profile(object):
    def __init__(self):
        self.segs = []
        
    def add(self, seg):
        self.segs.append( seg )
        
    def concat(self, npoints=None):
        ret = []
        s = 0
        
        for seg in self.segs:
            if len(seg)<2:
                continue
            
            s0, e0 = seg[0]
            ret.append( (s, e0) )
            for (s0, e0), (s1, e1) in cons(seg):
                s += abs(s1-s0)
                ret.append( (s, e1) )
                
        if npoints is not None:
            compression = int(len(ret)/float(npoints))
            if compression <= 1:
                return ret
            
            return list(compress(ret,compression))
                
        return ret

def populate_profile_db( osmdb_name, profiledb_name, dem_basenames, resolution ):

    ddb = OSMDB( osmdb_name )
    elevs = ElevationPile()
    for dem_basename in dem_basenames:
        elevs.add( dem_basename )
    pdb = ProfileDB( profiledb_name, overwrite=True )

    n = ddb.count_edges()
    print "Profiling %d way segments"%n
    
    for i, (id, parent_id, node1, node2, dist, geom, tags) in enumerate( ddb.edges() ):
        if i%1000==0: print "%d/%d"%(i,n)
        
        raw_profile = elevs.profile( geom, resolution )
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
def main():
    usage = "python profile.py osmdb_name profiledb_name resolution dem_basename "
    if len(argv) < 5:
        print usage
        exit()

    osmdb_name = argv[1]
    profiledb_name = argv[2]
    resolution = int(argv[3])
    dem_basenames = argv[4:]

    print "osmdb name:", osmdb_name
    print "profiledb name:", profiledb_name
    print "resolution:", resolution
    print "dem_basenames:", dem_basenames
    
    populate_profile_db(osmdb_name, profiledb_name, dem_basenames, resolution)

if __name__ == '__main__':
    main()
