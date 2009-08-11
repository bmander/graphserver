#include "graph.h"

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

fibheap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit );

void pqPush( fibheap *pq, Vertex* item, int priority );

Vertex* pqPop( fibheap *pq, int *priority ) ;

CH* get_contraction_heirarchies(Graph* gg, WalkOptions* wo, int search_limit) ;
