from graphserver.core import *
import unittest
import pickle

class TestServiceCalendar(unittest.TestCase):
    def test_basic(self):
        c = ServiceCalendar()
        assert( c.head == None )
        
        assert( c.period_of_or_before(0) == None )
        assert( c.period_of_or_after(0) == None )
        
    def test_get_service_id_int(self):
        c = ServiceCalendar()
        assert c.get_service_id_int( "A" ) == 0
        assert c.get_service_id_int( "A" ) == 0
        assert c.get_service_id_int( "B" ) == 1
        try:
            c.get_service_id_int( 1 )
            assert False
        except TypeError:
            pass
        
        c.add_period(0,1000,["B"])
        
        import pickle
        from cStringIO import StringIO
        src = StringIO()
        p = pickle.Pickler(src)        
        
        p.dump(c)
        datastream = src.getvalue()
        dst = StringIO(datastream)

        upc = pickle.Unpickler(dst).load()
        print c.expound("America/Los_Angeles")
        print upc.expound("America/Los_Angeles")
        assert c.expound("America/Los_Angeles") == upc.expound("America/Los_Angeles"), upc
        for _c in [c, upc]:
            assert _c.get_service_id_string( -1 ) == None
            assert _c.get_service_id_string( 0 ) == "A", _c.to_xml()
            assert _c.get_service_id_string( 1 ) == "B"
            assert _c.get_service_id_string( 2 ) == None
            try:
                _c.get_service_id_string( "A" )
                assert False
            except TypeError:
                pass
        
    def test_single(self):
        c = ServiceCalendar()
        c.add_period( 0,1000,["A","B","C"] )
        
        assert c.head
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        assert c.head.service_ids == [0,1,2]
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(500).begin_time==0
        assert c.period_of_or_before(1000).begin_time==0
        assert c.period_of_or_before(50000).begin_time==0
        
        assert c.period_of_or_after(-1).begin_time==0
        assert c.period_of_or_after(0).begin_time==0
        assert c.period_of_or_after(500).begin_time==0
        assert c.period_of_or_after(1000)==None
        assert c.period_of_or_after(1001) == None
        
    def test_overlap_a_little(self):
        
        c = ServiceCalendar()
        c.add_period( 0, 1000, ["A"] )
        c.add_period( 1000, 2000, ["B"] )
        
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(999).begin_time==0
        assert c.period_of_or_before(1000).begin_time==1000
        
        c = ServiceCalendar()
        c.add_period(1000,2000,["B"])
        c.add_period(0,1000,["A"])
        
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        
        assert c.period_of_or_before(-1) == None
        assert c.period_of_or_before(0).begin_time==0
        assert c.period_of_or_before(999).begin_time==0
        assert c.period_of_or_before(1000).begin_time==1000
        
        #--==--
    
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['A'])
        sc.add_period(1*3600*24,2*3600*24, ['B'])
        
        assert sc.period_of_or_after( 1*3600*24 ).begin_time == 86400
        
        
    def test_multiple(self):
        c = ServiceCalendar()
        # out of order
        c.add_period( 1001,2000,["C","D","E"] )
        c.add_period( 0,1000,["A","B","C"] )
        
        assert c.head
        assert c.head.begin_time == 0
        assert c.head.end_time == 1000
        assert c.head.service_ids == [3,4,0]
        
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
        assert c.period_of_or_after(1000).begin_time == 1001
        assert c.period_of_or_after(1001).begin_time == 1001
        assert c.period_of_or_after(2000) == None
        assert c.period_of_or_after(2001) == None
        
    def test_add_three(self):
        c = ServiceCalendar()
        c.add_period( 0,10,["A","B","C"] )
        #out of order
        c.add_period( 16,20,["C","D","E"] )
        c.add_period( 11,15,["E","F","G"] )
        
        
        assert c.head.next.next.begin_time == 16
        
    def test_periods(self):
        c = ServiceCalendar()
        
        c.add_period( 0,10,["A","B","C"] )
        #out of order
        c.add_period( 16,20,["E","F","G"] )
        c.add_period( 11,15,["C","D","E"] )
        
        assert [x.begin_time for x in c.periods] == [0,11,16]
            
    def test_to_xml(self):
        c = ServiceCalendar()
        
        c.add_period( 0,10,["A","B","C"] )
        #out of order
        c.add_period( 16,20,["D","E","F"] )
        c.add_period( 11,15,["C","D","E"] )
        
        assert c.to_xml() == "<ServiceCalendar><ServicePeriod begin_time='0' end_time='10' service_ids='A,B,C'/><ServicePeriod begin_time='11' end_time='15' service_ids='C,D,E'/><ServicePeriod begin_time='16' end_time='20' service_ids='D,E,F'/></ServiceCalendar>"

    def test_pickle(self):
        cc = ServiceCalendar()
        cc.add_period( 0, 100, ["A","B"] )
        cc.add_period( 101, 200, ["C","D"] )
        cc.add_period( 201, 300, ["E","F"] )
        
        ss = pickle.dumps( cc )
        laz = pickle.loads( ss )
        
        assert cc.__getstate__() == laz.__getstate__()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestServiceCalendar)
    unittest.TextTestRunner(verbosity=2).run(suite)