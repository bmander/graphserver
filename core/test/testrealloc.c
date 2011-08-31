#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../fibheap/fibheap.h"
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

int main() {
    Graph* gg = gNew();

    char num[30];

    int i;
    for(i=0; i<INITIAL_GRAPH_CAP+5; i++) {
        sprintf( num, "%d", i );
        Vertex* vx = gAddVertex( gg, num );
    }

    for(i=0; i<INITIAL_GRAPH_CAP+5; i++) {
        Vertex *vx = gGetVertexByIndex( gg, i );
        printf( "%s\n", vx->label );
    }

    gDestroy( gg ); 
    
    return 1;
}
