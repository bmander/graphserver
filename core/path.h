struct Path {
  Vector *vertices;
  Vector *edges;
} ;

// PATH FUNCTIONS

Path *
pathNew( SPTVertex* origin, int init_size, int expand_delta );

void
pathDestroy(Path *this);

SPTVertex *
pathGetVertex( Path *this, int i );

Edge *
pathGetEdge( Path *this, int i );

void
pathAddSegment( Path *this, SPTVertex *vertex, Edge *edge );
