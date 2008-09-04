import sys, os
sys.path = [os.path.dirname(os.path.abspath(__file__)) + "/.."] + sys.path
from graphserver.core import *
from graphserver.engine import Engine
import time
import unittest

import os

def get_mem_usage():
    """returns percentage and vsz mem usage of this script"""
    pid = os.getpid()
    psout = os.popen( "ps -p %s u"%pid ).read()
    
    parsed_psout = psout.split("\n")[1].split()
    
    return float(parsed_psout[3]), int( parsed_psout[4] )

import csv
class TestGraph(unittest.TestCase):
    def test_basic(self):
        g = Graph()
        assert g
        
        g.destroy()
        
    def test_add_vertex(self):
        g = Graph()
        v = g.add_vertex("home")
        assert v.label == "home"
        
        g.destroy()
        
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
        assert str(e)=="<Edge><Street name='helloworld' length='1.000000' /></Edge>"
        
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
        
        spt = g.shortest_path_tree("home", "work", State(g.numauthorities,0))
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("home").payload.weight==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        assert spt.get_vertex("work").payload.weight==2
        
        spt.destroy()
        g.destroy()
        
    def test_bogus_origin(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree("bogus", "work", State(g.numauthorities,0))
        
        assert spt == None
        
        spt = g.shortest_path_tree_retro("home", "bogus", State(g.numauthorities,0))
        
        assert spt == None
        
        
    def test_spt_retro(self):
        
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numauthorities,100))
        
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out == 0
        assert spt.get_vertex("home").degree_in == 1
        assert spt.get_vertex("home").payload.weight == 2
        assert spt.get_vertex("work").degree_in == 0
        assert spt.get_vertex("work").degree_out == 1
        assert spt.get_vertex("work").payload.weight == 0
        
        spt.destroy()
        g.destroy()
        
        
    def test_shortst_path_tree_link(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree("home", "work", State(g.numauthorities,0))
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
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numauthorities,0))
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
        
    def test_shortest_path_tree_triphopschedule(self):
        g = Graph()
        g.add_vertex("home")
        g.add_vertex("work")
        
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0,agency=0)
        
        g.add_edge("home", "work", ths )
        
        spt = g.shortest_path_tree("home", "work", State(g.numauthorities,0))
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").outgoing[0].payload.__class__ == TripHop
        assert spt.get_vertex("work").incoming[0].payload.__class__ == TripHop
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
        spt.destroy()
        g.destroy()
        
    def test_spt_ths_retro(self):
        g = Graph()
        g.add_vertex("home")
        g.add_vertex("work")
        
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0,agency=0)
        
        g.add_edge("home", "work", ths )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numauthorities,2*3600))
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").incoming[0].payload.__class__ == TripHop
        assert spt.get_vertex("work").outgoing[0].payload.__class__ == TripHop
        assert spt.get_vertex("home").incoming[0].payload.trip_id == "Bar to Cow"
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
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sprime = e.walk(State(g.numauthorities,0))
        
        assert str(sprime)=="<state time='282352' weight='2147483647' dist_walked='240000.0' num_transfers='0' prev_edge_type='0' prev_edge_name='helloworld'></state>"

        g.destroy()
        
    def xtestx_shortest_path_tree_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numauthorities,0))
        
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
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numauthorities,0))
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
        
        spt = g.shortest_path_tree("home", "work", State(g.numauthorities))
        sp = spt.path("work")
        
        assert sp
        
    def test_shortest_path_tree_triphopschedule_wrongday(self):
        g = Graph()
        
        rawhops = [(10,     20,'Foo to Bar')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 10, [1]) )
        ths = TripHopSchedule(hops=rawhops, service_id=2, calendar=cal, timezone_offset=0,agency=0)
        
        g.add_vertex("A")
        g.add_vertex("B")
        
        g.add_edge("A", "B", ths)
        
        sp = g.shortest_path_tree("A", "B", State(g.numauthorities,0) )
        
        assert sp.vertices
        
    def xtestx_shortest_path_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sp = g.shortest_path("home", "work", State(g.numauthorities))
        
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
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(g.numauthorities,0) )
        
        assert spt.get_vertex("Seattle").outgoing[0].payload.name == "I-5 south"
        
        g.add_vertex( "Portland-busstop" )
        g.add_vertex( "Seattle-busstop" )
        
        g.add_edge( "Seattle", "Seattle-busstop", Link() )
        g.add_edge( "Seattle-busstop", "Seattle", Link() )
        g.add_edge( "Portland", "Portland-busstop", Link() )
        g.add_edge( "Portland-busstop", "Portland", Link() )
        
        spt = g.shortest_path_tree( "Seattle", "Seattle-busstop", State(g.numauthorities,0) )
        assert spt.get_vertex("Seattle-busstop").incoming[0].payload.__class__ == Link
        spt.destroy()
        
        spt = g.shortest_path_tree( "Seattle-busstop", "Portland", State(g.numauthorities,0) )
        assert spt.get_vertex("Portland").incoming[0].payload.__class__ == Street
        spt.destroy()
        
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 86400, [1,2]) )
        rawhops = [(10,     20,'A'),
                   (15,     30,'B'),
                   (400,   430,'C')]
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0,agency=0)
        
        g.add_edge( "Seattle-busstop", "Portland-busstop", ths )
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(g.numauthorities,0) )
        
        assert spt.get_vertex( "Portland" ).incoming[0].from_v.incoming[0].from_v.incoming[0].from_v.label == "Seattle"
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(g.numauthorities,0) )
        vertices, edges = spt.path( "Portland" )
        
        assert [v.label for v in vertices] == ['Seattle', 'Seattle-busstop', 'Portland-busstop', 'Portland']
        assert [e.payload.__class__ for e in edges] == [Link, TripHop, Link]
        
        spt.destroy()
        g.destroy()
        
    def test_hello_world_retro(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        
        g.add_edge( "Seattle", "Portland", Street("I-5 south", 5000) )
        g.add_edge( "Portland", "Seattle", Street("I-5 north", 5500) )
        
        spt = g.shortest_path_tree_retro( "Seattle", "Portland", State(g.numauthorities,0) )
        
        assert spt.get_vertex("Seattle").incoming[0].payload.name == "I-5 south"
        
        g.add_vertex( "Portland-busstop" )
        g.add_vertex( "Seattle-busstop" )
        
        g.add_edge( "Seattle", "Seattle-busstop", Link() )
        g.add_edge( "Seattle-busstop", "Seattle", Link() )
        g.add_edge( "Portland", "Portland-busstop", Link() )
        g.add_edge( "Portland-busstop", "Portland", Link() )
        
        spt = g.shortest_path_tree_retro( "Seattle", "Seattle-busstop", State(g.numauthorities,0) )
        assert spt.get_vertex("Seattle-busstop").outgoing[0].payload.__class__ == Link
        spt.destroy()
        
        spt = g.shortest_path_tree_retro( "Seattle-busstop", "Portland", State(g.numauthorities,0) )
        assert spt.get_vertex("Portland").outgoing[0].payload.__class__ == Street
        spt.destroy()
        
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 86400, [1,2]) )
        rawhops = [(10,     20,'A'),
                   (15,     30,'B'),
                   (400,   430,'C')]
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0,agency=0)
        
        g.add_edge( "Seattle-busstop", "Portland-busstop", ths )
        
        spt = g.shortest_path_tree_retro( "Seattle", "Portland", State(g.numauthorities,430) )
        
        assert spt.get_vertex("Portland").outgoing[0].to_v.outgoing[0].to_v.outgoing[0].to_v.label == "Seattle"
        
        spt = g.shortest_path_tree_retro( "Seattle", "Portland", State(g.numauthorities,430) )
        vertices, edges = spt.path_retro( "Seattle" )
        
        assert [v.label for v in vertices] == ['Seattle', 'Seattle-busstop', 'Portland-busstop', 'Portland']
        assert [e.payload.__class__ for e in edges] == [Link, TripHop, Link]
        
        spt.destroy()
        g.destroy()
        
    def test_get_route(self):
        "Check it finds the route we expect"
        
        g = Graph()
        
        reader = csv.reader(open("map.csv"))
        
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
            
        v85thStreet = "53184534"
        vBeaconAve = "53072051"
        idealVertices = ['53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '53183554', '53213063', '53197105', '53213061', '53090659', '53213059', '53157290', '53062869', '53213057', '53213055', '53213054', '53184527', '67507140', '67507145', '67507034', '67507151', '67507040', '67507158', '67507048', '67507166', '67507051', '67507176', '67507057', '67507126', '53233319', '53147253', '53233320', '53233321', '60002786', '60002787', '60002788', '88468927', '53125664', '53116774', '53116776', '88486408', '53116778', '88486413', '53116779', '88486416', '53116784', '53116788', '31394358', '53070243', '30790093', '31394277', '124206007', '31394282', '31393878', '29977892', '124205994', '31428350', '29545469', '29545479', '29545426', '29545421', '29545417', '29545423', '29484769', '29484785', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231231', '30230962', '60878121', '53224639', '53210038', '53081902', '53052413', '53210039', '53224626', '53168444', '53224629', '53224632', '53208783', '53083017', '53083040', '53208784', '53187334', '53187337', '53089335', '53066732', '53208785', '53178012', '53208786', '53152490', '53183929', '53146692', '53146065', '53083086', '53083102', '53113957', '53113944', '53190685', '53203056', '53167007', '53129046', '53098715', '53208787', '53208788', '53180738', '53072051']
        idealEdges = ['9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '10425996-0', '10425996-1', '10425996-2', '10425996-3', '10425996-4', '10425996-5', '10425996-6', '10425996-7', '10425996-8', '10425996-9', '10425996-10', '10425996-11', '10425996-12', '9116336-2', '9116336-3', '9116346-1', '9116346-2', '9116346-3', '9116346-4', '9116346-5', '9116346-6', '9116346-7', '9116346-8', '9116346-9', '6488959-1', '6488959-2', '6488959-3', '6488959-4', '6488959-5', '6488959-6', '4864595-10', '8027224-0', '8027224-1', '6381214-5', '6381214-6', '6373885-0', '6373885-1', '6373885-2', '6373885-3', '6373885-4', '6373885-5', '6373885-6', '6446116-3', '4864592-0', '4864592-1', '4864578-0', '13517028-0', '13517029-0', '4709507-6', '4709507-7', '4709507-8', '4869151-0', '4869146-0', '4644189-0', '4644192-0', '4644159-0', '4869146-3', '4869146-4', '4644156-0', '4722460-0', '4722460-1', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '4743936-0', '4743934-0', '4743897-3', '4743897-4', '8116116-0', '6457969-20', '6457969-21', '6457969-22', '6476943-0', '6476943-1', '6476943-2', '6476943-3', '6476943-4', '6456455-20', '6456455-21', '6456455-22', '6456455-23', '6456455-24', '6456455-25', '6456455-26', '6456455-27', '6456455-28', '6456455-29', '6456455-30', '6456455-31', '6456455-32', '6456455-33', '6456455-34', '6456455-35', '6456455-36', '6456455-37', '6456455-38', '6456455-39', '6456455-40', '6456455-41', '6456455-42', '6456455-43', '6456455-44', '6456455-45', '6456455-46']
        
        spt = g.shortest_path_tree( v85thStreet, vBeaconAve, State(g.numauthorities,0) )
        vertices, edges = spt.path( vBeaconAve )
        
        assert spt.get_vertex("53072051").payload.time == 31505
        assert spt.get_vertex("53072051").payload.weight == 39562277
        
        assert( False not in [l==r for l,r in zip( [v.label for v in vertices], idealVertices )] )
        assert( False not in [l==r for l,r in zip( [e.payload.name for e in edges], idealEdges )] )
            
        vBallardAve = "53115442"
        vLakeCityWay = "124175598"
        idealVertices = ['53115442', '53115445', '53115446', '53227448', '53158020', '53105937', '53148458', '53077817', '53077819', '53077821', '53077823', '53077825', '60413953', '53097655', '60413955', '53196479', '53248412', '53245437', '53153886', '53181632', '53246786', '53078069', '53247761', '53129527', '53203543', '53248413', '53182343', '53156127', '53227471', '53240242', '53109739', '53248420', '53234775', '53170822', '53115167', '53209384', '53134650', '53142180', '53087702', '53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '53183554', '53213063', '53197105', '53213061', '53090659', '53213059', '53157290', '53062869', '53213057', '53213055', '53213054', '53184527', '67507140', '67507145', '67507034', '67507151', '67507040', '67507158', '67507048', '67507166', '67507051', '67507176', '67507057', '67507126', '53233319', '53147253', '53233320', '53233321', '60002786', '60002787', '88468933', '53125662', '53195800', '88486410', '53228492', '88486425', '53215121', '88486457', '53199820', '53185765', '53233322', '53227223', '88486676', '53086030', '53086045', '53204778', '88486720', '53204762', '88486429', '53139133', '53139142', '88486453', '53072465', '30790081', '30790104', '53072467', '124181376', '30759113', '53072469', '53072472', '53072473', '53072475', '53072476', '53072477', '53072478', '124175598']
        idealEdges = ['6372784-0', '6372784-1', '6480699-3', '6517019-4', '6517019-5', '6517019-6', '6517019-7', '6346366-0', '6346366-1', '6346366-2', '6346366-3', '10425981-2', '8072147-2', '8072147-3', '6441828-10', '22758990-0', '6511156-0', '6511156-1', '6511156-2', '6511156-3', '6511156-4', '6511156-5', '6511156-6', '6511156-7', '6511156-8', '6511156-9', '6511156-10', '6511156-11', '6511156-12', '6511156-13', '6511156-14', '9112003-0', '9112003-1', '9112003-2', '9112003-3', '9112003-4', '9112003-5', '9112003-6', '9112003-7', '9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '10425996-0', '10425996-1', '10425996-2', '10425996-3', '10425996-4', '10425996-5', '10425996-6', '10425996-7', '10425996-8', '10425996-9', '10425996-10', '10425996-11', '10425996-12', '9116336-2', '9116336-3', '9116346-1', '9116346-2', '9116346-3', '9116346-4', '9116346-5', '9116346-6', '9116346-7', '9116346-8', '9116346-9', '6488959-1', '6488959-2', '6488959-3', '6488959-4', '6488959-5', '6488959-6', '6488959-7', '6488959-8', '6488959-9', '6488959-10', '6488959-11', '6488959-12', '6488959-13', '6488959-14', '6488959-15', '6488959-16', '6488959-17', '6488959-18', '6488959-19', '6488959-20', '6488959-21', '6488959-22', '6488959-23', '6488959-24', '6488959-25', '6488959-26', '6488959-27', '6488959-28', '6488959-29', '6344932-0', '6344932-1', '6344932-2', '13514591-0', '13514602-0', '13514602-1', '13514602-2', '8591344-0', '8591344-1', '8591344-2', '8591344-3', '8591344-4', '8591344-5']
        
        spt = g.shortest_path_tree( vBallardAve, vLakeCityWay, State(g.numauthorities,0) )
        vertices, edges = spt.path( vLakeCityWay )
        
        assert spt.get_vertex("124175598").payload.time == 13684
        assert spt.get_vertex("124175598").payload.weight == 6547467
        
        assert( False not in [l==r for l,r in zip( [v.label for v in vertices], idealVertices )] )
        assert( False not in [l==r for l,r in zip( [e.payload.name for e in edges], idealEdges )] )
            
        #one last time
        vSandPointWay = "32096172"
        vAirportWay = "60147448"
        idealVertices = ['32096172', '60411560', '32096173', '32096176', '53110403', '32096177', '32096180', '53208261', '32096181', '60411559', '32096184', '53164136', '32096185', '32096190', '32096191', '32096194', '53123806', '32096196', '32096204', '53199337', '32096205', '32096208', '60411513', '32096209', '53040444', '32096212', '60411512', '53208255', '32096216', '53079385', '53079384', '32096219', '31192107', '31430499', '59948312', '31430457', '31430658', '29973173', '31430639', '29977895', '30012801', '31430516', '30012733', '29464742', '32271244', '31430321', '29464754', '31430318', '29973106', '31429815', '29464758', '31429758', '32103448', '60701659', '29464594', '29463661', '59677238', '59677231', '29463657', '29463479', '29449421', '29449412', '29545007', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231566', '30231379', '30230524', '30887745', '30887637', '30887631', '30887106', '60147424', '53131178', '53128410', '53131179', '53027159', '60147448']
        idealEdges = ['4910430-0', '4910430-1', '4910417-0', '4910416-0', '4910416-1', '4910414-0', '4910413-0', '4910413-1', '4910412-0', '4910412-1', '4910410-0', '4910410-1', '4910408-0', '4910405-0', '4910405-1', '4910405-2', '4910405-3', '4910402-0', '4910399-0', '4910399-1', '4910397-0', '4910394-0', '4910394-1', '4910392-0', '4910392-1', '4910385-0', '4910385-1', '4910385-2', '4910385-3', '4910385-4', '4910385-5', '4910384-0', '4910384-1', '4869358-0', '4869358-1', '4869358-2', '4869358-3', '4869357-0', '4869357-1', '4869357-2', '4869357-3', '4869357-4', '4869357-5', '4636137-0', '4636137-1', '4636137-2', '4636137-3', '4636137-4', '4636137-5', '4636137-6', '4708973-0', '4708973-1', '4708973-2', '4708973-3', '4636201-0', '4708972-0', '4708972-1', '4708972-2', '4636105-0', '4636093-0', '4729956-0', '4644053-0', '4644064-0', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '15257848-2', '15257848-3', '15257848-4', '4810339-0', '4810342-0', '4810342-1', '4810337-0', '4810290-0', '8044406-0', '15240328-7', '15240328-8', '15240328-9', '15240328-10']
        
        
        spt = g.shortest_path_tree( vSandPointWay, vAirportWay, State(g.numauthorities,0) )
        vertices, edges = spt.path( vAirportWay )
        
        assert spt.get_vertex("60147448").payload.time == 21082
        assert spt.get_vertex("60147448").payload.weight == 17068232
        
        assert( False not in [l==r for l,r in zip( [v.label for v in vertices], idealVertices )] )
        assert( False not in [l==r for l,r in zip( [e.payload.name for e in edges], idealEdges )] )
            
    def test_get_route_retro(self):
        "Check it finds the route we expect, in reverse"
        
        g = Graph()
        
        reader = csv.reader(open("map.csv"))
        
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
            
        v85thStreet = "53184534"
        vBeaconAve = "53072051"
        idealVertices = ['53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '69516594', '53132048', '69516588', '53095152', '53132049', '53239899', '53147269', '53138815', '69516553', '53138764', '53194375', '53185509', '53194376', '53144840', '53178633', '53178635', '53194364', '53125622', '53045160', '53194365', '53194366', '53194367', '53194368', '53185796', '53194369', '53086028', '90251330', '90251121', '30789993', '30789998', '31394282', '31393878', '29977892', '124205994', '31428350', '29545469', '29545479', '29545426', '29545421', '29545417', '29545423', '29484769', '29484785', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231231', '30230962', '60878121', '53224639', '53210038', '53081902', '53052413', '53210039', '53224626', '53168444', '53224629', '53224632', '53208783', '53083017', '53083040', '53208784', '53187334', '53187337', '53089335', '53066732', '53208785', '53178012', '53208786', '53152490', '53183929', '53146692', '53146065', '53083086', '53083102', '53113957', '53113944', '53190685', '53203056', '53167007', '53129046', '53098715', '53208787', '53208788', '53180738', '53072051']
        idealEdges = ['9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '6438432-16', '6438432-17', '6386686-0', '6386686-1', '6386686-2', '6497278-2', '6497278-3', '6497278-4', '6497278-5', '6497278-6', '6514850-51', '6439614-0', '6439614-1', '6439614-2', '6439614-3', '15255537-1', '6439607-0', '6439607-1', '6439607-2', '6439607-3', '6439607-4', '6439607-5', '6439607-6', '6439607-7', '6439607-8', '6439607-9', '6439607-10', '10497741-3', '10497743-3', '4709507-4', '4709507-5', '4709507-6', '4709507-7', '4709507-8', '4869151-0', '4869146-0', '4644189-0', '4644192-0', '4644159-0', '4869146-3', '4869146-4', '4644156-0', '4722460-0', '4722460-1', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '4743936-0', '4743934-0', '4743897-3', '4743897-4', '8116116-0', '6457969-20', '6457969-21', '6457969-22', '6476943-0', '6476943-1', '6476943-2', '6476943-3', '6476943-4', '6456455-20', '6456455-21', '6456455-22', '6456455-23', '6456455-24', '6456455-25', '6456455-26', '6456455-27', '6456455-28', '6456455-29', '6456455-30', '6456455-31', '6456455-32', '6456455-33', '6456455-34', '6456455-35', '6456455-36', '6456455-37', '6456455-38', '6456455-39', '6456455-40', '6456455-41', '6456455-42', '6456455-43', '6456455-44', '6456455-45', '6456455-46']
        
        spt = g.shortest_path_tree_retro( v85thStreet, vBeaconAve, State(g.numauthorities,31505) )
        vertices, edges = spt.path_retro( v85thStreet )
        
        assert spt.get_vertex(v85thStreet).payload.time == 63
        assert spt.get_vertex(v85thStreet).payload.weight == 39360085
        
        assert [v.label for v in vertices] == idealVertices
        assert [e.payload.name for e in edges] == idealEdges
        
        vBallardAve = "53115442"
        vLakeCityWay = "124175598"
        idealVertices = ['53115442', '53115445', '53115446', '53227448', '53158020', '53105937', '53148458', '53077817', '53077819', '53077821', '53077823', '53077825', '60413953', '53097655', '60413955', '53196479', '53248412', '53245437', '53153886', '53181632', '53246786', '53078069', '53247761', '53129527', '53203543', '53248413', '53182343', '53156127', '53227471', '53240242', '53109739', '53248420', '53234775', '53170822', '53115167', '53209384', '53134650', '53142180', '53087702', '53184534', '53193013', '69374666', '53193014', '69474340', '53185600', '53077802', '69474361', '53090673', '53193015', '53193016', '53193017', '53193018', '53189027', '53193019', '53193020', '53112767', '53193021', '53183554', '53213063', '53197105', '53213061', '53090659', '53213059', '53157290', '53062869', '53213057', '53213055', '53213054', '53184527', '67507140', '67507145', '67507034', '67507151', '67507040', '67507158', '67507048', '67507166', '67507051', '67507176', '67507057', '67507126', '53233319', '53147253', '53233320', '53233321', '60002786', '60002787', '88468933', '53125662', '53195800', '88486410', '53228492', '88486425', '53215121', '88486457', '53199820', '53185765', '53233322', '53227223', '88486676', '53086030', '53086045', '53204778', '88486720', '53204762', '88486429', '53139133', '53139142', '88486453', '53072465', '30790081', '30790104', '53072467', '124181376', '30759113', '53072469', '53072472', '53072473', '53072475', '53072476', '53072477', '53072478', '124175598']
        idealEdges = ['6372784-0', '6372784-1', '6480699-3', '6517019-4', '6517019-5', '6517019-6', '6517019-7', '6346366-0', '6346366-1', '6346366-2', '6346366-3', '10425981-2', '8072147-2', '8072147-3', '6441828-10', '22758990-0', '6511156-0', '6511156-1', '6511156-2', '6511156-3', '6511156-4', '6511156-5', '6511156-6', '6511156-7', '6511156-8', '6511156-9', '6511156-10', '6511156-11', '6511156-12', '6511156-13', '6511156-14', '9112003-0', '9112003-1', '9112003-2', '9112003-3', '9112003-4', '9112003-5', '9112003-6', '9112003-7', '9112003-8', '6438432-0', '6438432-1', '6438432-2', '6438432-3', '6438432-4', '6438432-5', '6438432-6', '6438432-7', '6438432-8', '6438432-9', '6438432-10', '6438432-11', '6438432-12', '6438432-13', '6438432-14', '6438432-15', '10425996-0', '10425996-1', '10425996-2', '10425996-3', '10425996-4', '10425996-5', '10425996-6', '10425996-7', '10425996-8', '10425996-9', '10425996-10', '10425996-11', '10425996-12', '9116336-2', '9116336-3', '9116346-1', '9116346-2', '9116346-3', '9116346-4', '9116346-5', '9116346-6', '9116346-7', '9116346-8', '9116346-9', '6488959-1', '6488959-2', '6488959-3', '6488959-4', '6488959-5', '6488959-6', '6488959-7', '6488959-8', '6488959-9', '6488959-10', '6488959-11', '6488959-12', '6488959-13', '6488959-14', '6488959-15', '6488959-16', '6488959-17', '6488959-18', '6488959-19', '6488959-20', '6488959-21', '6488959-22', '6488959-23', '6488959-24', '6488959-25', '6488959-26', '6488959-27', '6488959-28', '6488959-29', '6344932-0', '6344932-1', '6344932-2', '13514591-0', '13514602-0', '13514602-1', '13514602-2', '8591344-0', '8591344-1', '8591344-2', '8591344-3', '8591344-4', '8591344-5']
        
        spt = g.shortest_path_tree_retro( vBallardAve, vLakeCityWay, State(g.numauthorities,13684) )
        vertices, edges = spt.path_retro( vBallardAve )
        
        assert spt.get_vertex(vBallardAve).payload.time == 0
        assert spt.get_vertex(vBallardAve).payload.weight == 6559168
        
        assert [v.label for v in vertices] == idealVertices
        assert [e.payload.name for e in edges] == idealEdges
            
        #one last time
        vSandPointWay = "32096172"
        vAirportWay = "60147448"
        idealVertices = ['32096172', '60411560', '32096173', '32096176', '53110403', '32096177', '32096180', '53208261', '32096181', '60411559', '32096184', '53164136', '32096185', '32096190', '32096191', '32096194', '53123806', '32096196', '32096204', '53199337', '32096205', '32096208', '60411513', '32096209', '53040444', '32096212', '60411512', '53208255', '32096216', '53079385', '53079384', '32096219', '31192107', '31430499', '59948312', '31430457', '31430658', '29973173', '31430639', '29977895', '30012801', '31430516', '30012733', '29464742', '32271244', '31430321', '29464754', '31430318', '29973106', '31429815', '29464758', '31429758', '32103448', '60701659', '29464594', '29463661', '59677238', '59677231', '29463657', '29463479', '29449421', '29449412', '29545007', '29545373', '29979589', '30078988', '30079048', '244420183', '29979596', '29979598', '30230262', '30230264', '30279409', '30279408', '30230266', '30230273', '30230277', '30230281', '30230300', '30230506', '30231566', '30231379', '30230524', '30887745', '30887637', '30887631', '30887106', '60147424', '53131178', '53128410', '53131179', '53027159', '60147448']
        idealEdges = ['4910430-0', '4910430-1', '4910417-0', '4910416-0', '4910416-1', '4910414-0', '4910413-0', '4910413-1', '4910412-0', '4910412-1', '4910410-0', '4910410-1', '4910408-0', '4910405-0', '4910405-1', '4910405-2', '4910405-3', '4910402-0', '4910399-0', '4910399-1', '4910397-0', '4910394-0', '4910394-1', '4910392-0', '4910392-1', '4910385-0', '4910385-1', '4910385-2', '4910385-3', '4910385-4', '4910385-5', '4910384-0', '4910384-1', '4869358-0', '4869358-1', '4869358-2', '4869358-3', '4869357-0', '4869357-1', '4869357-2', '4869357-3', '4869357-4', '4869357-5', '4636137-0', '4636137-1', '4636137-2', '4636137-3', '4636137-4', '4636137-5', '4636137-6', '4708973-0', '4708973-1', '4708973-2', '4708973-3', '4636201-0', '4708972-0', '4708972-1', '4708972-2', '4636105-0', '4636093-0', '4729956-0', '4644053-0', '4644064-0', '4722460-2', '4722460-3', '4722460-4', '4722460-5', '4722460-6', '14017470-0', '14017470-1', '5130429-0', '13866257-0', '13866256-0', '4748963-0', '4748962-0', '4748962-1', '15257844-0', '15257848-0', '15257848-1', '15257848-2', '15257848-3', '15257848-4', '4810339-0', '4810342-0', '4810342-1', '4810337-0', '4810290-0', '8044406-0', '15240328-7', '15240328-8', '15240328-9', '15240328-10']
        
        spt = g.shortest_path_tree_retro( vSandPointWay, vAirportWay, State(g.numauthorities,21082) )
        vertices, edges = spt.path_retro( vSandPointWay )
        
        assert spt.get_vertex(vSandPointWay).payload.time == 0
        assert spt.get_vertex(vSandPointWay).payload.weight == 17035839
        
        assert [v.label for v in vertices] == idealVertices
        assert [e.payload.name for e in edges] == idealEdges
            
    def xtestx_gratuitous_loop(self): #don't actually run with the test suite
        g = Graph()
        
        reader = csv.reader(open("map.csv"))
        
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



import time
from random import randint
class TestGraphPerformance(unittest.TestCase):
    def test_load_performance(self):
        g = Graph()
        
        reader = csv.reader(open("map.csv"))
        
        t0 = time.time()
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
        t1 = time.time()
        dt = t1-t0
        
        limit = 0.8
        print "Graph loaded in %f s; limit %f s"%(dt,limit)
        assert dt <= limit
        
    def test_spt_performance(self):
        g = Graph()
        
        reader = csv.reader(open("map.csv"))
        
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
            
        runtimes = []
        
        nodeids = ["53204010","53116165","53157403",
                   "30279744","67539645","53217469",
                   "152264675","53062837","53190677",
                   "53108368","91264868","53145350",
                   "53156103","53139148","108423294",
                   "53114499","53110306","53132736",
                   "53103049","53178033"] #twenty random node ids in the given graph
        for nodeid in nodeids:
            t0 = time.time()
            spt = g.shortest_path_tree( nodeid, None, State(0) )
            t1 = time.time()
            runtimes.append( t1-t0 )
            
        average = sum(runtimes)/len(runtimes)
        
        limit = 0.031
        print "average runtime is %f s; limit %f s"%(average,limit)
        assert average < limit
        
    def test_stress(self):
        g = Graph()
        
        reader = csv.reader(open("map.csv"))
        
        nodeids = {}
        for wayid, fromv, tov, length in reader:
            nodeids[fromv] = True
            nodeids[tov] = True
            
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
        nodeids = nodeids.keys()
        
        mempercent, memblock = get_mem_usage()
        changes = []
        for i in range(40):
            spt = g.shortest_path_tree( nodeids[ randint(0,len(nodeids)-1) ], "bogus", State(0) )
            spt.destroy()
            
            thispercent, thisblock = get_mem_usage()
            
            #print "last iteration memory usage: %d"%memblock
            #print "this iteration memory usage: %d"%thisblock
            #print "---"
            print thispercent, thisblock
            changes.append( cmp(memblock, thisblock) )
            
            memblock = thisblock
        
        assert sum(changes) >= -1 #memory usage only increases in one iteration out of all

class TestState(unittest.TestCase):
    def test_basic(self):
        s = State(1,0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge_name == None
        assert s.prev_edge_type == 5
        assert s.num_agencies == 1
        assert s.service_period(0) == None
        
    def test_basic_multiple_calendars(self):
        s = State(2,0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge_name == None
        assert s.prev_edge_type == 5
        assert s.num_agencies == 2
        assert s.service_period(0) == None
        assert s.service_period(1) == None

    def test_set_cal(self):
        s = State(1,0)
        sp = ServicePeriod(0, 1*3600*24, [1,2])
        
        try:
            s.set_calendar_day(1, cal)
            assert False #should have failed by now
        except:
            pass
        
        s.set_service_period(0, sp)
        
        spout = s.service_period(0)
        
        assert spout.begin_time == 0
        assert spout.end_time == 86400
        assert spout.service_ids == [1,2]
        
    def test_destroy(self):
        s = State(1)
        
        s.destroy() #did we segfault?
        
        try:
            print s.time
            assert False #should have popped exception by now
        except:
            pass
        
        try:
            s.destroy()
            assert False
        except:
            pass
        
    def test_clone(self):
        
        s = State(1,0)
        sp = ServicePeriod(0, 1*3600*24, [1,2])
        s.set_service_period(0,sp)
        
        s2 = s.clone()
        
        s.clone()
        
        assert s2.time == 0
        assert s2.weight == 0
        assert s2.dist_walked == 0
        assert s2.num_transfers == 0
        assert s2.prev_edge_name == None
        assert s2.prev_edge_type == 5
        assert s2.num_agencies == 1
        assert s2.service_period(0).to_xml() == "<ServicePeriod begin_time='0' end_time='86400' service_ids='1,2'/>"

class TestStreet(unittest.TestCase):
    def test_street(self):
        s = Street("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<Street name='mystreet' length='1.100000' />"
        
    def test_destroy(self):
        s = Street("mystreet", 1.1)
        s.destroy()
        
        assert s.soul==None
        
    def test_street_big_length(self):
        s = Street("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<Street name='longstreet' length='240000.000000' />"
        
    def test_walk(self):
        s = Street("longstreet", 2)
        
        after = s.walk(State(0,0))
        assert after.time == 2
        assert after.weight == 4
        assert after.dist_walked == 2
        assert after.prev_edge_type == 0
        assert after.prev_edge_name == "longstreet"
        assert after.num_agencies == 0
        
    def test_walk_back(self):
        s = Street("longstreet", 2)
        
        before = s.walk_back(State(0,100))
        
        assert before.time == 98
        assert before.weight == 4
        assert before.dist_walked == 2.0
        assert before.prev_edge_type == 0
        assert before.prev_edge_name == "longstreet"
        assert before.num_agencies == 0
        
class TestPyPayload(unittest.TestCase):
    def _minimal_graph(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        return g
    
    def test_basic(self):
        p = NoOpPyPayload(1.1)
        
    def test_cast(self):
        g = self._minimal_graph()
        e = NoOpPyPayload(1.2)
        
        ed = g.add_edge( "Seattle", "Portland", e )
        print ed.payload
        assert e == ed.payload
        ep = ed.payload # uses EdgePayload.from_pointer internally.
        assert e == ep
        assert ep.num == 1.2
    
        
    
    def test_walk(self):
        class IncTimePayload(GenericPyPayload):
            def walk_impl(self, state):
                state.time = state.time + 10
                state.weight = 5
                return state
            
            def walk_back_impl(self, state):
                state.time = state.time - 10
                state.weight = 0
                return state
            
            def collapse(self, state):
                return Link()
            
        g = self._minimal_graph()
        ed = g.add_edge( "Seattle", "Portland", IncTimePayload())
        assert(isinstance(ed.payload,IncTimePayload))
        s = State(1,1)
        assert s.time == 1
        s1 = ed.walk(s)
        assert s1
        assert s.time == 1
        assert s1.soul != s.soul
        assert s1.time == 11
        assert s1.weight == 5
        s2 = ed.walk_back(s1)
        assert s2
        assert s2.time == 1
        assert s2.weight == 0
        
    def test_failures(self):
        class ExceptionRaiser(GenericPyPayload):
            def bad_stuff(self, state):
                raise Exception("I am designed to fail.")
            walk_impl = bad_stuff
            walk_back_impl = bad_stuff
            collapse_impl = bad_stuff
            collapse_back_impl = bad_stuff

        g = self._minimal_graph()
        ed = g.add_edge( "Seattle", "Portland", ExceptionRaiser())
        
        
        ed.walk(State(1,0)) 
        ed.walk_back(State(1,0))
        ed.payload.collapse(State(1,0))
        ed.payload.collapse_back(State(1,0))


class TestLink(unittest.TestCase):
    def link_test(self):
        l = Link()
        assert l
        assert str(l)=="<Link name='LINK'/>"
        
    def test_destroy(self):
        l = Link()
        l.destroy()
        
        assert l.soul==None
        
    def test_name(self):
        l = Link()
        assert l.name == "LINK"
        
    def test_walk(self):
        l = Link()
        
        after = l.walk(State(1,0))
        
        assert after.time==0
        assert after.weight==0
        assert after.dist_walked==0
        assert after.prev_edge_type==3
        assert after.prev_edge_name=="LINK"
        assert after.num_agencies == 1
        
    def test_walk_back(self):
        l = Link()
        
        before = l.walk_back(State(1,0))
        
        assert before.time == 0
        assert before.weight == 0
        assert before.dist_walked == 0.0
        assert before.prev_edge_type == 3
        assert before.prev_edge_name == "LINK"
        assert before.num_agencies == 1

from graphserver.core import Wait
class TestWait(unittest.TestCase):
    def test_wait(self):
        waitend = 100
        utcoffset = 0
        w = Wait(waitend, utcoffset)
        assert w.end == waitend
        assert w.utcoffset == utcoffset
        assert w.to_xml() == "<Wait end='100' utcoffset='0' />"

        s = State(1,0)
        sprime = w.walk(s)
        assert sprime.time == 100
        assert sprime.weight == 100

        s = State(1, 150)
        sprime = w.walk_back(s)
        assert sprime.time == 100
        assert sprime.weight == 50
        
        s = State(1, 86400)
        sprime = w.walk(s)
        assert sprime.time == 86500
        assert sprime.weight == 100

        w.destroy()
        
        w = Wait(100, -20)
        assert w.end == 100
        assert w.utcoffset == -20
        s = State(1, 86400)
        sprime = w.walk(s)
        assert sprime.weight == 120
        
    def test_august(self):
        # noon, -7 hours off UTC, as America/Los_Angeles in summer
        w = Wait(43200, -25200)
        
        # one calendar, noon august 27, America/Los_Angeles
        s = State(1, 1219863600)
        
        assert w.walk(s).time == 1219863600
        
        # one calendar, 11:55 AM August 27 2008, America/Los_Angeles
        s = State(1, 1219863300)
        assert w.walk(s).time == 1219863600
        assert w.walk(s).weight == 300

class TestTripHop(unittest.TestCase):
    
    def test_triphop(self):
        sc = ServiceCalendar()
        sc.add_period( ServicePeriod( 0, 86400, [1] ) )
        
        th = TripHop(25, 100, "foo", sc, timezone_offset=0, agency=0, service_id=1)

        assert th.depart == 25
        assert th.arrive == 100
        assert th.transit == 75
        assert th.trip_id == "foo"
        assert th.calendar.head.begin_time==0
        assert th.timezone_offset == 0
        assert th.agency == 0
        assert th.service_id == 1

        s = State(1,0)
        sprime = th.walk(s)
        assert sprime.time == 100
        assert sprime.weight == 100

        s = State(1, 200)
        sprime = th.walk_back(s)
        assert sprime
        assert sprime.time==25
        assert sprime.weight==175
        
    def test_unixtime(self):
        sc = ServiceCalendar()
        sc.add_period( ServicePeriod( 0,86399,[1]) )
        sc.add_period( ServicePeriod( 86400, 86400+86399, [1]) )
        
        th = TripHop(25,100,"foo",sc, timezone_offset=0, agency=0, service_id=1)
        
        time = 25+86400
        
        s = State(1,time)  
        sprime = th.walk(s)
        assert sprime.weight==75
        assert sprime.time==time+75
        
    def test_august(self):
        sc = ServiceCalendar()
        #beginning of august 27 to end of august 27, America/Los_Angeles.
        sc.add_period( ServicePeriod( 1219820400, 1219906799, [1]) ) 
        
        #triphop from 12:00 noon to 12:05 PM. timezone offset is -7 hours, corresponding to west coast on daylight savings time
        th = TripHop( 43200, 43500, "foo", sc, timezone_offset=-7*3600, agency=0, service_id=1 )
        
        # noon on august 27th, America/Los_Angeles
        time = 1219863600
        
        s = State(1,time)
        ret = th.walk(s)
        assert ret.time == 1219863900 #12:05PM august 27th, America/Los_Angeles
        
        

class TestTriphopSchedule(unittest.TestCase):
    
    def setUp(self):
        pass
        
    def tearDown(self):
        pass
    
    def test_triphop_schedule(self):
        
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        # using a tuple
        sc = ServiceCalendar()
        sc.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(rawhops, 1, sc, 0, agency=0)
        
        assert ths.timezone_offset == 0
        
        h1 = ths.triphops[0]
        assert h1.depart == 0
        assert h1.arrive == 1*3600
        assert h1.trip_id == "Foo to Bar"
        h2 = ths.triphops[1]
        assert h2.depart == 1*3600
        assert h2.arrive == 2*3600
        assert h2.trip_id == "Bar to Cow"
                               
        assert(ths.triphops[0].trip_id == 'Foo to Bar')
        assert(len(ths.triphops) == 2)
        assert str(ths)=="<TripHopSchedule service_id='1'><TripHop depart='00:00' arrive='01:00' transit='3600' trip_id='Foo to Bar' service_id='1' agency='0' timezone_offset='0'/><TripHop depart='01:00' arrive='02:00' transit='3600' trip_id='Bar to Cow' service_id='1' agency='0' timezone_offset='0'/></TripHopSchedule>"
    
    def test_destroy(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        ths.destroy()
        
        assert ths.soul == None
        
    def test_get_calendar(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        assert ths.calendar.head.end_time==86400
        
    def test_get_next_hop(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        assert ths.get_next_hop( 0 ).trip_id == "Foo to Bar"
        assert ths.get_next_hop( 1 ).trip_id == "Bar to Cow"
        assert ths.get_next_hop( 3600 ).trip_id == "Bar to Cow"
        assert ths.get_next_hop( 3601 ) == None
        
    def test_get_last_hop(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        assert ths.get_last_hop( 0 ) == None
        assert ths.get_last_hop( 3600 ).trip_id == "Foo to Bar"
        assert ths.get_last_hop( 3601 ).trip_id == "Foo to Bar"
        assert ths.get_last_hop( 2*3600-1).trip_id == "Foo to Bar"
        assert ths.get_last_hop( 2*3600 ).trip_id == "Bar to Cow"
        assert ths.get_last_hop( 100000 ).trip_id == "Bar to Cow"
    
    def test_walk(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        s = ths.walk(State(2,0))
        
        assert s.time == 3600
        assert s.weight == 3600
        assert s.dist_walked == 0
        assert s.num_transfers == 1
        assert s.prev_edge_type == 2
        assert s.prev_edge_name == "Foo to Bar"
        assert s.num_agencies == 2
        assert s.service_period(0).service_ids == [1,2]
        assert s.service_period(0).begin_time == 0
        assert s.service_period(0).end_time == 86400
        assert s.service_period(1) == None
        assert str(s) == "<state time='3600' weight='3600' dist_walked='0.0' num_transfers='1' prev_edge_type='2' prev_edge_name='Foo to Bar'><ServicePeriod begin_time='0' end_time='86400' service_ids='1,2'/></state>"
        
        rawhops = [(0,     1*3600,'auth1trip0'),
                   (1*3600,2*3600,'auth1trip1')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [3,4]) )
        ths = TripHopSchedule(hops=rawhops, service_id=3, calendar=cal, timezone_offset=0, agency=1)
        
        sfinal = ths.walk(s)
        
        assert sfinal.time == 7200
        assert sfinal.weight == 7200
        assert sfinal.dist_walked == 0.0
        assert sfinal.prev_edge_type == 2
        assert sfinal.prev_edge_name == "auth1trip1"
        assert sfinal.service_period(0).service_ids == [1,2]
        assert sfinal.service_period(1).service_ids == [3,4]
    
    
    def test_walk_back(self):
        rawhops = [(1*3600,2*3600,'Foo to Bar'),
                   (2*3600,3*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        assert ths.walk_back(State(1,0)) == None
        assert ths.walk_back(State(1,2*3600-1)) == None
        
        s = ths.walk_back(State(2,3*3600)) 
        
        assert s.time == 7200
        assert s.weight == 3600
        assert s.dist_walked == 0.0
        assert s.num_transfers == 1
        assert s.prev_edge_name == "Bar to Cow"
        assert s.num_agencies == 2
        assert str(s.service_period(0)) == "<ServicePeriod begin_time='0' end_time='86400' service_ids='1,2'/>"
        assert s.service_period(0).service_ids == [1,2]
        assert s.service_period(0).begin_time == 0
        assert s.service_period(0).end_time == 86400
        assert s.service_period(1) == None
        
        rawhops = [(1*3600,2*3600,'auth1trip0'),
                   (2*3600,3*3600,'auth1trip1')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [3,4]) )
        ths = TripHopSchedule(hops=rawhops, service_id=3, calendar=cal, timezone_offset=0, agency=1)
        
        sfinal = ths.walk_back(s)
        
        assert sfinal.time == 3600
        assert sfinal.weight == 7200
        assert sfinal.dist_walked == 0.0
        assert sfinal.num_transfers == 2
        assert sfinal.prev_edge_type == 2
        assert sfinal.prev_edge_name == "auth1trip0"
        assert sfinal.num_agencies == 2
        assert str(sfinal.service_period(0))=="<ServicePeriod begin_time='0' end_time='86400' service_ids='1,2'/>"
        assert str(sfinal.service_period(1))=="<ServicePeriod begin_time='0' end_time='86400' service_ids='3,4'/>"
    
    
    def test_walk_wrong_day(self):
        rawhops = [(10,     20,'Foo to Bar')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 10, [1]) )
        ths = TripHopSchedule(hops=rawhops, service_id=2, calendar=cal, timezone_offset=0, agency=0)
        
        s = ths.walk(State(1,0))
        
        print s == None
    
    def test_collapse_wrong_day(self):

        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 10, [1]) )
        rawhops = [(10,     20,'Foo to Bar')]
        ths = TripHopSchedule(hops=rawhops, service_id=2, calendar=cal, timezone_offset=0, agency=0)
        
        th = ths.collapse(State(1,0))
        
        assert th == None
    
    def test_collapse(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = ServiceCalendar()
        cal.add_period( ServicePeriod(0, 1*3600*24, [1,2]) )
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0, agency=0)
        
        th = ths.collapse(State(1,0))
        
        assert th.depart == 0
        assert th.arrive == 3600
        assert th.transit == 3600
        assert th.trip_id == "Foo to Bar"
    

class TestListNode(unittest.TestCase):
    def test_list_node(self):
        l = ListNode()

class TestVertex(unittest.TestCase):
    def test_basic(self):
        v=Vertex("home")
        assert v
        
    def test_destroy(self): #mostly just check that it doesn't segfault. the stress test will check if it works or not.
        v=Vertex("home")
        v.destroy()
        
        try:
            v.label
            assert False #pop exception by now
        except:
            pass
        
    def test_label(self):
        v=Vertex("home")
        print v.label
        assert v.label == "home"
    
    def test_incoming(self):
        v=Vertex("home")
        assert v.incoming == []
        assert v.degree_in == 0
        
    def test_outgoing(self):
        v=Vertex("home")
        assert v.outgoing == []
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        v = Vertex("home")
        assert v.to_xml() == "<Vertex degree_out='0' degree_in='0' label='home'/>"

class TestServicePeriod(unittest.TestCase):
    def test_service_period(self):
        c = ServicePeriod(0, 1*3600*24, [1,2])
        assert(c.begin_time == 0)
        assert(c.end_time == 1*3600*24)
        assert(len(c.service_ids) == 2)
        assert(c.service_ids == [1,2])
        
    def test_fast_forward_rewind(self):
        cc = ServiceCalendar()
        cc.add_period( ServicePeriod( 0, 100, [1,2]) )
        cc.add_period( ServicePeriod( 101, 200, [3,4]) )
        cc.add_period( ServicePeriod( 201, 300, [5,6]) )
        
        hh = cc.head
        ff = hh.fast_forward()
        assert ff.begin_time==201
        pp = ff.rewind()
        assert pp.begin_time==0
        
    def test_midnight_datum(self):
        c = ServicePeriod( 0, 1*3600*24, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 0
        
        c = ServicePeriod( 500, 1000, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 0
        
        c = ServicePeriod( 1*3600*24, 2*3600*24, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 86400
        assert c.datum_midnight(timezone_offset=-3600) == 3600
        assert c.datum_midnight(timezone_offset=3600) == 82800
        
        c = ServicePeriod( 1*3600*24+50, 1*3600*24+60, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 86400
        assert c.datum_midnight(timezone_offset=-3600) == 3600
        
    def test_normalize_time(self):
        c = ServicePeriod(0, 1*3600*24, [1,2])
        
        assert c.normalize_time( 0, 0 ) == 0
        assert c.normalize_time( 0, 100 ) == 100

class TestServiceCalendar(unittest.TestCase):
    def test_basic(self):
        c = ServiceCalendar()
        assert( c.head == None )
        
        assert( c.period_of_or_before(0) == None )
        assert( c.period_of_or_after(0) == None )
        
    def test_single(self):
        c = ServiceCalendar()
        c.add_period( ServicePeriod( 0,1000,[1,2,3]) )
        
        assert c.head
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        assert c.head.service_ids == [1,2,3]
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(500).begin_time==0
        assert c.period_of_or_before(1000).begin_time==0
        assert c.period_of_or_before(50000).begin_time==0
        
        assert c.period_of_or_after(-1).begin_time==0
        assert c.period_of_or_after(0).begin_time==0
        assert c.period_of_or_after(500).begin_time==0
        assert c.period_of_or_after(1000).begin_time==0
        assert c.period_of_or_after(1001) == None
        
    def test_multiple(self):
        c = ServiceCalendar()
        # out of order
        c.add_period( ServicePeriod(1001,2000,[3,4,5]) )
        c.add_period( ServicePeriod(0,1000,[1,2,3]) )
        
        assert c.head
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        assert c.head.service_ids == [1,2,3]
        
        assert c.head.previous == None
        assert c.head.next.begin_time == 1001
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time == 0
        assert c.period_of_or_before(1000).begin_time == 0
        assert c.period_of_or_before(1001).begin_time == 1001
        assert c.period_of_or_before(2000).begin_time == 1001
        assert c.period_of_or_before(2001).begin_time == 1001
        
        assert c.period_of_or_after(-1).begin_time == 0
        assert c.period_of_or_after(0).begin_time == 0
        assert c.period_of_or_after(1000).begin_time == 0
        assert c.period_of_or_after(1001).begin_time == 1001
        assert c.period_of_or_after(2000).begin_time == 1001
        assert c.period_of_or_after(2001) == None
        
    def test_add_three(self):
        c = ServiceCalendar()
        c.add_period( ServicePeriod(0,10,[1,2,3]) )
        #out of order
        c.add_period( ServicePeriod(16,20,[4,5,6]) )
        c.add_period( ServicePeriod(11,15,[3,4,5]) )
        
        
        assert c.head.next.next.begin_time == 16
        
    def test_periods(self):
        c = ServiceCalendar()
        
        c.add_period( ServicePeriod(0,10,[1,2,3]) )
        #out of order
        c.add_period( ServicePeriod(16,20,[4,5,6]) )
        c.add_period( ServicePeriod(11,15,[3,4,5]) )
        
        assert [x.begin_time for x in c.periods] == [0,11,16]
            
    def test_to_xml(self):
        c = ServiceCalendar()
        
        c.add_period( ServicePeriod(0,10,[1,2,3]) )
        #out of order
        c.add_period( ServicePeriod(16,20,[4,5,6]) )
        c.add_period( ServicePeriod(11,15,[3,4,5]) )
        
        assert c.to_xml() == "<ServiceCalendar><ServicePeriod begin_time='0' end_time='10' service_ids='1,2,3'/><ServicePeriod begin_time='11' end_time='15' service_ids='3,4,5'/><ServicePeriod begin_time='16' end_time='20' service_ids='4,5,6'/></ServiceCalendar>"


class TestEngine(unittest.TestCase):
    def test_basic(self):
        gg = Graph()
        eng = Engine(gg)
        
        assert eng
        
    def test_basic(self):
        gg = Graph()
        eng = Engine(gg)
        
        assert eng
        
    def test_all_vertex_labels(self):
        gg = Graph()
        gg.add_vertex("A")
        gg.add_vertex("B")
        gg.add_edge("A","B",Street("1",10))
        gg.add_edge("B","A",Street("2",10))
        gg.add_vertex("C")
        gg.add_edge("C","A",Street("3",10))
        gg.add_edge("A","C",Street("4",10))
        gg.add_edge("B","C",Street("5",10))
        gg.add_edge("C","B",Street("6",10))
        
        eng = Engine(gg)
        
        assert eng.all_vertex_labels() == "<?xml version='1.0'?><labels><label>A</label><label>B</label><label>C</label></labels>"
        
    def test_walk_edges_street(self):
        gg = Graph()
        gg.add_vertex("A")
        gg.add_vertex("B")
        gg.add_edge("A","B",Street("1",10))
        gg.add_edge("B","A",Street("2",10))
        gg.add_vertex("C")
        gg.add_edge("C","A",Street("3",10))
        gg.add_edge("A","C",Street("4",10))
        gg.add_edge("B","C",Street("5",10))
        gg.add_edge("C","B",Street("6",10))
        
        eng = Engine(gg)
        
        assert eng.walk_edges("A", time=0) == "<?xml version='1.0'?><vertex><state time='0' weight='0' dist_walked='0.0' num_transfers='0' prev_edge_type='5' prev_edge_name='None'></state><outgoing_edges><edge><destination label='C'><state time='11' weight='22' dist_walked='10.0' num_transfers='0' prev_edge_type='0' prev_edge_name='4'></state></destination><payload><Street name='4' length='10.000000' /></payload></edge><edge><destination label='B'><state time='11' weight='22' dist_walked='10.0' num_transfers='0' prev_edge_type='0' prev_edge_name='1'></state></destination><payload><Street name='1' length='10.000000' /></payload></edge></outgoing_edges></vertex>"

    def xtest_outgoing_edges_entire_osm(self):
        gg = Graph()
        osm = OSM("sf.osm")
        add_osm_to_graph(gg,osm)
        
        eng = Engine(gg)
        
        assert eng.outgoing_edges("65287655") == "<?xml version='1.0'?><edges><edge><dest><Vertex degree_out='4' degree_in='4' label='65287660'/></dest><payload><Street name='8915843-0' length='218.044876' /></payload></edge></edges>"
        
    def xtest_walk_edges_entire_osm(self):
        gg = Graph()
        osm = OSM("sf.osm")
        add_osm_to_graph(gg,osm)
        
        eng = Engine(gg)
        
        assert eng.walk_edges("65287655", time=0) == "<?xml version='1.0'?><vertex><state time='Thu Jan  1 00:00:00 1970' weight='0' dist_walked='0.0' num_transfers='0' prev_edge_type='5' prev_edge_name='None'></state><outgoing_edges><edge><destination label='65287660'><state time='Thu Jan  1 00:04:16 1970' weight='512' dist_walked='218.044875866' num_transfers='0' prev_edge_type='0' prev_edge_name='8915843-0'></state></destination><payload><Street name='8915843-0' length='218.044876' /></payload></edge></outgoing_edges></vertex>"

if __name__ == '__main__':
    tl = unittest.TestLoader()
    
    testables = [\
                 TestGraph,
                 TestGraphPerformance,
                 TestState,
                 TestPyPayload,
                 TestLink,
                 TestWait,
                 TestTripHop,
                 TestTriphopSchedule,
                 TestStreet,
                 TestListNode,
                 TestVertex,
                 TestServicePeriod,
                 TestServiceCalendar,
                 TestEngine,
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)

