#include "graphserver.h"
#include <stdio.h>

// PATH FUNCTIONS

Path *
pathNew( Vertex* origin ) {
    Path *this = (Path*)malloc(sizeof(Path));
    
    this->num_elements = 0;
    this->num_alloc = 50;
    
    this->vertices = (Vertex**)malloc((this->num_alloc+1)*sizeof(Vertex*));
    this->edges = (Edge**)malloc(this->num_alloc*sizeof(Edge*));
    
    /*
     * A path is an alternative series of (vertex, edge, vertex, edge, vertex) 
     * elements. As such a complete path always has one more vertices than 
     * edges. One way to deal with this inconveniently dangling Vertex is to
     * specify it at path initialization.
     */
    this->vertices[0] = origin;
    
    return this;
}

void
pathDestroy(Path *this) {
    free(this->vertices);
    free(this->edges);
    free(this);
}

int
pathGetSize(Path *this) {
    return this->num_elements;
}

Vertex *
pathGetVertex( Path *this, int i ) {
    if( i < 0 || i >= this->num_elements+1 ) {
        return NULL;
    }
    
    return this->vertices[i];
}

Edge *
pathGetEdge( Path *this, int i ) {
    if( i < 0 || i >= this->num_elements ) {
        return NULL;
    }
    
    return this->edges[i];
}

void
pathAddSegment( Path *this, Vertex *vertex, Edge *edge ) {
    // expand the arrays, if they're full
    if (this->num_elements >= this->num_alloc-1) {
        printf( "EXPAND\n" );
        this->vertices = (Vertex**)realloc(this->vertices, 
                                           ((this->num_alloc+50) * sizeof(Vertex*)));
        this->edges = (Edge**)realloc(this->vertices, 
                                      ((this->num_alloc+50) * sizeof(Edge*)));
        this->num_alloc += 50;
    }
    
    this->vertices[this->num_elements+1] = vertex;
    this->edges[this->num_elements] = edge;
    
    this->num_elements++;
}