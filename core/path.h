struct Path {
  int num_elements;
  int num_alloc;
    
  Vertex **vertices;
  Edge **edges;
} ;

// PATH FUNCTIONS

Path *
pathNew( Vertex* origin );

void
pathDestroy(Path *this);

int
pathGetSize(Path *this);

Vertex *
pathGetVertex( Path *this, int i );

Edge *
pathGetEdge( Path *this, int i );

void
pathAddSegment( Path *this, Vertex *vertex, Edge *edge );