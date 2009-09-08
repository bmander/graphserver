package main.java.algorithm.kao;

import main.java.core.Edge;

public class EdgeOption implements Comparable<EdgeOption>{
	long timeToArrival;
	public Edge edge;
	
	EdgeOption(Edge hop, long timeToArrival) {
		this.edge = hop;
		this.timeToArrival = timeToArrival;
	}

	@Override
	public int compareTo(EdgeOption arg0) {
		return (int)(timeToArrival-arg0.timeToArrival);
	}
	
	public String toString() {
		return edge + " " + timeToArrival;
	}
}
