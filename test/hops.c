#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/graph.h"
#include <valgrind/callgrind.h>

int main() {
    Graph* gg = gNew();
    ServiceCalendar* sc = scNew();
    ServiceId sid = 0;
    ServicePeriod* sp = spNew( 0, 1000000, 1, &sid );
    scAddPeriod( sc, sp );
    TimezonePeriod *tzp = tzpNew( 0, 1000000, 0 );
    Timezone *tz = tzNew();
    tzAddPeriod( tz, tzp );
    
    FILE* fp = fopen( "hopslines", "r" );
    char* fromv = (char*)malloc(255*sizeof(char));
    char* frompsv = (char*)malloc(255*sizeof(char));
    char* topsv = (char*)malloc(255*sizeof(char));
    char* tov = (char*)malloc(255*sizeof(char));
    char* tripid = (char*)malloc(255*sizeof(char));
    int depart;
    int crossing;
    int arrive;
    int i = 0;
    while(!feof(fp)) {
        fscanf( fp, "%s %s %s %s %s %d %d %d", fromv, frompsv, topsv, tov, tripid, &depart, &crossing, &arrive );
        printf( "%s %s %s %s %s %d %d %d\n",fromv, frompsv, topsv, tov, tripid, depart, crossing, arrive);
        
        gAddVertex( gg, fromv );
        gAddVertex( gg, tov );
        gAddVertex( gg, frompsv );
        gAddVertex( gg, topsv );
        
        TripBoard* tb = tbNew( 0, sc, tz, 0 );
        tbAddBoarding(tb, tripid, depart);
        gAddEdge( gg, fromv, frompsv, (EdgePayload*)tb );
        
        Crossing* cr = crNew( crossing );
        gAddEdge( gg, frompsv, topsv, (EdgePayload*)cr );
        
        Alight* al = alNew( 0, sc, tz, 0 );
        alAddAlighting( al, tripid, arrive );
        gAddEdge( gg, topsv, tov, (EdgePayload*)al );
        
    }
    
    
    //clean up
    free(fromv);
    free(frompsv);
    free(tov);
    free(topsv);
    free(tripid);
    
    tzDestroy(tz);
    scDestroy(sc);
    fclose( fp );
    gDestroy( gg, 1, 1 );
    
    /*
    
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
    //Graph* spt = gShortestPathTree( gg, "A", "B", initstate, 1 );
    
    //gDestroy(spt, 1, 0);
    gDestroy(gg, 1, 1);
    tzDestroy( tz );
    scDestroy( cal );
    free( sids );
    //nothing should be left
    
    */
    
    return 1;
}
