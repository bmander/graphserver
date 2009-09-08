package main.java.core;

import java.io.Serializable;

import main.java.edgetype.Walkable;
import main.java.gtfs.exception.NegativeWeightException;


public class Edge extends AbstractEdge implements Serializable{
	private static final long serialVersionUID = 2847531383395983317L;
	public Vertex fromv;
    public Vertex tov;
    public Walkable payload;
    
    Edge( Vertex fromv, Vertex tov, Walkable payload ) {
        this.fromv = fromv;
        this.tov = tov;
        this.payload = payload;
    }
    
    public WalkResult walk(State s0, WalkOptions wo) throws NegativeWeightException {
    	return payload.walk( s0, wo );
    }
    
    public WalkResult walkBack(State s0, WalkOptions wo) throws NegativeWeightException{
    	return payload.walkBack( s0, wo );
    }
    
    public String toString() {
        return fromv.label + " -"+payload.toString()+"-> " + tov.label;
    }
}