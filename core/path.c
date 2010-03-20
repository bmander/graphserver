#include "graphserver.h"
#include <stdio.h>

// PATH FUNCTIONS

Path *
pathNew( Vertex* origin, int init_size, int expand_delta ) {
    Path *this = (Path*)malloc(sizeof(Path));
    
    this->vertices = vecNew( init_size, expand_delta );
    this->edges = vecNew( init_size, expand_delta );
    
    /*
     * A path is an alternating series of (vertex, edge, vertex, edge, vertex) 
     * elements. As such a complete path always has one more vertices than 
     * edges. One way to deal with this inconveniently dangling Vertex is to
     * specify it at path initialization.
     */
    vecAdd( this->vertices, origin );
    
    return this;
}

void
pathDestroy(Path *this) {
    vecDestroy( this->vertices );
    vecDestroy( this->edges );
    free(this);
}

Vertex *
pathGetVertex( Path *this, int i ) {
    return (Vertex*)vecGet( this->vertices, i );
}

Edge *
pathGetEdge( Path *this, int i ) {
    return (Edge*)vecGet( this->edges, i );
}

void
pathAddSegment( Path *this, Vertex *vertex, Edge *edge ) {
    vecAdd( this->vertices, vertex );
    vecAdd( this->edges, edge );
}

void*
pathGetVertexPointer( Path *this ) {
    return this->vertices;
}

void*
pathGetEdgePointer( Path *this ) {
    return this->edges;
}