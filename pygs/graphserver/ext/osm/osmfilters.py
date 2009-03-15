from graphserver.core import Graph, Link, Street, State
from osmdb import OSMDB
import time

class OSMDBFilter(object):
    def setup(self, db):
        pass
    
    def filter(self, db):
        pass
    
    def teardown(self, db):
        pass
    
    def run(self,db):
        self.setup(db)
        self.filter(db)

    def rerun(self,db):
        self.teardown(db)
        self.run(db)
        
    def visualize(self, db):
        pass
    
class FindDisjunctGraphsFilter(OSMDBFilter):
    def setup(self, db):
        c = db.cursor()
        c.execute("CREATE table graph_nodes (graph_num INTEGER, node_id TEXT)")
        c.execute("CREATE index graph_nodes_node_indx ON graph_nodes(node_id)")
        c.close()

    def teardown(self, db):
        c = db.cursor()
        c.execute("DROP table graph_nodes")
        c.close()
        
    def filter(self, osmdb):
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
        
    def visualize(self, db, extra_args):
        assert len(extra_args) == 1
        filename = extra_args[0]
        
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
            
        mr.saveLocal(filename)
        mr.stop()
        print "Done"
        
            
        
def main():
    from sys import argv
    mode, osmdb_file = argv[1:3]
    db = OSMDB(osmdb_file)
    
    f = FindDisjunctGraphsFilter()
    if mode == 'run':
        f.run(db)
    elif mode == 'rerun':
        f.rerun(db)
    elif mode == 'visualize':
        if len(argv) > 3:
            extra = argv[3:]
        else:
            extra = []
        f.visualize(db, extra)
    else:
        raise Exception("Unknown mode.")
    
if __name__ == '__main__':
    main()