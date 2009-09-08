package test;

import junit.framework.TestCase;
import edgetype.factory.GTFSHopFactory;
import edgetype.Hop;
import gtfs.Feed;

import java.util.ArrayList;
import java.util.Collections;
import java.util.GregorianCalendar;

import core.State;
import core.WalkOptions;

public class TestHop extends TestCase {
	
	public void testHopAfterMidnight() throws Exception {
		Feed feed = new Feed( "caltrain_gtfs.zip" );
		GTFSHopFactory hf = new GTFSHopFactory( feed );
		ArrayList<Hop> hops = hf.run();
		
		Collections.sort(hops, new Hop.HopArrivalTimeComparator());
		Hop last = hops.get(hops.size()-1);
		
		GregorianCalendar aSundayAtMidnight = new GregorianCalendar(2009,7,30,0,0,0);
		assertTrue(last.walk(new State(aSundayAtMidnight), new WalkOptions()).weight==5820.0);
	}
}
