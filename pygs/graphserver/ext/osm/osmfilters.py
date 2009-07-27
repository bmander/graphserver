from graphserver.core import Graph, Link, Street, State
from osmdb import OSMDB
import time
from vincenty import vincenty as dist_earth
try:
  import json
except ImportError:
  import simplejson as json

class OSMDBFilter(object):
    def setup(self, db, *args):
        pass
    
    def filter(self, db, *args):
        pass
    
    def teardown(self, db):
        pass
    
    def run(self,db, *args):
        self.setup(db, *args)
        self.filter(db, *args)

    def rerun(self,db, *args):
        self.teardown(db)
        self.run(db)
        
    def visualize(self, db, *args):
        pass

class CalculateWayLengthFilter(OSMDBFilter):
    def setup(self, db, *args):
        c = db.cursor()
        try:
            c.execute("ALTER TABLE ways ADD column length FLOAT")
            db.conn.commit()
        except: pass
        c.close()

    def filter(self, db):
        way_length = {}
        print "Calculating length."
        for way in db.ways():
            g = way.geom
            l = 0
            for i in range(0, len(g)-1):
                l += dist_earth(g[i][1], g[i][0], g[i+1][1], g[i+1][0])
            way_length[way.id] = l

        print "Updating %s ways" % len(way_length)
        c = db.cursor()
        for w,l in way_length.items():
            c.execute("UPDATE ways set length = ? where id = ?", (l,w))
        db.conn.commit()
        c.close()
        print "Done"

class AddFromToColumnsFilter(OSMDBFilter):
    def setup(self, db, *args):
        c = db.cursor()
        try:
            c.execute("ALTER TABLE ways ADD column from_v TEXT")
            c.execute("ALTER TABLE ways ADD column to_v TEXT")
            db.conn.commit()
        except: pass
        c.close()

    def filter(self, db):
        add_list = []
        for way in db.ways():
            add_list.append((way.nds[0], way.nds[-1], way.id))

        print "Updating %s ways" % len(add_list)
        c = db.cursor()
        for a in add_list:
            c.execute("UPDATE ways set from_v = ?, to_v = ? where id = ?", a)
        db.conn.commit()
        c.close()
        print "Done"

class DeleteHighwayTypesFilter(OSMDBFilter):
    def run(self, db, *types):
        print "Types",types
        purge_list = []
        for way in db.ways():
            if 'highway' in way.tags and way.tags['highway'] in types:
                purge_list.append(way.id)
        
        c = db.cursor()
        for i in range(0,len(purge_list),100):
            query = "DELETE from ways WHERE id in ('%s')" % "','".join(purge_list[i:i+100])
            c.execute(query)
        db.conn.commit()
        c.close()
        print "Deleted all %s highway types (%s ways)" % (", ".join(types), len(purge_list))
        DeleteOrphanNodesFilter().run(db,None)
        
class DeleteOrphanNodesFilter(OSMDBFilter):
    def run(self, db, *args):
        node_ids = {}
        for nid in db.execute("SELECT id from nodes"):
            node_ids[nid[0]] = 0
        
        for way in db.ways():
            node_ids[way.nds[0]] += 1
            node_ids[way.nds[-1]] += 1
        
        purge_list = []
        for n,c in node_ids.items():
            if c == 0:
                purge_list.append(n)
        c = db.cursor()
        for i in range(0,len(purge_list),100):
            query = "DELETE from nodes WHERE id in ('%s')" % "','".join(purge_list[i:i+100])
            c.execute(query)
        db.conn.commit()
        c.close()
        print "Deleted %s nodes of %d" % (len(purge_list), len(node_ids))
        

class PurgeDisjunctGraphsFilter(OSMDBFilter):
    def filter(self, db, threshold=None):
        f = FindDisjunctGraphsFilter()
        try:
            f.teardown(db)
        except: pass
        
        f.run(db,*[])
        
        node_ids = {}

        if not threshold:
            largest = next(db.execute("SELECT graph_num, count(*) as cnt FROM graph_nodes GROUP BY graph_num ORDER BY cnt desc"))[0]
                    
            for x in db.execute("SELECT node_id FROM graph_nodes where graph_num != ?", (largest,)):
                node_ids[x[0]] = 1
        else: 
            for x in db.execute("""SELECT node_id FROM graph_nodes where graph_num in
                                (SELECT a.graph_num FROM 
                                  (SELECT graph_num, count(*) as cnt FROM graph_nodes GROUP BY graph_num HAVING cnt < %s) as a)""" % threshold):
                node_ids[x[0]] = 1

        c = db.cursor()

        purge_list = []
        for way in db.ways():
            if way.nds[0] in node_ids or way.nds[-1] in node_ids:
                purge_list.append(way.id)

        for i in range(0,len(purge_list),100):
            query = "DELETE from ways WHERE id in ('%s')" % "','".join(purge_list[i:i+100])
            c.execute(query)
        db.conn.commit()
        c.close()
        print "Deleted %s ways" % (len(purge_list))
        DeleteOrphanNodesFilter().run(db,*[])
                
        f.teardown(db)
        
class StripOtherTagsFilter(OSMDBFilter):
    def filter(self, db, feature_type, *keep_tags):
        keep_tags = dict([(t,1) for t in keep_tags])

        update_list = {}
        if feature_type == 'nodes':
            query = "SELECT id,tags FROM nodes"
        else:
            query = "SELECT id,tags FROM ways"
            
        c = db.cursor()
        c.execute(query)
        for id, tags in c:
            tags = json.loads(tags)
            for k in tags.keys():
                if k not in keep_tags:
                    del tags[k]
            
            update_list[id] = json.dumps(tags)
        
        for id, tags in update_list.items():
            c.execute("UPDATE ways set tags = ? WHERE id = ?",(id,tags))

        db.conn.commit()
        c.close()

class FindDisjunctGraphsFilter(OSMDBFilter):
    def setup(self, db, *args):
        c = db.cursor()
        c.execute("CREATE table graph_nodes (graph_num INTEGER, node_id TEXT)")
        c.execute("CREATE index graph_nodes_node_indx ON graph_nodes(node_id)")
        c.close()

    def teardown(self, db):
        c = db.cursor()
        c.execute("DROP table graph_nodes")
        c.close()
        
    def filter(self, osmdb, *args):
        g = Graph()
        t0 = time.time()
        
        vertices = {}
        print "load vertices into memory"
        for row in osmdb.execute("SELECT id from nodes"):
            g.add_vertex(str(row[0]))
            vertices[str(row[0])] = 0

        print "load ways into memory"
        for way in osmdb.ways():
            g.add_edge(way.nds[0], way.nds[-1], Link())
            g.add_edge(way.nds[-1], way.nds[0], Link())

        t1 = time.time()
        print "populating graph took: %f"%(t1-t0)
        t0 = t1
        
        iteration = 1
        c = osmdb.cursor()
        while True:
            #c.execute("SELECT id from nodes where id not in (SELECT node_id from graph_nodes) LIMIT 1")
            try:
                vertex, dummy = vertices.popitem()
            except:
                break
            spt = g.shortest_path_tree(vertex, None, State(1,0))
            for v in spt.vertices:
                vertices.pop(v.label, None)
                c.execute("INSERT into graph_nodes VALUES (?, ?)", (iteration, v.label))
            spt.destroy()
            
            t1 = time.time()
            print "pass %s took: %f"%(iteration, t1-t0)
            t0 = t1
            iteration += 1
        c.close()
        
        osmdb.conn.commit()
        g.destroy()
        # audit
        for gnum, count in osmdb.execute("SELECT graph_num, count(*) FROM graph_nodes GROUP BY graph_num"):
            print "FOUND: %s=%s" % (gnum, count)
        
    def visualize(self, db, out_filename, renderer="/usr/local/bin/prender/renderer"):
        
        from prender import processing
        c = db.conn.cursor()
        
        group_color = {}
        group_weight = {}
        group_count = {}
        colors = [(255,128,255), (255,0,255), (255,255,128), (0,255,0), (255,0,0)]
        cnum = 0
        for num, count in db.execute("SELECT graph_num, count(*) FROM graph_nodes GROUP BY graph_num"):
            group_count[num] = count
            group_color[num] = colors[cnum]
            if count < 50:
                 group_weight[num] = 2
            elif count < 100:
                 group_weight[num] = 1.5
            else:
                 group_weight[num] = 1
                 
            cnum = (cnum + 1) % len(colors)
        
        largest_group = max(group_count, key=lambda x: group_count[x])
        group_color[largest_group] = (0,0,0)
        group_weight[largest_group] = 0.5
        
        node_group = {}
        for gn, ni in db.execute("SELECT graph_num, node_id FROM graph_nodes"):
            node_group[ni] = gn
        
        # setup the drawing
        l,b,r,t = db.bounds()
        mr = processing.MapRenderer(renderer)
        WIDTH = 3000
        mr.start(l,b,r,t,WIDTH) #left,bottom,right,top,width
        mr.background(255,255,255)
        mr.smooth()
        width = float(r-l)/WIDTH
    
        for i, w in enumerate(db.ways()):
            if i%1000==0: print "way %d"%i
            
            g = w.geom
            group = node_group[w.nds[0]]
            color = group_color[group]
            mr.strokeWeight( group_weight[group] * width )
            mr.stroke(*color)                            
            mr.line(g[0][0],g[0][1],g[-1][0],g[-1][1])

        mr.strokeWeight(width*10)
        mr.stroke(255,0,0)
        for ct, lat, lon in db.execute("SELECT count(*) as cnt, lat, lon from nodes GROUP BY lat, lon HAVING cnt > 1"):
            if ct>1:
                mr.point( lon, lat )

        mr.saveLocal(out_filename)
        mr.stop()
        print "Done"
        
class StitchDisjunctGraphs(OSMDBFilter):
    
    def filter(self, osmdb, *args):
        alias = {}
        
        # for each location that appears more than once
        for nds, ct, lat, lon in osmdb.execute("SELECT group_concat(id), count(*) as cnt, lat, lon from nodes GROUP BY lat, lon HAVING cnt > 1"):
            
            # get all the nodes that appear at that location
            #ids = map(lambda x:x[0], osmdb.execute("SELECT id FROM nodes WHERE lat=? AND lon=?", (lat,lon)))
            #print nds
            nds = nds.split(",")
            first = nds.pop(0)
            alias[nds] = nds
            # alias the duplicate node to an identical node
            #for id in ids:
            # if id != ids[0]:
            # alias[id] = ids[0]
                    
        # delete all duplicate nodes
        dupes = alias.keys()
        print "%d dupe nodes"%len(dupes)
        print "Deleting dupe nodes"
        query = "DELETE FROM nodes WHERE id IN (%s)"%(",".join(dupes),)
        c = osmdb.cursor()
        c.execute(query)
        osmdb.conn.commit()
        c.close()
        
        print "Replacing references to dupe nodes"
        c = osmdb.cursor()
        # replace reference in nd lists
        for i, (id, nds_str) in enumerate( osmdb.execute("SELECT id, nds FROM ways") ):
            if i%1000==0: print "way %d"%i
            
            nds = json.loads(nds_str)
            if nds[0] in alias:
                nds[0] = alias[nds[0]]
                print "replace header"
            if nds[-1] in alias:
                nds[-1] = alias[nds[-1]]
                print "replace footer"
            
            
            c.execute( "UPDATE ways SET nds=? WHERE id=?", (json.dumps(nds), id) )
        osmdb.conn.commit()
        c.close()

def stitch_and_visualize(dbname,mapname):
    osmdb = OSMDB( dbname )
    ff = StitchDisjunctGraphs()
    ff.filter( osmdb )
    
    ff = FindDisjunctGraphsFilter()
    ff.run( osmdb )
    ff.visualize( osmdb, mapname )

def main():
    from sys import argv
    if len(argv) < 4:
        print "%s <Filter Name> <run|rerun|visualize> <osmdb_file> [<filter args> ...]" % argv[0]
        print "Filters:"
        for k,v in globals().items():
            if type(v) == type and issubclass(v,OSMDBFilter):
                print " -- %s" % k
        exit()
    
    filter_cls, mode, osmdb_file = argv[1:4]
    
    try:
        f = globals()[filter_cls]()
    except KeyError, e:
        raise Exception("Filter not found.")
    
    db = OSMDB(osmdb_file)
 
    if len(argv) > 4:
        extra = argv[4:]
    else:
        extra = []
    
    if mode == 'run':
        f.run(db, *extra)
    elif mode == 'rerun':
        f.rerun(db, *extra)
    elif mode == 'visualize':
        f.visualize(db, *extra)
    else:
        raise Exception("Unknown mode.")
    
if __name__ == '__main__':
    main()
 
