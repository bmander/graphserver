#include "graph.h"
#include "heap.h"

typedef struct Path Path;
typedef struct fibheap fibheap;
typedef struct CH CH;

struct Path {
    int n;
    EdgePayload** payloads;
    long length;
    Vertex* fromv;
    Vertex* tov;
} ;

struct CH {
    Graph* up;
    Graph* down;
} ;

Path* pathNew( int n, long length ) ;

int pathLength( Path* this ) ;

Path* pathCombine( Path* a, Path* b ) ;

void pathDestroy( Path* this ) ;
    
Path* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo, int weightlimit, int return_full_path ) ;

Path** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) ;

Heap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit );

void pqPush( Heap *pq, Vertex* item, long priority );

Vertex* pqPop( Heap *pq, long *priority ) ;

CH* get_contraction_hierarchies(Graph* gg, WalkOptions* wo, int search_limit) ;

CH* chNew(Graph *up, Graph *down);

Graph* chUpGraph( CH* this ) ;

Graph* chDownGraph( CH* this ) ;
