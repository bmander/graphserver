package main.java.edgetype.factory;

import java.util.ArrayList;

import main.java.edgetype.Hop;
import main.java.gtfs.Feed;
import main.java.gtfs.StopTime;
import main.java.gtfs.Trip;



public class GTFSHopFactory {
	private Feed feed;
	
	public GTFSHopFactory(Feed feed) throws Exception {
		this.feed = feed;
		this.feed.loadStopTimes();
		this.feed.loadCalendarDates();
	}
	
	public ArrayList<Hop> run() throws Exception {
		ArrayList<Hop> ret = new ArrayList<Hop>();
		
		//Load hops
		for(Trip trip : feed.getAllTrips() ) {
			ArrayList<StopTime> stoptimes = trip.getStopTimes();
			for(int i=0; i<stoptimes.size()-1; i++) {
				StopTime st0 = stoptimes.get(i);
				StopTime st1 = stoptimes.get(i+1);
				Hop hop = new Hop( st0, st1 );
				ret.add( hop );
			}
		}
		
		return ret;
	}
}
