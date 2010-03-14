import unittest
from graphserver.core import *
import time


class TestGraph(unittest.TestCase):
    
    def test_basic(self):
        g = Graph()
        assert g
        
        g.destroy()
        
    def test_empty_graph(self):
        g = Graph()
        assert g.vertices == []
        
        g.destroy()
        
    def test_add_vertex(self):
        g = Graph()
        v = g.add_vertex("home")
        assert v.label == "home"
        
        g.destroy()
        
    def test_remove_vertex(self):
        g = Graph()
        g.add_vertex( "A" )
        g.get_vertex( "A" ).label == "A"
        g.remove_vertex( "A", True, True )
        assert g.get_vertex( "A" ) == None
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        pl = Street( "AB", 1 )
        g.add_edge( "A", "B", pl )
        g.remove_vertex( "A", True, False )
        assert pl.name == "AB"
        assert g.get_vertex( "A" ) == None
        assert g.get_vertex( "B" ).label == "B"
        
    def test_add_vertices(self):
        g = Graph()
        verts = range(0,100000)
        t0 = time.time()
        g.add_vertices(verts)
        print "add vertices elapsed ", (time.time() - t0)
        vlist = g.vertices
        assert len(vlist) == len(verts)
        vlist.sort(lambda x, y: int(x.label) - int(y.label))
        assert vlist[0].label == "0"
        assert vlist[-1].label == str(verts[-1])
        g.destroy()
        
        
    def test_double_add_vertex(self):
        g = Graph()
        v = g.add_vertex("double")
        assert v.label == "double"
        assert g.size == 1
        v = g.add_vertex("double")
        assert g.size == 1
        assert v.label == "double"
        
        g.destroy()
        
    def test_get_vertex(self):
        g = Graph()
        
        g.add_vertex("home")
        v = g.get_vertex("home")
        assert v.label == "home"
        v = g.get_vertex("bogus")
        assert v == None
        
        g.destroy()
        
    def test_add_edge(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        assert e
        assert e.from_v.label == "home"
        assert e.to_v.label == "work"
        assert str(e)=="<Edge><Street name='helloworld' length='1.000000' rise='0.000000' fall='0.000000' way='0'/></Edge>"
        
        g.destroy()
    
    def test_add_edge_effects_vertices(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert fromv.degree_out==1
        assert tov.degree_in==1
        
        g.destroy()
    
    def test_vertices(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        assert g.vertices
        assert len(g.vertices)==2
        assert g.vertices[0].label == 'home'
        
        g.destroy()
    
    def test_shortest_path_tree(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("home").payload.weight==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        print spt.get_vertex("work").payload.weight
        assert spt.get_vertex("work").payload.weight==1
        
        spt.destroy()
        g.destroy()
        
    def test_aborts_at_maxtime(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        
        g.add_edge( "A", "B", Crossing() )
        g.add_edge( "B", "C", Crossing() )
        g.add_edge( "C", "D", Crossing() )
        
        spt = g.shortest_path_tree( "A", "D", State(1,0), WalkOptions() )
        assert [v.label for v in spt.vertices] == ['A', 'B', 'C', 'D']
        
        spt = g.shortest_path_tree( "A", "D", State(1,0), WalkOptions(), maxtime=100 )
        assert [v.label for v in spt.vertices] == ['A', 'B', 'C']
        
    def test_bogus_origin(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree("bogus", "work", State(g.numagencies,0), WalkOptions())
        
        assert spt == None
        
        spt = g.shortest_path_tree_retro("home", "bogus", State(g.numagencies,0), WalkOptions())
        
        assert spt == None
        
        
    def test_spt_retro(self):
        
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,100), WalkOptions())
        
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out == 0
        print spt.get_vertex("home").degree_in
        assert spt.get_vertex("home").degree_in == 1
        assert spt.get_vertex("home").payload.weight == 1
        assert spt.get_vertex("work").degree_in == 0
        assert spt.get_vertex("work").degree_out == 1
        assert spt.get_vertex("work").payload.weight == 0
        
        spt.destroy()
        g.destroy()
        
    def test_spt_retro_chain(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        
        g.add_edge( "A", "B", Street( "AB", 1 ) )
        g.add_edge( "B", "C", Street( "BC", 1 ) )
        g.add_edge( "C", "D", Street( "CD", 1 ) )
        
        spt = g.shortest_path_tree_retro( "A", "D", State(g.numagencies,1000), WalkOptions() )
        
        assert spt.get_vertex( "A" ).payload.time
        
        spt.destroy()
        
        
    def test_shortst_path_tree_link(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("work").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
        spt.destroy()
        g.destroy()
        
    def test_spt_link_retro(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("work").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
        
        spt.destroy()
        g.destroy()
        
    def test_walk_longstreet(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 24000 )
        e = g.add_edge("home", "work", s)
        
        wo = WalkOptions()
        sprime = e.walk(State(g.numagencies,0), wo)
        
        assert sprime.time==28235
        assert sprime.weight==39557235
        assert sprime.dist_walked==24000.0
        assert sprime.num_transfers==0
        
        wo.destroy()
        print str(sprime)

        g.destroy()
        
    def xtestx_shortest_path_tree_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0))
        
        assert spt.get_vertex("home").degree_out == 1
        
        spt.destroy()
        g.destroy()
            
    def test_shortest_path_tree_retro(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
        
        spt.destroy()
        g.destroy()
    
    def test_shortest_path(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies), WalkOptions())
        sp = spt.path("work")
        
        assert sp
        
    def xtestx_shortest_path_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sp = g.shortest_path("home", "work", State(g.numagencies))
        
        assert sp
        
    def test_add_link(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert e.payload
        assert e.payload.__class__ == Street
        
        x = g.add_edge("work", "home", Link())
        assert x.payload
        assert x.payload.name == "LINK"
        
        g.destroy()
    
    def test_hello_world(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        
        g.add_edge( "Seattle", "Portland", Street("I-5 south", 5000) )
        g.add_edge( "Portland", "Seattle", Street("I-5 north", 5500) )
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(g.numagencies,0), WalkOptions() )
        
        assert spt.get_vertex("Seattle").outgoing[0].payload.name == "I-5 south"
        
        g.add_vertex( "Portland-busstop" )
        g.add_vertex( "Seattle-busstop" )
        
        g.add_edge( "Seattle", "Seattle-busstop", Link() )
        g.add_edge( "Seattle-busstop", "Seattle", Link() )
        g.add_edge( "Portland", "Portland-busstop", Link() )
        g.add_edge( "Portland-busstop", "Portland", Link() )
        
        spt = g.shortest_path_tree( "Seattle", "Seattle-busstop", State(g.numagencies,0), WalkOptions() )
        assert spt.get_vertex("Seattle-busstop").incoming[0].payload.__class__ == Link
        spt.destroy()
        
        spt = g.shortest_path_tree( "Seattle-busstop", "Portland", State(g.numagencies,0), WalkOptions() )
        assert spt.get_vertex("Portland").incoming[0].payload.__class__ == Street
        spt.destroy()
        
        sc = ServiceCalendar()
        sc.add_period( 0, 86400, ["WKDY","SAT"] )
        tz = Timezone()
        tz.add_period( TimezonePeriod( 0, 86400, 0 ) )
        
        g.add_vertex( "Portland-busstop-onbus" )
        g.add_vertex( "Seattle-busstop-onbus" )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        tb.add_boarding( "A", 10, 0 )
        tb.add_boarding( "B", 15, 0 )
        tb.add_boarding( "C", 400, 0 )
        
        cr = Crossing(20)
        
        al = Alight("WKDY", sc, tz, 0)
        al.add_alighting( "A", 10+20, 0 )
        al.add_alighting( "B", 15+20, 0 )
        al.add_alighting( "C", 400+20, 0 )
        
        g.add_edge( "Seattle-busstop", "Seattle-busstop-onbus", tb )
        g.add_edge( "Seattle-busstop-onbus", "Portland-busstop-onbus", cr )
        g.add_edge( "Portland-busstop-onbus", "Portland-busstop", al )
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(g.numagencies,0), WalkOptions() )
        
        assert spt.get_vertex( "Portland" ).incoming[0].from_v.incoming[0].from_v.incoming[0].from_v.incoming[0].from_v.incoming[0].from_v.label == "Seattle"
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(g.numagencies,0), WalkOptions() )
        vertices, edges = spt.path( "Portland" )
        
        assert [v.label for v in vertices] == ['Seattle', 'Seattle-busstop', "Seattle-busstop-onbus", "Portland-busstop-onbus", 'Portland-busstop', 'Portland']
        assert [e.payload.__class__ for e in edges] == [Link, TripBoard, Crossing, Alight, Link]
        
        spt.destroy()
        g.destroy()
        
    def test_get_route(self):
        "Check it finds the route we expect"
        
        g = Graph()
        
        reader = csv.reader(open(find_resource("map.csv")))
        
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
            
        v85thStreet = "53184534"
        vBeaconAve = "53072051"
        idealVertices = ['53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '69516594', '53132048', '69516588', '53095152', '53132049', '53239899', '53147269', '53138815', '69516553', '53138764', '53194375', '53185509', '53194376', '53144840', '53178633', '53178635', '53194364', '53125622', '53045160', '53194365', '53194366', '53194367', '53194368', '53185796', '53194369', '53086028', '90251330', '90251121', '30789993', '30789998', '31394282', '31393878', '29977892', '124205994', '31428350', '29545469', '94008501', '29545421', '29545417', '29545423', '29484769', '29484785', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231231', '30230962', '60878121', '53224639', '53210038', '53081902', '53052413', '53210039', '53224626', '53168444', '53224629', '53224632', '53208783', '53083017', '53083040', '53208784', '53187334', '53187337', '53089335', '53066732', '53208785', '53178012', '53208786', '53152490', '53183929', '53146692', '53146065', '53083086', '53083102', '53113957', '53113944', '53190685', '53203056', '53167007', '53129046', '53098715', '53208787', '53208788', '53180738', '53072051']
        idealEdges = ['9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '6438432-16', '6438432-17', '6386686-0', '6386686-1', '6386686-2', '6497278-2', '6497278-3', '6497278-4', '6497278-5', '6497278-6', '6514850-51', '6439614-0', '6439614-1', '6439614-2', '6439614-3', '15255537-1', '6439607-0', '6439607-1', '6439607-2', '6439607-3', '6439607-4', '6439607-5', '6439607-6', '6439607-7', '6439607-8', '6439607-9', '6439607-10', '10497741-3', '10497743-3', '4709507-4', '4709507-5', '4709507-6', '4709507-7', '4709507-8', '4869151-0', '4869146-0', '4869146-1', '4869146-2', '4869146-3', '4869146-4', '4644156-0', '4722460-0', '4722460-1', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '4743936-0', '4743934-0', '4743897-3', '4743897-4', '8116116-0', '6457969-20', '6457969-21', '6457969-22', '6476943-0', '6476943-1', '6476943-2', '6476943-3', '6476943-4', '6456455-20', '6456455-21', '6456455-22', '6456455-23', '6456455-24', '6456455-25', '6456455-26', '6456455-27', '6456455-28', '6456455-29', '6456455-30', '6456455-31', '6456455-32', '6456455-33', '6456455-34', '6456455-35', '6456455-36', '6456455-37', '6456455-38', '6456455-39', '6456455-40', '6456455-41', '6456455-42', '6456455-43', '6456455-44', '6456455-45', '6456455-46']

        t0 = time.time()
        spt = g.shortest_path_tree( v85thStreet, vBeaconAve, State(g.numagencies,0), WalkOptions() )
        t1 = time.time()
        print "time:", (t1-t0)*1000
        
        vertices, edges = spt.path( vBeaconAve )
        
        assert spt.get_vertex("53072051").payload.time == 31439
        assert spt.get_vertex("53072051").payload.weight == 17311963
        assert spt.get_vertex("53072051").payload.dist_walked == 26774.100248
        
        assert( False not in [l==r for l,r in zip( [v.label for v in vertices], idealVertices )] )
        assert( False not in [l==r for l,r in zip( [e.payload.name for e in edges], idealEdges )] )
            
        vBallardAve = "53115442"
        vLakeCityWay = "124175598"
        idealVertices = ['53115442', '53115445', '53115446', '53227448', '53158020', '53105937', '53148458', '53077817', '53077819', '53077821', '53077823', '53077825', '60413953', '53097655', '60413955', '53196479', '53248412', '53245437', '53153886', '53181632', '53246786', '53078069', '53247761', '53129527', '53203543', '53248413', '53182343', '53156127', '53227471', '53240242', '53109739', '53248420', '53234775', '53170822', '53115167', '53209384', '53134650', '53142180', '53087702', '53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '53183554', '53213063', '53197105', '53213061', '53090659', '53213059', '53157290', '53062869', '53213057', '53213055', '53213054', '53184527', '67507140', '67507145', '67507034', '67507151', '67507040', '67507158', '67507048', '67507166', '67507051', '67507176', '67507057', '67507126', '53233319', '53147253', '53233320', '53233321', '60002786', '60002787', '88468933', '53125662', '53195800', '88486410', '53228492', '88486425', '53215121', '88486457', '53199820', '53185765', '53233322', '53227223', '88486676', '53086030', '53086045', '53204778', '88486720', '53204762', '88486429', '53139133', '53139142', '88486453', '53072465', '30790081', '30790104', '53072467', '124181376', '30759113', '53072469', '53072472', '53072473', '53072475', '53072476', '53072477', '53072478', '124175598']
        idealEdges = ['6372784-0', '6372784-1', '6480699-3', '6517019-4', '6517019-5', '6517019-6', '6517019-7', '6346366-0', '6346366-1', '6346366-2', '6346366-3', '10425981-2', '8072147-2', '8072147-3', '6441828-10', '22758990-0', '6511156-0', '6511156-1', '6511156-2', '6511156-3', '6511156-4', '6511156-5', '6511156-6', '6511156-7', '6511156-8', '6511156-9', '6511156-10', '6511156-11', '6511156-12', '6511156-13', '6511156-14', '9112003-0', '9112003-1', '9112003-2', '9112003-3', '9112003-4', '9112003-5', '9112003-6', '9112003-7', '9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '10425996-0', '10425996-1', '10425996-2', '10425996-3', '10425996-4', '10425996-5', '10425996-6', '10425996-7', '10425996-8', '10425996-9', '10425996-10', '10425996-11', '10425996-12', '9116336-2', '9116336-3', '9116346-1', '9116346-2', '9116346-3', '9116346-4', '9116346-5', '9116346-6', '9116346-7', '9116346-8', '9116346-9', '6488959-1', '6488959-2', '6488959-3', '6488959-4', '6488959-5', '6488959-6', '6488959-7', '6488959-8', '6488959-9', '6488959-10', '6488959-11', '6488959-12', '6488959-13', '6488959-14', '6488959-15', '6488959-16', '6488959-17', '6488959-18', '6488959-19', '6488959-20', '6488959-21', '6488959-22', '6488959-23', '6488959-24', '6488959-25', '6488959-26', '6488959-27', '6488959-28', '6488959-29', '6344932-0', '6344932-1', '6344932-2', '13514591-0', '13514602-0', '13514602-1', '13514602-2', '8591344-0', '8591344-1', '8591344-2', '8591344-3', '8591344-4', '8591344-5']
        
        t0 = time.time()
        spt = g.shortest_path_tree( vBallardAve, vLakeCityWay, State(g.numagencies,0), WalkOptions() )
        t1 = time.time()
        print "time: ", (t1-t0)*1000
        vertices, edges = spt.path( vLakeCityWay )
        
        assert spt.get_vertex("124175598").payload.time == 13684
        assert spt.get_vertex("124175598").payload.weight == 190321
        
        assert( False not in [l==r for l,r in zip( [v.label for v in vertices], idealVertices )] )
        assert( False not in [l==r for l,r in zip( [e.payload.name for e in edges], idealEdges )] )
            
        #one last time
        vSandPointWay = "32096172"
        vAirportWay = "60147448"
        idealVertices = ['32096172', '60411560', '32096173', '32096176', '53110403', '32096177', '32096180', '53208261', '32096181', '60411559', '32096184', '53164136', '32096185', '32096190', '32096191', '32096194', '53123806', '32096196', '32096204', '53199337', '32096205', '32096208', '60411513', '32096209', '53040444', '32096212', '60411512', '53208255', '32096216', '53079385', '53079384', '32096219', '31192107', '31430499', '59948312', '31430457', '31430658', '29973173', '31430639', '29977895', '30012801', '31430516', '30012733', '29464742', '32271244', '31430321', '29464754', '31430318', '29973106', '31429815', '29464758', '31429758', '32103448', '60701659', '29464594', '29463661', '59677238', '59677231', '29463657', '29463479', '29449421', '29449412', '29545007', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231566', '30231379', '30230524', '30887745', '30887637', '30887631', '30887106', '60147424', '53131178', '53128410', '53131179', '53027159', '60147448']
        idealEdges = ['4910430-0', '4910430-1', '4910417-0', '4910416-0', '4910416-1', '4910414-0', '4910413-0', '4910413-1', '4910412-0', '4910412-1', '4910410-0', '4910410-1', '4910408-0', '4910405-0', '4910405-1', '4910405-2', '4910405-3', '4910402-0', '4910399-0', '4910399-1', '4910397-0', '4910394-0', '4910394-1', '4910392-0', '4910392-1', '4910385-0', '4910385-1', '4910385-2', '4910385-3', '4910385-4', '4910385-5', '4910384-0', '4910384-1', '4869358-0', '4869358-1', '4869358-2', '4869358-3', '4869357-0', '4869357-1', '4869357-2', '4869357-3', '4869357-4', '4869357-5', '4636137-0', '4636137-1', '4636137-2', '4636137-3', '4636137-4', '4636137-5', '4636137-6', '4708973-0', '4708973-1', '4708973-2', '4708973-3', '4636201-0', '4708972-0', '4708972-1', '4708972-2', '4636105-0', '4636093-0', '4729956-0', '4644053-0', '4644064-0', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '15257848-2', '15257848-3', '15257848-4', '4810339-0', '4810342-0', '4810342-1', '4810337-0', '4810290-0', '8044406-0', '15240328-7', '15240328-8', '15240328-9', '15240328-10']
        
        
        spt = g.shortest_path_tree( vSandPointWay, vAirportWay, State(g.numagencies,0), WalkOptions() )
        vertices, edges = spt.path( vAirportWay )
        
        assert spt.get_vertex("60147448").payload.time == 21082
        print spt.get_vertex("60147448").payload.weight
        assert spt.get_vertex("60147448").payload.weight == 4079909
        
        assert( False not in [l==r for l,r in zip( [v.label for v in vertices], idealVertices )] )
        assert( False not in [l==r for l,r in zip( [e.payload.name for e in edges], idealEdges )] )
            
    def test_get_route_retro(self):
        "Check it finds the route we expect, in reverse"
        
        g = Graph()
        
        reader = csv.reader(open(find_resource("map.csv")))
        
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
            
        v85thStreet = "53184534"
        vBeaconAve = "53072051"
        idealVertices = ['53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '69516594', '53132048', '69516588', '53095152', '53132049', '53239899', '53147269', '53138815', '69516553', '53138764', '53194375', '53185509', '53194376', '53144840', '53178633', '53178635', '53194364', '53125622', '53045160', '53194365', '53194366', '53194367', '53194368', '53185796', '53194369', '53086028', '90251330', '90251121', '30789993', '30789998', '31394282', '31393878', '29977892', '124205994', '31428350', '29545469', '29545479', '29545426', '29545421', '29545417', '29545423', '29484769', '29484785', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231231', '30230962', '60878121', '53224639', '53210038', '53081902', '53052413', '53210039', '53224626', '53168444', '53224629', '53224632', '53208783', '53083017', '53083040', '53208784', '53187334', '53187337', '53089335', '53066732', '53208785', '53178012', '53208786', '53152490', '53183929', '53146692', '53146065', '53083086', '53083102', '53113957', '53113944', '53190685', '53203056', '53167007', '53129046', '53098715', '53208787', '53208788', '53180738', '53072051']
        idealEdges = ['9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '6438432-16', '6438432-17', '6386686-0', '6386686-1', '6386686-2', '6497278-2', '6497278-3', '6497278-4', '6497278-5', '6497278-6', '6514850-51', '6439614-0', '6439614-1', '6439614-2', '6439614-3', '15255537-1', '6439607-0', '6439607-1', '6439607-2', '6439607-3', '6439607-4', '6439607-5', '6439607-6', '6439607-7', '6439607-8', '6439607-9', '6439607-10', '10497741-3', '10497743-3', '4709507-4', '4709507-5', '4709507-6', '4709507-7', '4709507-8', '4869151-0', '4869146-0', '4644189-0', '4644192-0', '4644159-0', '4869146-3', '4869146-4', '4644156-0', '4722460-0', '4722460-1', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '4743936-0', '4743934-0', '4743897-3', '4743897-4', '8116116-0', '6457969-20', '6457969-21', '6457969-22', '6476943-0', '6476943-1', '6476943-2', '6476943-3', '6476943-4', '6456455-20', '6456455-21', '6456455-22', '6456455-23', '6456455-24', '6456455-25', '6456455-26', '6456455-27', '6456455-28', '6456455-29', '6456455-30', '6456455-31', '6456455-32', '6456455-33', '6456455-34', '6456455-35', '6456455-36', '6456455-37', '6456455-38', '6456455-39', '6456455-40', '6456455-41', '6456455-42', '6456455-43', '6456455-44', '6456455-45', '6456455-46']
        
        spt = g.shortest_path_tree_retro( v85thStreet, vBeaconAve, State(g.numagencies,31505), WalkOptions() )
        vertices, edges = spt.path_retro( v85thStreet )
    
        assert spt.get_vertex(v85thStreet).payload.time == 63
        assert spt.get_vertex(v85thStreet).payload.weight == 17022003
        
        assert [v.label for v in vertices] == idealVertices
        assert [e.payload.name for e in edges] == idealEdges
        
        vBallardAve = "53115442"
        vLakeCityWay = "124175598"
        idealVertices = ['53115442', '53115445', '53115446', '53227448', '53158020', '53105937', '53148458', '53077817', '53077819', '53077821', '53077823', '53077825', '53077826', '53077828', '53077830', '53077832', '53077833', '53153886', '53181632', '53246786', '53078069', '53247761', '53129527', '53203543', '53248413', '53182343', '53156127', '53227471', '53240242', '53109739', '53248420', '53234775', '53170822', '53115167', '53209384', '53134650', '53142180', '53087702', '53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '53183554', '53213063', '53197105', '53213061', '53090659', '53213059', '53157290', '53062869', '53213057', '53213055', '53213054', '53184527', '67507140', '67507145', '67507034', '67507151', '67507040', '67507158', '53210973', '53147258', '53210974', '53210975', '60002793', '60002790', '60002789', '60002786', '60002787', '88468933', '53125662', '53195800', '88486410', '53228492', '88486425', '53215121', '88486457', '53199820', '53185765', '53233322', '53227223', '88486676', '53086030', '53086045', '53204778', '88486720', '53204762', '88486429', '53139133', '53139142', '88486453', '53072465', '30790081', '30790104', '53072467', '124181376', '30759113', '53072469', '53072472', '53072473', '53072475', '53072476', '53072477', '53072478', '124175598']
        idealEdges = ['6372784-0', '6372784-1', '6480699-3', '6517019-4', '6517019-5', '6517019-6', '6517019-7', '6346366-0', '6346366-1', '6346366-2', '6346366-3', '6346366-4', '6346366-5', '6346366-6', '6346366-7', '6346366-8', '10379527-1', '6511156-2', '6511156-3', '6511156-4', '6511156-5', '6511156-6', '6511156-7', '6511156-8', '6511156-9', '6511156-10', '6511156-11', '6511156-12', '6511156-13', '6511156-14', '9112003-0', '9112003-1', '9112003-2', '9112003-3', '9112003-4', '9112003-5', '9112003-6', '9112003-7', '9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '10425996-0', '10425996-1', '10425996-2', '10425996-3', '10425996-4', '10425996-5', '10425996-6', '10425996-7', '10425996-8', '10425996-9', '10425996-10', '10425996-11', '10425996-12', '9116336-2', '9116336-3', '9116346-1', '9116346-2', '9116346-3', '6459254-1', '6459254-2', '6459254-3', '6459254-4', '6459254-5', '4794350-10', '4794350-11', '4794350-12', '6488959-6', '6488959-7', '6488959-8', '6488959-9', '6488959-10', '6488959-11', '6488959-12', '6488959-13', '6488959-14', '6488959-15', '6488959-16', '6488959-17', '6488959-18', '6488959-19', '6488959-20', '6488959-21', '6488959-22', '6488959-23', '6488959-24', '6488959-25', '6488959-26', '6488959-27', '6488959-28', '6488959-29', '6344932-0', '6344932-1', '6344932-2', '13514591-0', '13514602-0', '13514602-1', '13514602-2', '8591344-0', '8591344-1', '8591344-2', '8591344-3', '8591344-4', '8591344-5']

        spt = g.shortest_path_tree_retro( vBallardAve, vLakeCityWay, State(g.numagencies,13684) )
        vertices, edges = spt.path_retro( vBallardAve )
        
        assert spt.get_vertex(vBallardAve).payload.time == -8
        assert spt.get_vertex(vBallardAve).payload.weight == 196300
        
        assert [v.label for v in vertices] == idealVertices
        assert [e.payload.name for e in edges] == idealEdges
            
    def xtestx_gratuitous_loop(self): #don't actually run with the test suite
        g = Graph()
        
        reader = csv.reader(open(find_resource("map.csv")))
        
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
            
        v85thStreet = "53184534"
        vBeaconAve = "53072051"
        
        n = 10
        t0 = time.time()
        for i in range(n):
            spt = g.shortest_path_tree( v85thStreet, "bogus", State(g.num_authorities,0) )
            spt.destroy()
        t1 = time.time()
        
        print "executed %d iterations in %s seconds"%(n,(t1-t0))

    def test_board_alight_graph(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "A-1" )
        g.add_vertex( "B-1" )
        
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "1", 50, 0 )
        tb.add_boarding( "2", 100, 0 )
        tb.add_boarding( "3", 200, 0 )
        
        al = Alight( "WKDY", sc, tz, 0 )
        al.add_alighting( "1", 50, 0 )
        al.add_alighting( "2", 100, 0 )
        al.add_alighting( "3", 200, 0 )
        
        g.add_edge( "A", "A-1", tb )
        g.add_edge( "A-1", "B-1", Crossing(10) )
        g.add_edge( "B-1", "B", al )
        
        spt = g.shortest_path_tree( "A", "B", State(1,0), WalkOptions() )
                
        verts, edges =  spt.path( "B" )
        assert [vert.label for vert in verts] == ["A", "A-1", "B-1", "B"]
        assert [vert.payload.weight for vert in verts] == [0, 51, 61, 61]
        assert [vert.payload.time for vert in verts] == [0, 50, 60, 60]
        spt.destroy()
            
        spt = g.shortest_path_tree( "A", "B", State(1,50), WalkOptions() )
        verts, edges =  spt.path( "B" )
        assert [vert.label for vert in verts] == ["A", "A-1", "B-1", "B"]
        assert [vert.payload.weight for vert in verts] == [0, 1, 11, 11]
        assert [vert.payload.time for vert in verts] == [50, 50, 60, 60]
        spt.destroy()
        
        spt = g.shortest_path_tree( "A", "B", State(1,51), WalkOptions() )
        verts, edges =  spt.path( "B" )
        assert [vert.label for vert in verts] == ["A", "A-1", "B-1", "B"]
        assert [vert.payload.weight for vert in verts] == [0, 50, 60, 60]
        assert [vert.payload.time for vert in verts] == [51, 100, 110, 110]
        spt.destroy()
        
        spt = g.shortest_path_tree( "A", "B", State(1,201), WalkOptions() )
        assert spt.get_vertex( "B" ) == None
        spt.destroy()
        
    def test_basic(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        g.add_vertex( "E" )
        g.add_edge( "A", "B", Street("atob", 10) )
        g.add_edge( "A", "C", Street("atoc", 10) )
        g.add_edge( "C", "D", Street("ctod", 10) )
        g.add_edge( "B", "D", Street("btod", 10) )
        g.add_edge( "D", "E", Street("btoe", 10) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
        spt = g.shortest_path_tree( "A", None, State(1,0), wo )
        spt.set_thicknesses( "A" )
        
        for edge in spt.get_vertex( "A" ).outgoing:
            if edge.to_v.label == "B":
                assert edge.thickness == 10
            elif edge.to_v.label == "C":
                assert edge.thickness == 30

        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestGraph)
    unittest.TextTestRunner(verbosity=2).run(suite)