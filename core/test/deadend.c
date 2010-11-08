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
    
    //construct and add TripHop edge
    Timezone* tz = tzNew();
    TimezonePeriod* tzp = tzpNew( 0, 100000, 0 );
    tzAddPeriod( tz, tzp );
    ServiceCalendar* cal = scNew();
    ServiceId* sids = malloc( 1*sizeof(ServiceId) );
    sids[0] = 1;
    ServicePeriod* sp = spNew( 0, 1*3600*24, 1, sids );
    scAddPeriod( cal, sp );

    ServiceId sid = 0;
    int agency = 0;
    TripBoard *tb = tbNew( sid, cal, tz, agency );
    tbAddBoarding( tb, "A1", 10, 0 );
    
    gAddEdge( gg, "A", "B", (EdgePayload*)tb);
    
    State* initstate = stateNew(1, 20);
    WalkOptions* wo = woNew();
    ShortestPathTree* spt = gShortestPathTree( gg, "A", "B", initstate, wo, 1000000, 1000000, 1000000 );
    
    sptDestroy(spt);
    woDestroy( wo );
    gDestroy(gg);
    tzDestroy( tz );
    scDestroy( cal );
    free( sids );
    //nothing should be left
    
    return 1;
}
