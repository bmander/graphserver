#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../fibheap/fibheap.h"
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

int main(int argc, char** argv) {

    Graph *gg = gNew();

    gAddVertex( gg, "A" );
   
    WalkOptions *wo = woNew();
    wo->walking_speed = 1;

    State *st = stateNew(1,0);

    ShortestPathTree *spt = gShortestPathTree( gg, "A", "bogus", st, wo, INFINITY, INFINITY, INFINITY );
   
    woDestroy( wo );
    sptDestroy( spt );
    gDestroy( gg );

    return 0;
}
