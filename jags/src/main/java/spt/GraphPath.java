package spt;
import java.util.Vector;

import core.Edge;



public class GraphPath {
    public Vector<SPTVertex> vertices;
    public Vector<Edge> edges;
    
    public GraphPath() {
        this.vertices = new Vector<SPTVertex>();
        this.edges = new Vector<Edge>();
    }
    
    public String toString() {
    	return vertices.toString();
    }
}