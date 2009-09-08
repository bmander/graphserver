package test.java;

import java.util.GregorianCalendar;

import main.java.algorithm.Dijkstra;
import main.java.core.Graph;
import main.java.core.State;
import main.java.core.WalkOptions;
import main.java.edgetype.Hop;
import main.java.edgetype.loader.GTFSHopLoader;
import main.java.gtfs.Feed;
import main.java.spt.ShortestPathTree;

import junit.framework.TestCase;

public class TestDijkstra extends TestCase {
	public void testBasic() throws Exception {
		Feed feed = new Feed( "caltrain_gtfs.zip" );
		Graph gg = new Graph();
		GTFSHopLoader hl = new GTFSHopLoader(gg,feed);
		hl.load();
		
		ShortestPathTree spt = Dijkstra.getShortestPathTree(gg, 
				   "Millbrae Caltrain", 
				   "Mountain View Caltrain", 
				   new State(new GregorianCalendar(2009,8,7,12,0,0)), 
				   new WalkOptions());
		assertTrue( ((Hop)spt.getPath(gg.getVertex("Mountain View Caltrain")).vertices.lastElement().incoming.payload).end.arrival_time.getSecondsSinceMidnight()==48540 );
	}
}
