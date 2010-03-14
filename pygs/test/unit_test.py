import sys, os
sys.path = [os.path.dirname(os.path.abspath(__file__)) + "/.."] + sys.path
from graphserver.core import *
from graphserver.engine import Engine
from graphserver.graphdb import GraphDatabase
from graphserver import util
import time
import unittest
import pickle

import os

RESOURCE_DIR=os.path.dirname(os.path.abspath(__file__))

def find_resource(s):
    return os.path.join(RESOURCE_DIR, s)

def get_mem_usage():
    """returns percentage and vsz mem usage of this script"""
    pid = os.getpid()
    psout = os.popen( "ps u -p %s"%pid ).read()
    
    parsed_psout = psout.split("\n")[1].split()
    
    return float(parsed_psout[3]), int( parsed_psout[4] )

import csv

def test_graphserver_util():
    util.main_test()

import time
from random import randint
class TestGraphPerformance(unittest.TestCase):
    def test_load_performance(self):
        g = Graph()
        
        reader = csv.reader(open(find_resource("map.csv")))
        
        t0 = time.time()
        for wayid, fromv, tov, length in reader:
            g.add_vertex( fromv )
            g.add_vertex( tov )
            g.add_edge( fromv, tov, Street( wayid, float(length) ) )
        t1 = time.time()
        dt = t1-t0
        
        limit = 0.9
        print "Graph loaded in %f s; limit %f s"%(dt,limit)
        assert dt <= limit
        
    def test_spt_performance(self):
        g = Graph()
        
        reader = csv.reader(open(find_resource("map.csv")))
        
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
            spt = g.shortest_path_tree( nodeid, None, State(0), WalkOptions() )
            t1 = time.time()
            runtimes.append( t1-t0 )
            
        average = sum(runtimes)/len(runtimes)
        
        limit = 0.031
        print "average runtime is %f s; limit %f s"%(average,limit)
        assert average < limit
        
    def test_stress(self):
        g = Graph()
        
        reader = csv.reader(open(find_resource("map.csv")))
        
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
            spt = g.shortest_path_tree( nodeids[ randint(0,len(nodeids)-1) ], "bogus", State(0), WalkOptions() )
            spt.destroy()
            
            thispercent, thisblock = get_mem_usage()
            
            #print "last iteration memory usage: %d"%memblock
            #print "this iteration memory usage: %d"%thisblock
            #print "---"
            print thispercent, thisblock
            changes.append( cmp(memblock, thisblock) )
            
            memblock = thisblock
        
        assert sum(changes) >= -1 #memory usage only increases in one iteration out of all






if __name__ == '__main__':
    tl = unittest.TestLoader()
    
    testables = [\
                 #TestGraph,
                 #TestGraphPerformance,
                 #TestEdge,
                 #TestState,
                 #TestPyPayload,
                 #TestLink,
                 #TestWait,
                 #TestStreet,
                 #TestHeadway,
                 #TestListNode,
                 #TestVertex,
                 #TestServicePeriod,
                 #TestServiceCalendar,
                 #TestEngine,
                 #TestTimezone,
                 #TestTimezonePeriod,
                 #TestTripBoard,
                 #TestCrossing,
                 #TestAlight,
                 #TestHeadwayBoard,
                 #TestHeadwayAlight,
                 #TestWalkOptions,
                 #TestElapseTime,
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)

