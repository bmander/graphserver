
import java.util.ArrayList;
import java.util.GregorianCalendar;

import spt.ShortestPathTree;

import core.Edge;
import core.Graph;
import core.State;
import core.Vertex;
import core.WalkOptions;
import edgetype.Hop;
import edgetype.loader.GTFSHopLoader;
import gtfs.Feed;
import algorithm.kao.Kao;
import algorithm.kao.KaoGraph;
import algorithm.kao.Tree;
import junit.framework.TestCase;

public class TestKao extends TestCase {
	public void testBasic() throws Exception {
		Feed feed = new Feed( "caltrain_gtfs.zip" );
		KaoGraph kg = new KaoGraph( );
		GTFSHopLoader hl = new GTFSHopLoader(kg, feed);
		hl.load();
		
		GregorianCalendar t_0 = new GregorianCalendar(2009,8,7,12,0,0);
		long delta = 1000000000;
		Vertex mlb = kg.getVertex("Millbrae Caltrain");
		Vertex mtv = kg.getVertex("Mountain View Caltrain" );
		
		Tree tree = Kao.find(kg, t_0, mlb, delta);
		ArrayList<Edge> path = tree.path(mtv);
		
		assertTrue( ((Hop)path.get(path.size()-1).payload).end.arrival_time.getSecondsSinceMidnight()==48540 );
		
		Graph gg = new Graph();
		GTFSHopLoader h2 = new GTFSHopLoader(gg,feed);
		h2.load();
		ShortestPathTree spt = algorithm.Dijkstra.getShortestPathTree(gg, 
											   "Millbrae Caltrain", 
											   "Mountain View Caltrain", 
											   new State(t_0), 
											   new WalkOptions());
		assertTrue( ((Hop)spt.getPath(gg.getVertex("Mountain View Caltrain")).vertices.lastElement().incoming.payload).end.arrival_time.getSecondsSinceMidnight()==48540 );
		
	}
}
