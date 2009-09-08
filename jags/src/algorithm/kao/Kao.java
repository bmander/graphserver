package algorithm.kao;

import java.util.ArrayList;
import java.util.GregorianCalendar;

import core.Edge;
import core.Vertex;
import edgetype.Hop;
import gtfs.types.GTFSTime;

public class Kao {
	public static Tree find(KaoGraph graph, GregorianCalendar startTime, Vertex startVertex, long window) {
		Tree tree = new Tree();
		tree.setParent(startVertex,null);
		
		ArrayList<EdgeOption> edgeoptions = graph.sortedEdges(startTime, window);
		
		for( EdgeOption eo: edgeoptions ) {
			Edge segment = eo.edge;
			
			GTFSTime segmentStartTime = ((Hop)segment.payload).start.departure_time;
			Vertex segmentOrig = segment.fromv;
			Vertex segmentDest = segment.tov;
			
			if(tree.containsVertex(segmentOrig) && !tree.containsVertex(segmentDest)) {
				Edge parentSegment = tree.getParent(segment.fromv);
				
				if( parentSegment == null ) {
					tree.setParent(segmentDest, segment);
					continue;
				}
				
				GTFSTime parentSegmentEndTime = ((Hop)parentSegment.payload).end.arrival_time;
				
				if( segmentStartTime.getSecondsSinceMidnight() >= parentSegmentEndTime.getSecondsSinceMidnight() ) {
					tree.setParent(segmentDest, segment);
				}
			}
		}
		return tree;
	}
}
