package main.java.edgetype.loader;

import main.java.core.Graph;
import main.java.edgetype.Hop;
import main.java.edgetype.factory.GTFSHopFactory;
import main.java.gtfs.Feed;
import main.java.gtfs.Stop;

public class GTFSHopLoader {
	Graph graph;
	Feed feed;
	
	public GTFSHopLoader( Graph graph, Feed feed ) {
		this.graph = graph;
		this.feed = feed;
	}
	
	public void load() throws Exception {
		//Load stops
		feed.loadStops();
		for( Stop stop : feed.getAllStops() ) {
			graph.addVertex( stop.stop_id );
		}
		
		//Load hops
		GTFSHopFactory hf = new GTFSHopFactory(feed);
		for( Hop hop : hf.run() ) {
			graph.addEdge(hop.start.stop_id, hop.end.stop_id, hop);
		}
	}
	
}
