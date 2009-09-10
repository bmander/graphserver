package algorithm.kao;

import java.util.ArrayList;
import java.util.Collections;
import java.util.GregorianCalendar;

import core.Edge;
import core.Graph;
import core.State;
import core.WalkOptions;
import core.WalkResult;
import edgetype.Hop;
import edgetype.Walkable;

public class KaoGraph extends Graph {
	private static final long serialVersionUID = 3667189924531545548L;
	
	ArrayList<Edge> allhops;
	
	public KaoGraph() {
		allhops = new ArrayList<Edge>();
	}
	
    public Edge addEdge( String from_label, String to_label, Walkable ep ) {
    	Edge ret = super.addEdge(from_label, to_label, ep);
    	allhops.add(ret);
    	return ret;
    }
	
	public ArrayList<EdgeOption> sortedEdges(GregorianCalendar time, long window) {
		ArrayList<EdgeOption> ret = new ArrayList<EdgeOption>();
		State state0 = new State(time);
		
		for(int i=0; i<allhops.size(); i++) {
			Edge hopedge = allhops.get(i);
			Hop hop = (Hop)hopedge.payload;
			
			WalkResult wr = hop.walk(state0, new WalkOptions());
			
			if( wr != null ) {
				long timeToArrival = wr.state.time.getTimeInMillis() - time.getTimeInMillis();
				if( timeToArrival <= window ) {
					ret.add( new EdgeOption(hopedge, timeToArrival) );
				}
			}
		}
		
		Collections.sort(ret);
		
		return ret;
	}
}

