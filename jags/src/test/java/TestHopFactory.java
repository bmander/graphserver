package test.java;

import java.util.ArrayList;
import java.util.Collections;

import main.java.edgetype.Hop;
import main.java.edgetype.factory.GTFSHopFactory;
import main.java.gtfs.Feed;

import junit.framework.TestCase;



public class TestHopFactory extends TestCase {
	
	public void testBasic() throws Exception {
		Feed feed = new Feed( "caltrain_gtfs.zip" );
		GTFSHopFactory hf = new GTFSHopFactory( feed );
		ArrayList<Hop> hops = hf.run();
		
		Collections.sort(hops, new Hop.HopArrivalTimeComparator());
		Hop last = hops.get(hops.size()-1);
		assertTrue(last.start.departure_time.getSecondsSinceMidnight()==91740);
	}
}
