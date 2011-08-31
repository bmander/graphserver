#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../fibheap/fibheap.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

int main() {
    Graph *gg = gNew();
    Vertex* v1 = vNew(gg, "A");
    Vertex* v2 = vNew(gg, "B");

    ShortestPathTree *spt = sptNew();
    sptAddVertex( spt, v1, 0 );
    sptAddVertex( spt, v2, 1 );
    
    Link* origlink = linkNew();
    
    sptSetParent( spt, "A", "B", (EdgePayload*)origlink );
    
    vDestroy(v1, 1);
    vDestroy(v2, 1);
    linkDestroy(origlink);

    sptDestroy( spt );
    gDestroy( gg );
    
    return 1;
}
