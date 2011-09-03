#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../fibheap/fibheap.h"
#include "../graphserver.h"
#include "../graph.h"
#include <valgrind/callgrind.h>

int main(int argc, char** argv) {

    Graph *gg = gNew();

    gAddVertex( gg, "home" );
    gAddVertex( gg, "work" );

    Street *s = streetNew( "helloworld", 1, 0 );
    Edge *e = gAddEdge( gg, "home", "work", (EdgePayload*)s );
   
    gDestroy( gg );

    return 0;
}
