
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
    
CHPath* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo ) ;

CHPath** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) ;
