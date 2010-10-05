
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

Heap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit );

void pqPush( Heap *pq, Vertex* item, long priority );

Vertex* pqPop( Heap *pq, long *priority ) ;

CH* get_contraction_hierarchies(Graph* gg, WalkOptions* wo, int search_limit) ;

CH* chNew(void);

Graph* chUpGraph( CH* this ) ;

Graph* chDownGraph( CH* this ) ;
