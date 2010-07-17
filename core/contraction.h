
typedef struct CHPath CHPath;

struct CHPath {
    int n;
    EdgePayload** payloads;
    long length;
} ;

CHPath* chpNew( int n, long length ) ;

int chpLength( CHPath* this ) ;

CHPath* chpCombine( CHPath* a, CHPath* b ) ;

void chpDestroy( CHPath* this ) ;
    
Path* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo, int weightlimit, int return_full_path ) ;

CHPath** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) ;

fibheap_t init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit );

void pqPush( fibheap_t pq, Vertex* item, int priority );

Vertex* pqPop( fibheap_t pq );
