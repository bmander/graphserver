package edgetype.loader;

import core.Graph;
import edgetype.Hop;
import edgetype.factory.GTFSHopFactory;
import gtfs.Feed;
import gtfs.Stop;

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
