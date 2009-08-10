#include "graph.h"

typedef struct Path Path;
typedef struct fibheap fibheap;

struct Path {
    int n;
    EdgePayload** payloads;
    long length;
} ;

Path* pathNew( int n, long length ) ;

int pathLength( Path* this ) ;

Path* pathCombine( Path* a, Path* b ) ;

void pathDestroy( Path* this ) ;
    
Path* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo, int weightlimit, int return_full_path ) ;

Path** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) ;

fibheap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit );

void pqPush( fibheap *pq, Vertex* item, int priority );

Vertex* pqPop( fibheap *pq );
