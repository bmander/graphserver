#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    Graph* gg = gNew();
    gAddVertex( gg, "A" );
    gAddVertex( gg, "B" );
    gAddEdge( gg, "A", "B", (EdgePayload*)linkNew());
    
    State* initstate = stateNew(0);
    Graph* spt = gShortestPathTree( gg, "A", "B", initstate );
    
    gDestroy(spt, 1, 0);
    gDestroy(gg, 1, 1);
    //nothing should be left
    
    return 1;
}
