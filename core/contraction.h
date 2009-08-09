#include "graph.h"

typedef struct Path Path;

struct Path {
    int n;
    EdgePayload** payloads;
    long length;
} ;

Path* pathNew( int n, long length ) ;

int pathLength( Path* this ) ;

Path* pathCombine( Path* a, Path* b ) ;

void pathDestroy( Path* this ) ;
    
Path* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo ) ;

Path** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) ;
