#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

int main() {
    Graph* gg = gNew();
    gAddVertex( gg, "A" );
    gAddVertex( gg, "B" );
    gAddEdge( gg, "A", "B", (EdgePayload*)linkNew());

    WalkOptions *wo = woNew();
    
    State* initstate = stateNew(1, 0);
    ShortestPathTree* spt = gShortestPathTree( gg, "A", "B", initstate, wo, 1000001, 100000, 100000 );
    
    woDestroy(wo);
    sptDestroy(spt);
    gDestroy(gg);
    //nothing should be left
    
    return 1;
}
