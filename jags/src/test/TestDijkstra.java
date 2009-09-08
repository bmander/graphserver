package test;

import java.util.GregorianCalendar;

import spt.ShortestPathTree;
import algorithm.Dijkstra;
import core.Graph;
import core.State;
import core.WalkOptions;
import edgetype.Hop;
import edgetype.loader.GTFSHopLoader;
import gtfs.Feed;
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
