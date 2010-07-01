#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    Graph* gg = gNew();
    gAddVertex( gg, "A" );
    gAddVertex( gg, "B" );
    
    //construct and add TripHop edge
    Timezone* tz = tzNew();
    TimezonePeriod* tzp = tzpNew( 0, 100000, 0 );
    tzAddPeriod( tz, tzp );
    ServiceCalendar* cal = scNew();
    ServiceId* sids = malloc( 1*sizeof(ServiceId) );
    sids[0] = 1;
    ServicePeriod* sp = spNew( 0, 1*3600*24, 1, sids );
    scAddPeriod( cal, sp );
    TripHop* th = triphopNew( 10, 20, "A1", cal, tz, 0, 1);
    
    gAddEdge( gg, "A", "B", (EdgePayload*)th);
    
    State* initstate = stateNew(1, 20);
    Graph* spt = gShortestPathTree( gg, "A", "B", initstate, 1 );
    
    gDestroy(spt, 1, 0);
    gDestroy(gg, 1, 1);
    tzDestroy( tz );
    scDestroy( cal );
    free( sids );
    //nothing should be left
    
    return 1;
}
