
typedef struct CHPath CHPath;
typedef struct CH CH;

struct CHPath {
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

CHPath* chpNew( int n, long length ) ;

int chpLength( CHPath* this ) ;

CHPath* chpCombine( CHPath* a, CHPath* b ) ;

void chpDestroy( CHPath* this ) ;
    
CHPath* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo, int weightlimit, int return_full_path ) ;

CHPath** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) ;

fibheap_t init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit );

void pqPush( fibheap_t pq, Vertex* item, int priority );

Vertex* pqPop( fibheap_t pq, int *priority ) ;

CH* get_contraction_heirarchies(Graph* gg, WalkOptions* wo, int search_limit) ;
