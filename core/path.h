struct Path {
  Vector *vertices;
  Vector *edges;
} ;

// PATH FUNCTIONS

Path *
pathNew( Vertex* origin, int init_size, int expand_delta );

void
pathDestroy(Path *this);

Vertex *
pathGetVertex( const Path *this, int i );

Edge *
pathGetEdge( const Path *this, int i );

void
pathAddSegment( Path *this, Vertex *vertex, Edge *edge );