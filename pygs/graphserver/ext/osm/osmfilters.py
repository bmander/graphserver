from graphserver.core import Graph, Link, Street, State
from osmdb import OSMDB
import time

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
        DeleteOrphanNodesFilter().run(db,*args)

        
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
    def filter(self, db, *args):
        f = FindDisjunctGraphsFilter()
        try:
            f.teardown(db)
        except: pass
        
        f.run(db,*args)
        
        largest = next(db.execute("SELECT graph_num, count(*) as cnt FROM graph_nodes GROUP BY graph_num ORDER BY cnt desc"))[0]
        
        node_ids = {}
        
        for x in db.execute("SELECT node_id FROM graph_nodes where graph_num != ?", (largest,)):
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
        DeleteOrphanNodesFilter().run(db,*args)
                
        f.teardown(db)

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
        
        print "load vertices into memory"
        for row in osmdb.execute("SELECT id from nodes"):
            g.add_vertex(str(row[0]))

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
            c.execute("SELECT id from nodes where id not in (SELECT node_id from graph_nodes) LIMIT 1")
            try:
                vertex = next(c)[0]
            except:
                break
            spt = g.shortest_path_tree(vertex, None, State(1,0))
            for v in spt.vertices:
                c.execute("INSERT into graph_nodes VALUES (?, ?)", (iteration, v.label))
            spt.destroy()
            iteration += 1
            
            t1 = time.time()
            print "pass %s took: %f"%(iteration, t1-t0)
            t0 = t1
        c.close()
        
        osmdb.conn.commit()
        # audit
        for gnum, count in osmdb.execute("SELECT graph_num, count(*) FROM graph_nodes GROUP BY graph_num"):
            print "FOUND: %s=%s" % (gnum, count)
        
    def visualize(self, db, out_filename):
        
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
        mr = processing.MapRenderer("/usr/local/bin/prender/renderer")
        WIDTH = 2000
        mr.start(l,b,r,t,WIDTH) #left,bottom,right,top,width
        mr.background(255,255,255)
        mr.smooth()
        width = float(r-l)/WIDTH
    
        for w in db.ways():
            g = w.geom
            group = node_group[w.nds[0]]
            color = group_color[group]
            mr.strokeWeight( group_weight[group] * width )
            mr.stroke(*color)                            
            mr.line(g[0][0],g[0][1],g[-1][0],g[-1][1])
            
        mr.saveLocal(out_filename)
        mr.stop()
        print "Done"
        
            
        
def main():
    from sys import argv
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