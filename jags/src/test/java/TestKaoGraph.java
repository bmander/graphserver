package test.java;

import java.util.ArrayList;
import java.util.GregorianCalendar;

import main.java.algorithm.kao.EdgeOption;
import main.java.algorithm.kao.KaoGraph;
import main.java.core.Vertex;
import main.java.edgetype.Hop;
import main.java.edgetype.loader.GTFSHopLoader;
import main.java.gtfs.Feed;

import junit.framework.TestCase;

public class TestKaoGraph extends TestCase {
	public void testBasic() throws Exception {
		KaoGraph kg = new KaoGraph();
		assertNotNull( kg );
	}
	
	public void testImport() throws Exception {
		Feed feed = new Feed( "caltrain_gtfs.zip" );
		KaoGraph kg = new KaoGraph();
		GTFSHopLoader hl = new GTFSHopLoader(kg,feed);
		hl.load();
		
		Vertex mlb = kg.getVertex( "Millbrae Caltrain" );
		assertTrue( mlb.getDegreeOut() == 236 );
		assertTrue( mlb.getDegreeIn() == 236 );
		
		Vertex gilroy = kg.getVertex( "Gilroy Caltrain" );
		assertNotNull( gilroy );
	}
	
	public void testF() throws Exception {
		Feed feed = new Feed( "caltrain_gtfs.zip" );
		KaoGraph kg = new KaoGraph();
		GTFSHopLoader hl = new GTFSHopLoader(kg,feed);
		hl.load();
		
		ArrayList<EdgeOption> hol = kg.sortedEdges(new GregorianCalendar(2009,8,7,12,0,0), 1000000000);
		assertTrue( ((Hop)hol.get(0).edge.payload).start.departure_time.getSecondsSinceMidnight()==43200 );
		assertTrue( ((Hop)hol.get(hol.size()-1).edge.payload).end.arrival_time.getSecondsSinceMidnight()==82260 );
	}
}
